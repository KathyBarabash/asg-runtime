import hashlib
import re
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ValidationError
from varsubst import exceptions, varsubst

from .gin import ArgLocationEnum as GinArgLocationEnum
from .gin import ArgSourceEnum as GinArgSourceEnum
from .gin import Argument as GinArgument
from .gin import CallTypeEnum as GinCallTypeEnum

# import GIN data models
from .gin import ConnectorSpec as GinConnectorSpec
from .gin import Dataset as GinDataset
from .gin import apply_transformations_json as gin_apply_transforms

# import GIN methods
from .gin.common.util import replace_env_var
from .gin.executor.rest_helper import perform_rest_api_call as gin_rest_api_call
from .http import OriginFetcher
from .models import RestDataSource
from .utils import get_logger

logger = get_logger("gin_helper")


class TempApiCall(BaseModel):
    api_call: BaseModel | None = None
    servers: list | None = None
    param_args: dict | None = None
    header_args: dict | None = None
    data_args: dict | None = None
    otput_spec: dict | None = None
    timeout: int | None = None
    prepend_values: dict | None = None
    url: str | None = None
    # method: str = 'post'| 'get'| 'put'
    method: str
    pagination: BaseModel | None = None

class OriginApi(BaseModel):
    processed: bool | None = False
    output_specs: dict[str, GinDataset] | None = {}


