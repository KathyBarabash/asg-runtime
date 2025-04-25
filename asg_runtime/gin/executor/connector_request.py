import re

import pandas as pd
from pydantic import ValidationError
from varsubst import exceptions, varsubst

import asg_runtime.gin.common.con_spec.spec_helper_models as con_spec_models
from asg_runtime.gin.common.util import replace_env_var
from asg_runtime.utils.logging import get_logger

from ..common import ConnectorSpec
from .rest_helper import perform_rest_api_call
from .transform.transform_exec import (
    apply_transformations_json,
)

logger = get_logger("con_request")


class ConnectorRequest:
    """
    Represents a connector execution request
    and handles the request based on
    the provided connector specification and on
    the provided transfromations folder
    """

    def __init__(self, spec_file: str = None, spec_string: str = None, transforms_path: str = None):
        """
        Initialize the ConnectorRequest with the YAML specification,
        either from a file or from a string, and with a pointer to the
        transformations to be used for executing the request.

        Args:
            spec_file (str): A string containing a path name of the connector specification file
            spec_string (str): A string containing the connector specification
            transforms_path (str): A string containing a path name of the transformations folder
        """
        if spec_file:
            self.spec_file = spec_file
            self.con_spec = ConnectorSpec.from_file(spec_file)
        elif spec_string:
            self.con_spec = ConnectorSpec.from_string(spec_string)

        if not self.con_spec:
            raise ValueError("No valid connector specification is provided")

        self.transforms_path = transforms_path

        # Keep track which APIs we have executed.
        # executed_apis is a dict of API calls that need to be executed (key),
        # and a boolean indicating if they have been executed (value).
        self.executed_apis = {}

    def perform_api_call(
        self,
        api_name: str,
        output_spec: dict[str, con_spec_models.Dataset] = None,
        timeout: int | None = None,
    ) -> dict[str, any]:
        """
        Execute an API call and returns the request output
        as described in the output specification.
        Resolve any dependencies with other API calls.

        Args:
            api_name (str): Name of the API to call.
            output_spec (dict[str, Dataset]): Dictionary of output specification.
            timeout (int | None, optional): Timeout for API call.

        Returns:
            dict[str, any]): The output data structure for this API.
        """
        api_call = self.con_spec.spec.apicalls[api_name]

        # Resolve dependencies in the api call's arguments
        # Collect dependencies by api call, including the needed outputs
        # pre_reqs holds dictionary entry for each api, the value is a list of dependencies
        pre_reqs = {}
        if api_call.arguments is not None:
            for arg in api_call.arguments:
                if arg.source != con_spec_models.ArgSourceEnum.REFERENCE or arg.value is None:
                    # Skip to next argument if not a reference
                    continue
                # # Resolve a reference to environment variable
                # Only string type arguments can include a reference to an environment variable
                if isinstance(arg.value, str):
                    try:
                        arg.value = varsubst(arg.value)
                    except AttributeError:
                        # The attribute referred in 'fieldname' is not defined in the
                        # configuration class instance, skipping.
                        pass
                    except exceptions.KeyUnresolvedException:
                        # The environment variable that was referred in the configuration
                        # is not defined, skipping.
                        pass
                # Resolve a reference from a prerequistive api
                else:
                    try:
                        value = con_spec_models.Dataset(**arg.value)
                        dep_api = value.api
                        if dep_api in pre_reqs:
                            pre_req_entry = pre_reqs[dep_api]
                        else:
                            pre_req_entry = []
                        dep_path_list = value.path.split(".")
                        # Assume that then first value is the array name and the 2nd is the field
                        # The current implementation is scoped to one level array.
                        field_to_get = dep_path_list[1:]
                        if len(field_to_get) > 0:
                            field_to_get_ref = ".".join(dep_path_list[1:])
                        else:
                            field_to_get_ref = None
                        pre_req_entry.append(
                            {
                                "name": arg.name,
                                "path": dep_path_list[0],
                                "field_name": field_to_get_ref,
                            }
                        )
                        pre_reqs[dep_api] = pre_req_entry
                    except ValidationError:
                        continue

        # Are there are pre-req apis to call?
        reference_resolution = {}
        for dep_api, dep_api_entries in pre_reqs.items():
            # Check if we already called this API
            if dep_api not in self.executed_apis or self.executed_apis[dep_api] is False:
                dep_api_output_spec = {}
                for entry in dep_api_entries:
                    dep_api_output_spec[entry["path"]] = con_spec_models.Dataset(
                        api=dep_api, path=entry["path"]
                    )
                result = self.perform_api_call(dep_api, dep_api_output_spec, timeout)
                collect_entries = {}
                for entry in dep_api_entries:
                    collect_entries[entry["name"]] = {
                        "values": result[entry["path"]][entry["field_name"]],
                        "index": 0,
                    }
                reference_resolution[api_name] = collect_entries

        result = self._route_to_api_call_type(api_name, reference_resolution, output_spec, timeout)

        return result

    def _route_to_api_call_type(
        self,
        api_name: str,
        reference_resolution: dict[str, dict[str, any]],
        output_data: dict[str, con_spec_models.Dataset] = None,
        timeout: int | None = None,
    ) -> dict[str, any]:
        """
        Execute an API call and returns the request output
        as described in the output specification.
        Resolve any dependencies with other API calls.

        Args:
            api_name (str): Name of the API to call.
            reference_resolution: dict[str, dict[str, any]]: Dictionary of arguments for iteration
            output_data (dict[str, Dataset]): Dictionary of output specification.
            timeout (int | None, optional): Timeout for API call.

        Returns:
            dict[str, any]): The output data structure for this API.
        """
        api_call = self.con_spec.spec.apicalls[api_name]

        # Accumulate the results of multiple queries into a single dataframe
        accumulated_result = {}
        stop_iterations = False
        are_there_dependencies = True

        # Loop for each value of a dependenct argument
        # Currently only one dependent argument is supported
        while are_there_dependencies and not stop_iterations:
            are_there_dependencies = False
            prepend_values = {}
            if api_call.type == con_spec_models.CallTypeEnum.URL:
                # Prepare REST API call
                parameter_arguments = {}
                header_arguments = {}
                data_arguments = {}
                if api_call.arguments is not None:
                    # Look for argument that depends on a pre-req API call
                    for arg in api_call.arguments:
                        value = arg.value
                        # Replace environment variables with their actual values
                        if arg.type == "string" and "$" in value:
                            pattern = r"\$\w+"
                            # Replace all environment variables in the value
                            value = re.sub(pattern, replace_env_var, value)
                        # If the arg.name appears in the reference_resolution then we need to resolve to get the value
                        if (
                            api_name in reference_resolution
                            and arg.name in reference_resolution[api_name]
                        ):
                            # reference_resolution is { dependent_api: { argument: {index: ##, values: DF} }}
                            are_there_dependencies = True
                            index_to_reference = reference_resolution[api_name][arg.name]["index"]
                            reference_values = reference_resolution[api_name][arg.name]["values"]
                            # Get the value
                            if not isinstance(reference_values, pd.core.series.Series):
                                reference_values = [reference_values]
                            value = reference_values[index_to_reference]
                            # Signal to stop when we reach the last reference, or up to 20 iteration
                            # Stopping at 20 itertaion is a temporaruy setting due to performance issues.
                            if (
                                index_to_reference == len(reference_values) - 1
                                or index_to_reference > 20
                            ):
                                stop_iterations = True
                            else:
                                reference_resolution[api_name][arg.name]["index"] = (
                                    index_to_reference + 1
                                )
                            prepend_values[arg.name] = value
                        if arg.argLocation == con_spec_models.ArgLocationEnum.HEADER:
                            header_arguments[arg.name] = value
                        elif arg.argLocation == con_spec_models.ArgLocationEnum.DATA:
                            data_arguments[arg.name] = value
                        elif arg.argLocation == con_spec_models.ArgLocationEnum.PARAMETER:
                            parameter_arguments[arg.name] = value

                servers = []
                for server in self.con_spec.servers:
                    servers.append(server.url)
                api_result = perform_rest_api_call(
                    api_call,
                    servers,
                    parameter_arguments,
                    header_arguments,
                    data_arguments,
                    output_data,
                    timeout,
                )
                for dataset_key, dataset_value in api_result.items():
                    for arg_name, arg_value in prepend_values.items():
                        full_arg_name = "argument-" + arg_name
                        dataset_value[full_arg_name] = arg_value
                    if dataset_key not in accumulated_result:
                        accumulated_result[dataset_key] = dataset_value
                    else:
                        accumulated_result[dataset_key].append(dataset_value)
            else:
                raise NotImplementedError(f"Invalid call type: {api_call.type}")

        return accumulated_result

    def execute(
        self,
    ) -> dict[str, any]:
        """
        Execute a connector from the connector specification.
        If the result is paginated, pull in and combine the full data using
        the method stated in the specification at self.spec_file.

        Returns:
            dict[str, any]): The output data structure specified in the API configuration file.
        """
        # Reset executed apis tracking
        self.executed_apis = {}
        # apis_output_spec is a dict that stores the output specification for each API.
        apis_output_spec = {}
        out_data_spec = self.con_spec.spec.output.data
        logger.debug("Output spec: %s", out_data_spec)
        # Inspect the request output and add APIs that needs to be executed to satisft the output
        if out_data_spec is not None:
            for out_df_name, df_ref in out_data_spec.items():
                # Add the apiname to the list of not yet executed APIs only if the API
                #  is in the list of APIs to call
                if df_ref.api in self.con_spec.spec.apicalls:
                    logger.debug(
                        "Adding API call to list of calls to be made: %s",
                        df_ref.api,
                    )
                    self.executed_apis[df_ref.api] = False
                    # Add the output specification for the API
                    if df_ref.api not in apis_output_spec:
                        apis_output_spec[df_ref.api] = {}
                    apis_output_spec[df_ref.api][out_df_name] = df_ref
                else:
                    # The requested output reference points to an API that is not
                    #  part of the connector specification.
                    raise exceptions.KeyUnresolvedException(
                        f"Output endpoint reference {df_ref.api} is not in the api calls list"
                    )

        logger.debug(f"Collect data by calling the apis: {list(self.executed_apis.keys())}")
        output = self.fetch_data(
            self.executed_apis.items(),
        )

        return output

    def fetch_data(apis):
        # Loop for all APIs that should be executed, starting of those that provides the output
        output = {}
        for api_name, was_executed in apis:
            if not apis[api_name]:
                logger.debug(f"Execute {api_name}")
                result = self.perform_api_call(
                    api_name,
                    apis[api_name],
                    self.con_spec.spec.timeout,
                )
                logger.debug(
                    f"api {api_name} returned ok, adding {len(result)} items to the output"
                )
                output.update(result)
                apis[api_name] = True

                return output

    def apply_transforms(self, spec_exports, output):
        transformed_output = {}
        for export_name, process_data_set in spec_exports.items():
            data_set_path = process_data_set.dataframe
            logger.debug(
                f"export_name={export_name}, process_data_set={process_data_set}, data_set_path={data_set_path}"
            )
            curr_df = apply_transformations_json(
                output,
                data_set_path,
                process_data_set,
                self.transforms_path,
            )
            transformed_output[export_name] = curr_df
        return transformed_output


