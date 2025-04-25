import re
from typing import Any

from asg_runtime.gin.common.types import EnvToken


def replace_env_var(match: re.Match) -> str:
    var_name = match.group()
    return EnvToken(var_name).get_secret_value()


# from langchain_core.documents.base import Document
# def get_details_for_call(
#     call_name: str, context: list[Document]
# ) -> ToolDetails | None:
#     """
#     Given a context with a list of Documents, find the document containing
#     details of a particular API call, and return those details.

#     Args:
#         call_name (str): API call name
#         context (list[Document]): Context with list of Documents.

#     Returns:
#         ToolDetails | None: Document for desired API call, if it exists.
#     """
#     base_log = logging.getLogger(Logging.BASE)
#     for doc in context:
#         # De-serialize into a ToolDetails object
#         tool_details_dict = json.loads(doc.metadata["tool_details_str"])
#         tool_details = ToolDetails(**tool_details_dict)
#         if call_name == tool_details.name:
#             base_log.debug("Context doc for call %s: %s", call_name, doc)
#             return tool_details
#     base_log.warning("%s can't be found in context", call_name)
#     return None


def get_fstring_kwords(string: str) -> list[str]:
    """
    Get keywords to an f-string.

    Args:
        string (str): f-string with keyword slots.

    Returns:
        list: Keywords to f-string.
    """
    kwords = []
    # Split on instances of right brace, drop anything before the brace.
    for substr in string.split("{")[1:]:
        if "}" not in substr:
            continue
        kw = substr.split("}", 1)[0]
        if kw != "":
            kwords.append(kw)
    return kwords


def retrieve_value_from_json_path(data: dict, path: str) -> Any | None:
    """
    Traverse the dictionary in the data argument to obtain the value
    referenced in the provided path argument.
    It allows retrieval of a value from a json dictionary, where path is a
    json path.

    Args:
        data (dict): Data to pull a value from
        path (str): Path to value, given as dot separated keys.

    Returns:
        Any | None: Value, or None if path doesn't exist.
    """
    # data is a nested dict, and we will continually redefine subdata as a
    # subordinate dict as we index through the path defined in path.
    # Ultimately subdata will become the value we are after, or otherwise
    # None if it doesn't exist.
    subdata = data
    for key in path.split("."):
        subdata = subdata.get(key, None)
        if not subdata:
            return None
    return subdata
