import inspect
import re

from asg_runtime.gin.common.types import APITypes, ToolDetails

# List to store all the tool metadata
tool_metadata_list: list[ToolDetails] = []


def make_tool(func):
    """Decorator to capture tool metadata from the function docstring."""
    tool_name = func.__name__
    docstring = func.__doc__
    if docstring is None:
        print(f"Function {tool_name} has no docstring.")
        return func
    # Extract description and args section
    description_match = re.search(r"^\s*(.*?)\n\s*Args\s*:(.*?)$", docstring, re.DOTALL)
    if description_match:
        tool_description = description_match.group(1).strip()
        args_section = description_match.group(2).strip()

        # Extract parameter details
        params = {}
        for param_match in re.findall(
            r"(\w+)\s*\(([\w\s]+)\)\s*:\s*(.*?)(?=\n\s+\w|\s*$)",
            args_section,
            re.DOTALL,
        ):
            param_name = param_match[0].strip()
            param_type = param_match[1].strip()
            param_description = param_match[2].strip()
            params[param_name] = {
                "type": param_type,
                "description": param_description,
            }

    # Extract required arguments from signature
    required = []
    sig = inspect.signature(func)
    for param_name, param in sig.parameters.items():
        # Add to required list if the parameter has no default value
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    params["required"] = required
    tool_data = ToolDetails(
        name=tool_name,
        parameters=params,
        description=tool_description,
        api_type=APITypes.FUNCTION,
    )

    if tool_data not in tool_metadata_list:
        # Add to the global list
        tool_metadata_list.append(tool_data)
    return func