# def execute_from_file(
#     filename: str,
#     log_level: str = None,
#     user_functions_path=None,
# ) -> dict[str, any]:
#     """
#     Execute a connector from a connector specification file.

#     Args:
#         spec_file (str): Path to a file containing the connector specification.
#         log_level (str): Logging level to set or None to set the default level.
#         user_functions_path (str): A string containing a path name of the transformations folder
#     Returns:
#         dict: Returned data from connector execution.
#     """
#     # Set log level
#     Logging(log_level=log_level)

#     connector_request = ConnectorRequest(
#         spec_file=filename, transforms_path=user_functions_path
#     )
#     return connector_request.run()


# def execute_from_string(
#     spec_string: str,
#     log_level: str = None,
#     user_functions_path=None,
# ) -> dict[str, any]:
#     """
#     Execute a connector from a connector specification string.

#     Args:
#         spec_string (str): A string containing the connector specification.
#         log_level (str): Logging level to set or None to set the default level.
#         user_functions_path (str): A string containing a path name of the transformations folder
#     Returns:
#         dict[str, any]: Data obtained from the connector execution.
#     """
#     Logging(log_level=log_level)
#     logger.debug(f"execute_from_string: log_level={log_level} user_functions_path={user_functions_path}")

#     connector_request = ConnectorRequest(
#         spec_string=spec_string,
#         transforms_path=user_functions_path
#     )

#     return connector_request.execute()
