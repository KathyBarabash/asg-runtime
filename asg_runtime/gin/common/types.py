"""
Common types.

Currently these are just type aliases which serve to make type hints more
descriptive.
"""

import os
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, ConfigDict, Secret, SecretStr, model_validator
from varsubst import exceptions, varsubst


class Platform(StrEnum):
    """AI model hosting platform identifier"""

    BAM = auto()
    RITS = auto()
    WATSONX = auto()
    RITS_OPENAI = auto()
    OPENAI = auto()


class ModelType(StrEnum):
    """Model type identifier"""

    LLM = auto()
    EMBEDDINGS = auto()


class ModelPurpose(StrEnum):
    """Used to pick LLM type"""

    EVAL = auto()
    API_GEN = auto()


class PlatformCredentials(BaseModel):
    """Credentials for accessing model platforms."""

    model_config = ConfigDict(
        title="Credentials for accessing model platforms.",
        validate_assignment=True,
        validate_default=True,
        use_attribute_docstrings=True,
        protected_namespaces=("x_"),
    )

    api_key: SecretStr
    """API key for model platform."""

    api_base: str | None = None
    """API endpoint for model platform."""

    api_project_id: str | None = None
    """Project ID for model platform."""

    @model_validator(mode="after")
    def resolve_env_references(cls, values):
        """
        Replace any SecretStr fields containing environment variable references with
        the corresponding value from the environment.
        """
        for field_name in values.__fields_set__:
            field_value = getattr(values, field_name)
            if isinstance(field_value, SecretStr):
                secret_value = field_value.get_secret_value()
                if secret_value.startswith("$") and secret_value.endswith(""):
                    env_var = secret_value[1:]
                    new_value = os.getenv(env_var)
                    if new_value:
                        setattr(values, field_name, SecretStr(new_value))  # Update field directly
        return values


class ModelDef(BaseModel):
    """Data structure describing what model to use and how to use it."""

    model_config = ConfigDict(
        title="Model Definition",
        validate_assignment=True,
        validate_default=True,
        use_attribute_docstrings=True,
        protected_namespaces=("x_"),
    )

    model_id: str
    """Model to use."""

    credentials: PlatformCredentials
    """Credentials for model platform."""

    platform: Platform
    """Hosting platform for model."""

    model_type: ModelType | None
    """Type of model to use."""

    model_params: dict[str, Any] | None = None
    """Parameters for LLM."""


class HTTPParamLocation(StrEnum):
    """Possible locations for parameters in REST API calls."""

    QUERY = auto()
    HEADER = auto()
    PATH = auto()
    COOKIE = auto()


class HTTPMethod(StrEnum):
    """HTTP methods. Only the RESTful methods are currently supported."""

    DELETE = auto()
    GET = auto()
    POST = auto()
    PUT = auto()


class HTTPMeta(BaseModel):
    """HTTP protocol details required to fulfill request, beyond what is needed
    for the tool calling workflow to know about."""

    endpoint: str
    """URL endpoint for call."""

    method: HTTPMethod
    """HTTP method to use."""

    auth_type: list | None = None

    output_schema: dict | None = None

    servers: list | None = None


class APITypes(StrEnum):
    """API types."""

    REST = auto()
    """RESTful API."""

    FUNCTION = auto()
    """Function call (Python, etc.)."""


class ToolDetails(BaseModel, extra="forbid"):
    """Details about a tool (function call)."""

    name: str
    """Tool Name."""

    parameters: dict[str, Any] | None = {}
    """Tool parameter details."""

    description: str
    """Tool description."""

    api_type: APITypes
    """Type of API this tool is a part of."""

    call_meta: HTTPMeta | None = None
    """Metadata about calling the tool which is ignored during inferencing of
    tool calls, but may be needed during actual execution. Only HTTP protocol
    related information is supported, but this could be expanded to other
    protocols in the future."""


class EnvToken(Secret[str]):
    """An implementation for token where the token itself is stores as an
    environment variable."""

    def _display(self) -> str:
        return super().get_secret_value()

    def get_secret_value(self) -> str:
        value = super().get_secret_value()
        try:
            value = varsubst(value)
        except AttributeError:
            # The attribute referred in 'fieldname' is not define in the
            # configuration class instance, skipping.
            pass
        except exceptions.KeyUnresolvedException:
            # The environment variable that was referred in the configuration
            # is not defined, skipping.
            pass
        return value

    def get_raw_value(self) -> str:
        """Get stored value, without substituting if an environment variable."""
        return super().get_secret_value()


class ApiCallInf(BaseModel):
    """API call descriptor, from LLM inference."""

    model_config = ConfigDict(
        title="API call descriptor",
        validate_assignment=True,
        validate_default=True,
        use_attribute_docstrings=True,
    )

    raw_str: str
    """Raw substring from LLM inference that describes this API call."""

    valid: bool = True
    """Boolean for whether the details of this call should be trusted to function."""

    name: str = ""
    """API call to make."""

    parameters: dict[str, Any] = {}
    """Parameters to API call."""


class AuthType(StrEnum):
    """
    Enumeration of security types.

    Attributes
        API_KEY: str
        BEARER: str
        NO_AUTH: str
    """

    API_KEY = auto()
    "API key authorization"

    BEARER = auto()
    "HTTP bearer authentication"

    NO_AUTH = auto()
    "No authorization"


class App(BaseModel):
    """Application details."""

    app_id: int
    """Unique application ID number."""

    title: str
    """Title of application."""

    version: str
    """Version of application."""

    api_spec: str
    """API specification"""


class AppInstance(BaseModel):
    """Application instance details."""

    inst_id: int
    """Unique instance ID number."""

    description: str
    """Description of instance."""

    app_id: int
    """Application ID associated with instance."""

    base_url: str
    """Base URL to associated application instance."""

    auth_type: AuthType
    """Type of authentication."""

    auth_name: str
    """Authentication name"""

    auth_scheme: str
    """Authentication schema"""

    key_envar: EnvToken
    """API key/Bearer environment variable."""
