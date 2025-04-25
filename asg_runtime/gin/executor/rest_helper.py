"""
Handle REST API calls.
"""

import time
from math import ceil
from urllib import parse

import requests

import asg_runtime.gin.common.con_spec.spec_helper_models as con_spec_models
import asg_runtime.gin.common.util as gin_util
from asg_runtime.utils.logging import get_logger

logger = get_logger("gin_rest_helper")


def perform_rest_api_call(
    api_call: con_spec_models.ApiCall,
    servers: list[str],
    parameter_arguments: dict = None,
    header_arguments: dict = None,
    data_arguments: dict = None,
    output_data: dict[str, con_spec_models.Dataset] = None,
    timeout: int | None = None,
) -> dict[str, any]:
    """
    Execute a REST API call and returns the request output
    as described in the output specification.

    Args:
        api_call (ApiCall): Single API call to be made here.
        servers (list[str]): list of servers to connect to when executing the REST call.
        parameter_arguments (dict, optional): Query parameters.
        header_arguments (dict, optional): Header arguments.
        data_arguments (dict, optional): Data for POST/PUT.
        output_data (dict[str, con_spec_models.Dataset]): Dictionary of output specification.
        timeout (int | None, optional): Timeout for HTTP request.

    Returns:
        dict[str, any]): A dictionary containing the response json formatted output data
    """
    # Assemble the URL for the REST call
    # Supporting only using the 1st entry in the servers list
    call_url = servers[0].removesuffix("/") + "/" + api_call.endpoint.removeprefix("/")

    # Loop through all pages of data
    response_list: list[requests.Response] = []
    pg = 1
    done = False
    while not done:
        # Pop off path parameters from parameters so they don't get passed
        # into query string
        logger.debug("Page: %d. Calling: %s", pg, call_url)
        logger.debug("Parameters: %s", parameter_arguments)
        logger.debug("Headers: %s", header_arguments)
        logger.debug("Data: %s", data_arguments)

        # Make call, and collect response
        response = _perform_url_call(
            api_call.method,
            call_url,
            parameter_arguments,
            header_arguments,
            data_arguments,
            timeout,
        )
        response_list.append(response)

        # Determine URL and parameters for next call
        if not api_call.pagination:
            # No pagination defined in specification
            break

        done, call_url, parameter_arguments_to_update = _handle_pagination(
            call_url, response, api_call.pagination
        )

        if not done:
            for (
                param_name,
                param_value,
            ) in parameter_arguments_to_update.items():
                parameter_arguments[param_name] = param_value
        pg += 1

    # Format responses into a dictionary of output data structures.
    # Current supported is json format (dict)
    output = _handle_api_output(output_data, response_list)

    return output


def _perform_url_call(
    method: con_spec_models.MethodEnum,
    url: str,
    parameter_arguments: dict | None = None,
    header_arguments: dict | None = None,
    data_arguments: dict | None = None,
    timeout: int | None = None,
) -> requests.Response:
    """
    Perform a single REST call and get the response.
    Any query parameter
    Args:
        method (MethodEnum): The HTTP method to use for this API.
        url (str): URL the request is sent to, with path parameters
            already filled in.
        parameter_arguments (dict | None, optional): Query parameters.
        header_arguments (dict | None, optional): Header arguments.
        data_arguments (dict | None, optional): Data for POST/PUT.
        timeout (int | None, optional): Timeout for HTTP request.

    Raises:
        NotImplementedError: Raised if a request method has not yet been
            implemented.

    Returns:
        requests.Response: Response from request.
    """
    if not parameter_arguments:
        parameter_arguments = {}
    if not header_arguments:
        header_arguments = {}
    if not data_arguments:
        data_arguments = {}

    # Fill in path parameters
    call_url = url.format(**parameter_arguments).removeprefix("/")
    query_parameters = parameter_arguments.copy()
    # Remove parameters that we filled into the URL
    for path_param in gin_util.get_fstring_kwords(url):
        query_parameters.pop(path_param)

    if method == con_spec_models.MethodEnum.GET:
        response = _get_with_retries(
            url=call_url,
            params=query_parameters,
            headers=header_arguments,
            timeout=timeout,
        )
    elif method == con_spec_models.MethodEnum.POST:
        response = requests.post(
            call_url,
            params=query_parameters,
            headers=header_arguments,
            data=data_arguments,
            timeout=timeout,
        )
    elif method == con_spec_models.MethodEnum.PUT:
        raise NotImplementedError("PUT method is not supported")
    else:
        raise NotImplementedError(f"Method {method} not supported")

    return response


retries = 3
delay = 3


def _get_with_retries(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int | None = None,
) -> requests.Response:
    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as http_err:
            if response.status_code in [500, 503]:
                logger.debug(f"request failed with {str(http_err)})")
                logger.debug(f"retrying ({attempt + 2}/{retries})")
                time.sleep(delay)
            else:
                raise http_err
    logger.debug(f"Request failed for {retries} attempts, giving up")
    raise Exception("Max retries reached for {url}, can not fetch the data")