class GinHelper:
    """
    Represents a connector execution request
    and handles the request based on
    the provided connector specification and on
    the provided transfromations folder
    """

    con_spec: GinConnectorSpec
    spec_hash: str
    transforms_path: Path

    origin_apis: dict[str, OriginApi]

    # this is used to unwrap legacy recursion
    collect_only: bool = True
    collected_apis = list[TempApiCall]  # maybe we can combine it into origin_apis

    def __init__(self, spec_string: str, transforms_path: Path):
        """
        Initialize the ConnectorRequest with the YAML specification,
        either from a file or from a string, and with a pointer to the
        transformations to be used for executing the request.

        Args:
            spec_file (str): A string containing a path name of the connector specification file
            spec_string (str): A string containing the connector specification
            transforms_path (str): A string containing a path name of the transformations folder
        """
        logger.debug("initializing request handler for the spec")
        self.con_spec = GinConnectorSpec.from_string(spec_string)
        if not self.con_spec:
            raise ValueError("no valid connector specification is provided")

        logger.debug("TODO - just saving the transorms path, better to also load the functions")
        self.transforms_path = transforms_path

        self.origin_apis = self.init_origin_apis()
        self.collect_apis_to_call()

        self.spec_hash = hashlib.sha256(spec_string.encode("utf-8")).hexdigest()
        return

    def init_origin_apis(self) -> dict[str,OriginApi]:
        origin_apis = {}

        logger.debug("_init_origin_apis enter")
        datasets_to_collect = self.con_spec.spec.output.data
        if not datasets_to_collect:
            logger.warning("no 'outputs' section in the spec, no transformations will be applied")
            return
        num_datasets = len(datasets_to_collect)
        if not num_datasets:
            logger.warning("no outputs in the spec, no transformations will be applied")
            return
        logger.debug(f"the spec calls for collecting {num_datasets} transformed datasets")

        # inspect spec outputs and collect origin APIs that need to be called
        for dataset_name, dataset in datasets_to_collect.items():
            api_name = dataset.api
            logger.debug(f"dataset_name={dataset_name}, api_name={api_name}")
            if api_name not in self.con_spec.spec.apicalls:
                raise Exception(
                    f"Badly formatted spec: output dataset {dataset_name} references {api_name}, not in the api calls list"
                )

            logger.debug(f"enlisting {api_name}")
            origin_api = OriginApi(processed=False)
            origin_api.output_specs[dataset_name] = dataset
            origin_apis[api_name] = origin_api

        logger.debug(f"_init_origin_apis exit, origin_apis={origin_apis}")
        return origin_apis

    def collect_apis_to_call(self) -> list[TempApiCall]:
        logger.debug("collect_apis_to_call - enter")
        self.collected_apis = []

        # Loops for all APIs in the call list, starting of those that provides the output
        self.collect_only = True
        output = self.execute() 
        logger.debug(f"len(output)={len(output)} (should be 0)")
        logger.debug(
            f"len(self.collected_apis)={len(self.collected_apis)}, len(self.origin_apis)={len(self.origin_apis)}"
        )
        return

    # ------------------------- apis exposed to asg-runtime -------------------
    def get_key_for_spec(self):
        return self.spec_hash

    def get_origin_sources(self) -> list[TempApiCall]:
        return self.collected_apis


    async def get_data_from_sources(
        self, origin_sources: list[TempApiCall], origin_fetcher: OriginFetcher | None = None
    ) -> dict[str, any]:
        logger.debug(f"get_data_from_sources - enter for {len(origin_sources)} sources")
        result = {}

        for source in origin_sources:
            logger.debug(f"source={source}")

            if origin_fetcher:
                logger.debug("use new async-caching fetcher")
                http_data_source = RestDataSource(
                    url_template=source.url,
                    parameter_args=source.param_args,
                    header_args=source.header_args,
                    timeout=source.timeout,
                    pagination = source.pagination,
                )
                json_pages = await origin_fetcher.fetch_json_pages_from_source(http_data_source)
                if not isinstance(json_pages, list):
                    logger.error(
                        f"origin_fetcher.fetch_json_pages_from_source returned {type(json_pages)}, expected list")                   
                logger.debug(f"received {len(json_pages)} json pages")
                origin_data = jason_to_datasets(source.otput_spec, json_pages)
                logger.debug(
                    f"transformed into origin_data of type={type(origin_data)} and len={len(origin_data)}"
                )
            else:
                # use legacy sync non-caching way
                origin_data = gin_rest_api_call(
                    source.api_call,
                    source.servers,
                    source.param_args,
                    source.header_args,
                    source.data_args,
                    source.otput_spec,
                    source.timeout,
                )
            logger.debug(f"api_result: len={len(origin_data)}")
            result.update(self._accumulate_api_result(origin_data, source.prepend_values))

        logger.debug(f"collected {len(result)} datasets")

        return result

    def get_origin_data(self) -> dict[str, any]:
        logger.debug("get_origin_data - enter")

        # Loops for all APIs in the call list, starting of those that provides the output
        self.collect_only = False
        output = self.execute()
        logger.debug(f"len(output)={len(output)}")

        return output

    def apply_transforms(self, origin_data: dict) -> dict:
        logger.debug(f"apply_transforms = enter, origin_data type={type(origin_data)}, len={len(origin_data)}")
        spec_exports = self.con_spec.spec.output.exports
        if not spec_exports or not len(spec_exports):
            logger.debug("no exports defined, returning data with no transformations")
            return origin_data

        logger.debug(f"spec defines {len(spec_exports)} output datasets")
        result = {}
        for export_name, process_data_set in spec_exports.items():
            data_set_path = process_data_set.dataframe
            logger.debug(
                f"transforming origin data to produce dataset {export_name} from data at path={data_set_path} with {process_data_set}"
            )
            export_data = gin_apply_transforms(
                json_data=origin_data[data_set_path],
                process_data_set=process_data_set,
                user_functions_path=self.transforms_path)
            logger.debug(f"received export_data of len={len(export_data)}")
            result[export_name] = export_data
            
        logger.debug(f"apply_transforms = exit, collected {len(result)} datasets")
        return result

    # --------------------------------------------------
    # boundary methods from the old code,
    # methods from the ConnectorRequest and http-helper
    # refactored to support separation of the stages into:
    # 1. origin fetching
    # 2. transformation
    # ------------------------------------------------------------------------
    # refactored ConnectorRequest.execute()
    # 1. creation of the list of names of origin methods to call
    # is refactored out into a private method _init_origin_calls_lists
    # and executed as part of initialization
    # 2. applying transormations is extracted into a private method
    # to be called by asg-runtime after all the data is fetched from the
    # origin
    #
    def execute(self) -> dict[str, any]:
        logger.debug(f"execute - enter, self.origin_apis={self.origin_apis}")

        # Loops for all APIs in the call list, starting of those that provides the output
        output = {}
        for api_name, api_info in self.origin_apis.items():
            if api_info.processed:
                logger.debug(f"{api_name} was already fetched, skipping")
                continue

            logger.debug(f"calling perform_api_call for {api_name}")
            result = self.perform_api_call(
                api_name,
                api_info.output_specs,
                self.con_spec.spec.timeout,
            )
            logger.debug(f"api {api_name} returned ok, adding {len(result)} items to the output")
            output.update(result)
            api_info.processed = True

        logger.debug(f"execute - exit, self.origin_apis={self.origin_apis}")
        return output

    # extracted from ConnectorRequest.perform_api_call
    def _compute_api_prepeqs(self, args: list[GinArgument]) -> dict[str, any]:
        # Resolve dependencies in the api call's arguments
        # Collect dependencies by api call, including the needed outputs
        # pre_reqs holds dictionary entry for each api, the value is a list of dependencies
        pre_reqs = {}
        logger.debug(f"compute_api_prepeqs - enter for {args}")

        if not args:
            return pre_reqs

        for arg in args:
            if arg.source != GinArgSourceEnum.REFERENCE or arg.value is None:
                logger.debug(f"argument {arg} is not a reference or lacks value, skipping")
                continue
            logger.debug(f"argument {arg} is a reference with non-null value")

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
                    value = GinDataset(**arg.value)
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
        return pre_reqs

    # left as it was in ConnectorRequest
    # onnly added loging messages
    def perform_api_call(
        self,
        api_name: str,
        output_spec: dict[str, GinDataset] = None,
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
        logger.debug(f"perform_api_call enter for {api_name}: api_call={api_call.model_dump()}")

        pre_reqs = self._compute_api_prepeqs(api_call.arguments)
        logger.debug(f"api has {len(pre_reqs)} pre_reqs:{pre_reqs}")

        # Are there any pre-req apis to call?
        reference_resolution = {}
        for dep_api, dep_api_entries in pre_reqs.items():
            # Check if we already processed this API
            if dep_api not in self.origin_apis or self.origin_apis[dep_api].processed is False:
                dep_api_output_spec = {}
                for entry in dep_api_entries:
                    dep_api_output_spec[entry["path"]] = GinDataset(api=dep_api, path=entry["path"])
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

    # mostly left untouched from ConnectorRequest
    # refactored only to respect the flag to
    # avoid fetching the data and just collect the rest call parameters
    # when global flag is set to true
    def _route_to_api_call_type(
        self,
        api_name: str,
        reference_resolution: dict[str, dict[str, any]],
        output_data: dict[str, GinDataset] = None,
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
            if api_call.type == GinCallTypeEnum.URL:
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
                        if arg.argLocation == GinArgLocationEnum.HEADER:
                            header_arguments[arg.name] = value
                        elif arg.argLocation == GinArgLocationEnum.DATA:
                            data_arguments[arg.name] = value
                        elif arg.argLocation == GinArgLocationEnum.PARAMETER:
                            parameter_arguments[arg.name] = value

                servers = []
                for server in self.con_spec.servers:
                    servers.append(server.url)

                # REFACTOR IS HERE
                if self.collect_only:
                    call_url = (
                        servers[0].removesuffix("/") + "/" + api_call.endpoint.removeprefix("/")
                    )

                    rest_api_call = TempApiCall(
                        api_call=api_call,
                        servers=servers,
                        param_args=parameter_arguments,
                        header_args=header_arguments,
                        data_args=data_arguments,
                        otput_spec=output_data,
                        timeout=timeout,
                        prepend_values=prepend_values,
                        url=call_url,
                        method=api_call.method.value,
                        pagination=api_call.pagination,
                    )
                    self.collected_apis.append(rest_api_call)
                else:
                    api_result = gin_rest_api_call(
                        api_call,
                        servers,
                        parameter_arguments,
                        header_arguments,
                        data_arguments,
                        output_data,
                        timeout,
                    )
                    # REFACTOR IS HERE
                    accumulated_result.update(
                        self._accumulate_api_result(api_result, prepend_values)
                    )
            else:
                raise NotImplementedError(f"Invalid call type: {api_call.type}")

        return accumulated_result

    # extracted for code compactness
    # does not need to belong to a class
    def _accumulate_api_result(self, api_result, prepend_values):
        accumulated_result = {}
        for dataset_key, dataset_value in api_result.items():
            for arg_name, arg_value in prepend_values.items():
                full_arg_name = "argument-" + arg_name
                dataset_value[full_arg_name] = arg_value
            if dataset_key not in accumulated_result:
                accumulated_result[dataset_key] = dataset_value
            else:
                accumulated_result[dataset_key].append(dataset_value)
        return accumulated_result


# ------------------ private ---------------
# extracted from the legacy rest_helper._handle_ 
# where it was bundled into the http access
# ------------------------------------------
def jason_to_datasets(
    output_spec: dict[str, GinDataset], 
    json_list: list[any]
) -> dict[str, any]:
    output = {}

    if not output_spec:
        logger.debug("_handle_api_output - no output spec defined, returning data as is")
        output["data"] = json_list
        return output

    for resp_json in json_list:
        for out_dataset, dataset_ref in output_spec.items():
            if dataset_ref.path in (".", ""):
                if dataset_ref.path in output:
                    if isinstance(output[dataset_ref.path], list):
                        output[dataset_ref.path].append(resp_json)
                    elif isinstance(output[dataset_ref.path], dict):
                        output[dataset_ref.path].update(resp_json)
                else:
                    output[dataset_ref.path] = resp_json
            else:
                if out_dataset in output:
                    if isinstance(output[out_dataset], list):
                        output[out_dataset].append(resp_json[dataset_ref.path])
                    elif isinstance(output[out_dataset], dict):
                        output[out_dataset].update(resp_json[dataset_ref.path])
                else:
                    output[out_dataset] = resp_json[dataset_ref.path]

    return output
