"""Methods for generating connector specification"""

import json
import logging
import re

from langchain_core.documents.base import Document

from asg_runtime.gin.common.logging import Logging
from asg_runtime.gin.common.types import (
    ApiCallInf,
    APITypes,
    AppInstance,
    AuthType,
    HTTPParamLocation,
)
from asg_runtime.gin.common.util import get_details_for_call

from .spec_helper_models import (
    ArgLocationEnum,
    ArgSourceEnum,
    CallTypeEnum,
    Dataset,
    ProcessDataSet,
    Server,
)
from .spec_model import ConnectorSpec


def create_output_section(call: ApiCallInf, context: list[Document]) -> dict[str, Dataset]:
    """
    Create the output section in the connector specification.
    Populate the output section based on the given APi call response schema,
    returning all root level elements.

    Args:
        call (ApiCallInf):API call
        context (List[Document]): Contextual documents provided to LLM of
            available APIs.

    Returns:
        Dict[str, Dataset]: The output section in the connector specification.
    """
    out_dataframes = {}
    tool_details = get_details_for_call(call.name, context)
    if tool_details is None:
        return None
    if tool_details.call_meta and tool_details.call_meta.output_schema:
        schema = tool_details.call_meta.output_schema
    else:
        return None
    if schema["type"] == "array":
        out_dataframes[call.name] = Dataset(api=call.name)
    else:
        for key in schema["properties"].keys():
            out_dataframes[key] = Dataset(api=call.name, path=key)
    if not out_dataframes:  # out_dataframes is empty
        return None
    return out_dataframes


def make_connector_json_schema() -> str:
    """
    Create a JSON Schema for the connector specification.

    Returns:
        str: JSON Schema of connector specification.
    """
    return json.dumps(ConnectorSpec.model_json_schema(), indent=2)


def make_connector_spec(
    api_calls: list[ApiCallInf],
    context: list[Document],
    user_input: str,
    out_dataframes: dict[str, Dataset],
    exports: dict[str, ProcessDataSet] = None,
    app_inst: AppInstance | None = None,
) -> ConnectorSpec:
    """Create a connector specification from a list of API call inferences.

    Args:
        api_calls (List[ApiCallInf]): List of API calls.
        context (List[Document]): Contextual documents provided to LLM of
            available APIs.
        user_input (str): User utterance.
        exports (Dict[str, ProcessDataSet]): key - output dataframe name,
            value - ProcessDataSet object.
        app_inst (Optional[AppInstance]): Source application instance details
            to add to connector specification.

    Returns:
        ConnectorSpec:  Connector specification.
    """
    base_log = logging.getLogger(Logging.BASE)
    apicalls_dict = {}
    for call in api_calls:
        apicall = {
            "type": CallTypeEnum.URL,
        }

        tool_details = get_details_for_call(call.name, context)
        if tool_details.api_type != APITypes.REST:
            # This connector exporter is REST specific
            raise ValueError(f"Invalid API type: {tool_details.api_type}")
        apicall["endpoint"] = tool_details.call_meta.endpoint
        apicall["method"] = tool_details.call_meta.method

        list_args = []

        security_arg = {}
        security_arg["type"] = "string"
        security_arg["source"] = ArgSourceEnum.CONSTANT
        if app_inst:
            if app_inst.auth_type != AuthType.NO_AUTH:
                update_app_inst_security_arg(security_arg, app_inst)
                list_args.append(security_arg)
        else:
            if tool_details.call_meta.auth_type:
                auth_types = tool_details.call_meta.auth_type
                if not auth_types:
                    base_log.error("No app_inst and authentication couldn't be resolved from spec")
                    raise NotImplementedError("Authentication cannot be found and handled")
            # Take the first auth_type of this endpoint, the user can specify explicitly the type
            # he wants to use in the app instance
            default_auth_type = auth_types[0]
            auth_type = default_auth_type["type"].lower()
            if auth_type == "http":
                # Get if this is HTTP basic or HTTP bearer
                auth_type = default_auth_type["scheme"].lower()
            if auth_type != AuthType.NO_AUTH:
                security_arg["argLocation"] = default_auth_type["in"]
                if auth_type == AuthType.API_KEY:
                    security_arg["name"] = default_auth_type["name_in_request"]
                    security_arg["value"] = (default_auth_type["scheme"] + " " + "$TOKEN").strip()
                elif auth_type == AuthType.BEARER:
                    security_arg["name"] = "Authorization"
                    security_arg["value"] = "Bearer $TOKEN"
                else:
                    base_log.error(
                        "Security type %s defined in spec is not supported",
                        auth_type,
                    )
                    raise NotImplementedError("Authentication method is not supported")
                list_args.append(security_arg)

        for param in tool_details.parameters:
            if param in call.parameters or param in tool_details.parameters["required"]:
                args = {}
                args["name"] = param
                if param in call.parameters:
                    args["source"] = ArgSourceEnum.CONSTANT
                    args["value"] = call.parameters[param]
                else:
                    args["source"] = ArgSourceEnum.RUNTIME
                if "type" in tool_details.parameters[param]:
                    args["type"] = tool_details.parameters[param]["type"]
                # TODO Need a cleaner way to sync props.location enum values
                # with ArgLocationEnum, these are not aligned.
                if "location" in tool_details.parameters[param]:
                    if (
                        tool_details.parameters[param]["location"] == HTTPParamLocation.QUERY
                        or tool_details.parameters[param]["location"] == HTTPParamLocation.PATH
                    ):
                        args["argLocation"] = ArgLocationEnum.PARAMETER
                    elif tool_details.parameters[param]["location"] == HTTPParamLocation.HEADER:
                        args["argLocation"] = ArgLocationEnum.HEADER
                    else:
                        raise NotImplementedError(
                            f"Unsupported argument location: {
                                tool_details.parameters[param]["location"]}"
                        )
                list_args.append(args)
        apicall["arguments"] = list_args

        apicalls_dict[call.name] = apicall
    con_spec_dict = {
        "apiVersion": "connector/v1",
        "kind": "connector/v1",
        "metadata": {
            "name": "TBD",
            "description": "TBD",
            "inputPrompt": user_input,
        },
        "spec": {
            "apiCalls": apicalls_dict,
            "output": {
                "execution": "",
                "runtimeType": "python",
                "data": out_dataframes,
                "exports": exports,
            },
        },
    }
    base_log.debug("Connector spec dict: %s", con_spec_dict)
    con_spec = ConnectorSpec(**con_spec_dict)
    if app_inst:
        add_app_inst_servers_to_spec(con_spec, app_inst)
    else:
        servers = tool_details.call_meta.servers
        con_spec.servers = resolve_servers_section(servers)
    return con_spec