def _handle_pagination(
    call_url: str, response: requests.Response, pagination: con_spec_models.Pagination
):
    """
    Handle pagination instructions.

    Args:
        call_url (str): The URL of the API call being made.
        response (Response): The response object returned by the API call.
        pagination (Pagination): Pagination instructions for this API.

    Raises:
        NotImplementedError: Raised if a request method has not yet been
            implemented.
        ValueError: Raised if unable to understand the paging information from the API response.
        KeyError: Raised if pagination information is missing from the API response.
        Exception: Raised if the paging information tried to forward to a different URL.

    Returns:
        done (bool): indication if there are more pages to get.
        next_call_url (str): The URL of the next paging call.
        parameter_arguments (dict): An update to the query parameters.
    """
    # Convert the first response into a dict we can index through
    if "application/json" in response.headers["Content-Type"]:
        response_dict = response.json()
    else:
        raise NotImplementedError(
            f"Pagination not supported for {response.headers['Content-Type']}"
        )

    # Updated parameters to pass to next call
    parameter_arguments = {}
    done = False

    next_call_url = call_url
    # Determine URL of next block of data
    if pagination.next_path:
        # Perform paging by using a direct link to the next page from
        # the last dataset.
        # Make sure we are calling to the same server as the original call
        current_url_prefix = parse.urlparse(call_url).netloc
        next_call_url = gin_util.retrieve_value_from_json_path(response_dict, pagination.next_path)
        next_url_prefix = parse.urlparse(next_call_url).netloc
        if next_call_url and next_url_prefix != current_url_prefix:
            raise Exception(f"URL prefix for next data page does not match spec: {next_call_url}")
        if not next_call_url:
            done = True
    elif pagination.pagination_params:
        # Determine URL for next page of data.

        # Now get parameters for the next page of data. These may be
        # path parameters applied to the URL in the following step, or
        # query parameters that will be applied through the Python
        # requests method in the next iteration of this loop.
        for key, path in pagination.pagination_params.items():
            value = gin_util.retrieve_value_from_json_path(response_dict, path)
            parameter_arguments[key] = value

        if pagination.type == con_spec_models.PaginationTypeEnum.PAGE:
            # Increment the parameter for page from the spec by one.
            tr = pagination.param_translation
            # Page number of latest dataset; increment to next page
            try:
                page = int(parameter_arguments[tr.pageRef]) + 1
            except ValueError as exc:
                raise ValueError(f"Invalid page number: {parameter_arguments[tr.pageRef]}") from exc
            except KeyError as exc:
                raise KeyError(f"Page reference {tr.pageRef} not in pagination_params") from exc
            parameter_arguments[tr.pageRef] = page
            # Size of each page
            try:
                page_size = int(
                    gin_util.retrieve_value_from_json_path(response_dict, tr.pageSizePath)
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid page size: {gin_util.retrieve_value_from_json_path(response_dict, tr.pageSizePath)}"
                ) from exc
            # Total size of data
            try:
                total_size = int(
                    gin_util.retrieve_value_from_json_path(response_dict, tr.totalSizePath)
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid total data size: {gin_util.retrieve_value_from_json_path(response_dict, tr.totalSizePath)}"
                ) from exc
            # Total number of pages
            num_pages = ceil(total_size / page_size)
            # Determine if we already received all pages
            done = page > num_pages
        else:
            raise NotImplementedError(f"Pagination type not yet supported: {pagination.type}")
    else:
        raise NotImplementedError("Pagination instructions not implemented yet.")

    return done, next_call_url, parameter_arguments


def _handle_api_output(
    output_data: dict[str, con_spec_models.Dataset], response_list: list[requests.Response]
) -> dict[str, any]:
    """
    Handle the output of the API call based on the specified output data structure.

    Args:
        output_data (dict[str, Dataset]): The output data structure specified in the API configuration file.
        response_list (list[requests.Response]): A list of requests.Response objects returned from the API call.

    Returns:
        dict: A dictionary containing the json formatted output data.
    """
    # Format responses into a dictionary of output data structures.
    output = {}
    aggregated_response = []
    logger.debug(f"_handle_api_output enter with {len(response_list)} response pages")
    first_page_json = response_list[0].json()
    logger.debug(f"first_page: type={type(first_page_json)}, len={len(first_page_json)}")
    if output_data is not None:
        for resp in response_list:
            for out_dataset, dataset_ref in output_data.items():
                if dataset_ref.path in (".", ""):
                    # When the path into the response is just "." or "",
                    # return the root reply.
                    if dataset_ref.path in output:
                        # In case we added output in previous response and it was a list
                        # append to list.
                        # In case of json dict, update the dict.
                        if isinstance(output[dataset_ref.path], list):
                            output[dataset_ref.path].append(resp.json())
                        if isinstance(output[dataset_ref.path], dict):
                            output[dataset_ref.path].update(resp.json())
                    else:
                        # Assign output to be the response root.
                        output[dataset_ref.path] = resp.json()
                else:
                    # When there is a path into the response, return the
                    # path content
                    if out_dataset in output:
                        # In case we added output in previous response and it was a list, append to list.
                        # In case of json dict, update the dict.
                        if isinstance(output[out_dataset], list):
                            output[out_dataset].append(resp.json()[dataset_ref.path])
                        elif isinstance(output[out_dataset], dict):
                            output[out_dataset].update(resp.json()[dataset_ref.path])
                    else:
                        # Assign output's out_dataset name to be the object in response[dataset_ref.path].
                        output[out_dataset] = resp.json()[dataset_ref.path]
    else:
        aggregated_response = []
        for resp in response_list:
            aggregated_response.append(resp.json())
        output["data"] = aggregated_response

    logger.debug(f"_handle_api_output exit with output: type={type(output)}, len={len(output)}")
    return output
