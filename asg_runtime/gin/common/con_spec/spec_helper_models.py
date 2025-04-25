from enum import Enum, StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field


class ArgSourceEnum(str, Enum):
    """
    ArgSourceEnum is an enumerated type that represents the source of an argument value

    Attributes
        CONSTANT: str
            The argument value is a constant defined in the user's input utterance.
        RUNTIME: str
            The argument value is provided at runtime as an input to the call.
        REFERENCE: str
            The argument value is obtained by referencing an API call or env variable.
    """

    CONSTANT = "constant"
    RUNTIME = "runtime"
    REFERENCE = "reference"


class ArgLocationEnum(str, Enum):
    """
    ArgLocationEnum is an enumerated type that represents how the argument should be passed to the API.

    Attributes
        PARAMETER: str
            The argument value is a path or query string parameter to the API.
        HEADER: str
            The argument value is a header to the API.
        DATA: str
            The argument value is a data argument to the API.
    """

    PARAMETER = "parameter"
    HEADER = "header"
    DATA = "data"


class MethodEnum(str, Enum):
    """
    MethodEnum is an enumerated type that represents the type of HTTP method to use.

    Attributes
        POST: str
            The argument value is an HTTP POST method.
        GET: str
            The argument value is an HTTP GET method.
        PUT: str
            The argument value is an HTTP PUT method.
    """

    POST = "post"
    GET = "get"
    PUT = "put"


class PaginationTypeEnum(StrEnum):
    """
    Enumeration of supported pagination methods

    Attributes
        PAGE: str
            Page-based pagination
        CURSOR: str
            Cursor pagination
        OFFSET: str
            Offset pagination
        KEYSET: str
            Keyset (seek) pagination
        SEEK: str
            Synonym for KEYSET
        TIME: str
            Time-based pagination

    """

    PAGE = auto()
    CURSOR = auto()
    OFFSET = auto()
    KEYSET = auto()
    SEEK = KEYSET
    TIME = auto()


class CallTypeEnum(StrEnum):
    """
    Enumeration of call types.

    Attributes
        URL: str
            Call is a URL
    """

    URL = auto()


class RuntimeTypeEnum(StrEnum):
    """
    Enumeration of runtime types.

    Attributes
        PYTHON: str
            Connector is to be executed with Python runtime
    """

    PYTHON = auto()


class ArgTypeEnum(StrEnum):
    """
    Enumeration of argument types.

    Attributes
        ANY: str
        ARRAY: str
        ARRAYLIST: str
        BIGINT: str
        BOOL: str
        BOOLEAN: str
        BYTE: str
        CHAR: str
        DICT: str
        DOUBLE: str
        FLOAT: str
        HASHTABLE: str
        HASHMAP: str
        INTEGER: str
        LIST: str
        LONG: str
        NUMBER: str
        NULL: str
        OBJECT: str
        QUEUE: str
        STACK: str
        SHORT: str
        STRING: str
        TUPLE: str
    """

    ANY = auto()
    ARRAY = auto()
    ARRAYLIST = auto()
    BIGINT = auto()
    BOOL = auto()
    BOOLEAN = auto()
    BYTE = auto()
    CHAR = auto()
    DICT = auto()
    DOUBLE = auto()
    FLOAT = auto()
    HASHTABLE = auto()
    HASHMAP = auto()
    INTEGER = auto()
    LIST = auto()
    LONG = auto()
    NUMBER = auto()
    NULL = auto()
    OBJECT = auto()
    QUEUE = auto()
    STACK = auto()
    SHORT = auto()
    STRING = auto()
    TUPLE = auto()


class Metadata(BaseModel):
    name: str = "TBD"
    description: str = "TBD"
    input_prompt: str | None = Field(default=None, alias="inputPrompt")


class Dataset(BaseModel):
    """
    The Dataset object describes what is the api call output and how to obtain it.
    Attributes
        api: API name to get the output from.
        path: a string describing the json path to the output data.
        metadata: additional fields (metadata) that should be appended into the output.
    """

    api: str
    path: str | None = ""
    metadata: list[str] | None = None


class TransformFunction(BaseModel):
    """
    The TransformFunction object describes a transformation function.
    Attributes
        function: name of the function.
        description: function description.
        params: Dict of parameters that the transform function needs, key is parameter name in the function, value is the parameter value.
        output: the field name of the function's output, which can be referenced in proceeding functions.
    """

    function: str
    description: str | None = ""
    params: dict[str, Any] | None = None
    output: str | None = ""


class ProcessDataSet(BaseModel):
    """
    The ProcessDataSet object describes how to generate the output dataframe.
    Attributes
        dataframe: input dataset name to use in the transformation.
        fields: Dict that represents the transformation for each field in the output dataset.
    """

    dataframe: str
    fields: dict[str, list[TransformFunction]]


class Output(BaseModel):
    """
    The Output object describes how to handle the output of the API calls

    Attributes
        data: A dictionary mapping output dataframes to their sources in the API outputs.
        execution: TBD.
        runtime_type: A string representing the type of runtime used to execute the cell (e.g., "python").
        exports: Descriptive object on how to generate the output dataset, key is the name of the output dataframe,
                   value is the transformation logic that needs to be executed to reach a target schema.
    """

    data: dict[str, Dataset] | None = None
    execution: str = ""
    runtime_type: RuntimeTypeEnum = Field(default=RuntimeTypeEnum.PYTHON, alias="runtimeType")
    exports: dict[str, ProcessDataSet] | None = None


class Argument(BaseModel):
    name: str
    argLocation: ArgLocationEnum
    type: ArgTypeEnum
    source: ArgSourceEnum
    value: Any


class PagingParamDirectory(BaseModel):
    # Name of key in pagination_params dict that gives page number
    pageRef: str
    # Path in response data to page size number
    pageSizePath: str
    # Path in response data to total data size number
    totalSizePath: str


class Pagination(BaseModel):
    type: PaginationTypeEnum | None = None
    # If a response contains a URL to the next block of paginated data, this
    # field contains the path within the response data to the URL for the next
    # block. If this is provided, no other fields are necessary for determining
    # how to access the next set of data, just execute on this URL until the
    # response data no longer has this path.
    next_path: str | None = Field(default=None, alias="nextPath")
    # Dictionary containing key names equal to a required query parameter(s) to
    # access the next block of paginated data, and values equal to the path for
    # where to find those values in the latest set of response data.
    # Depending on the pagination type, some of these parameters may be handled
    # in special ways (like determining how many blocks of data exist, and
    # where we exist in those blocks).
    pagination_params: dict[str, Any] | None = Field(default=None, alias="paginationParams")
    # This maps parameters needed to implement a certain type of paging
    param_translation: PagingParamDirectory | None = Field(
        default=None, alias="paramTranslation"
    )


class ApiCall(BaseModel):
    type: CallTypeEnum
    endpoint: str
    method: MethodEnum
    arguments: list[Argument] | None = None
    pagination: Pagination | None = None


class Call(BaseModel):
    apicalls: dict[str, ApiCall] = Field(alias="apiCalls")
    output: Output
    timeout: int | None = 60


class Server(BaseModel):
    url: str
    description: str | None = None