def update_app_inst_security_arg(security_arg: dict[str, str], app_inst: AppInstance) -> None:
    """Update security argument values from app_inst.

    Args:
        security_arg (dict[str, str]): Security argument dictionary.
        app_inst (AppInstance): Source application instance details
            to create the security argument from.
    """
    if app_inst.auth_type == AuthType.API_KEY:
        security_arg["name"] = app_inst.auth_name
        security_arg["value"] = (
            app_inst.auth_scheme + " " + app_inst.key_envar.get_raw_value()
        ).strip()
    elif app_inst.auth_type == AuthType.BEARER:
        security_arg["name"] = "Authorization"
        security_arg["value"] = "Bearer " + app_inst.key_envar.get_raw_value()
    else:
        raise NotImplementedError("Authentication method is not supported")

    # currently assuming the location is only in header, user can set this in app_inst
    security_arg["argLocation"] = ArgLocationEnum.HEADER


def resolve_servers_section(
    servers: list[dict[str:any]],
) -> list[dict[str:any]]:
    """
    Processes and resolves the given servers in case the server URL uses a template.
    For example: `url: '{protocol}://api.example.com'`
    In such case in addition to the `url` object there is also a `variables` object.
    Each template variable is a dictionary entry in `variables` that includes
    a `default` entry that can be used to fill the variable name.

    Args:
        servers (list): A list of server dictionaries (from the spec), each containing details about an API server.
    Returns:
        list: A list of resolved server dictionaries.
    """
    resolved_servers = []
    for server in servers:
        url_template = server.get("url", "")
        description = server.get("description", "")
        variables = server.get("variables", {})

        # Resolve the URL with variables
        resolved_url = resolve_url(url_template, variables)

        resolved_servers.append({"description": description, "url": resolved_url})

    return resolved_servers


def resolve_url(url_template: str, variables: dict[str, any]) -> str:
    """Replaces placeholders in the URL with default values from variables."""
    resolved_url = url_template

    # Find all placeholders in the URL
    placeholders = re.findall(r"\{(.*?)\}", url_template)

    # Replace each placeholder with its default value
    for placeholder in placeholders:
        default_value = variables.get(placeholder, {}).get("default", f"{{{placeholder}}}")
        resolved_url = resolved_url.replace(f"{{{placeholder}}}", default_value)

    return resolved_url


def add_app_inst_servers_to_spec(
    con_spec: ConnectorSpec,
    app_inst: AppInstance,
) -> None:
    """Add base URL to a connector specification.

    Args:
        con_spec (ConnectorSpec): Connector spec to add instance details to.
        app_inst (AppInstance): Source application instance details
            to add to connector specification.
    """
    con_spec.servers = [Server(url=app_inst.base_url)]
