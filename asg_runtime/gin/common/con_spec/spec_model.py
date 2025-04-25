import yaml
from pydantic import BaseModel, ConfigDict, Field

from .spec_helper_models import Call, Metadata, Server


# This is the base of the connector specification
class ConnectorSpec(BaseModel):
    """Connector specification."""

    model_config = ConfigDict(
        title="GIN Connector",
        validate_assignment=True,
        validate_default=True,
        use_attribute_docstrings=True,
    )

    api_version: str = Field("connector/v1", alias="apiVersion")
    kind: str = "connector/v1"
    metadata: Metadata
    spec: Call
    servers: list[Server] | None = None

    @classmethod
    def from_file(cls, file_path: str) -> "ConnectorSpec":
        """
        Import connector specification file.

        Args:
            file_path (str): Path to connector specification file.

        Returns:
            ConnectorSpec: Connector specification.
        """
        with open(file_path, encoding="UTF-8") as file:
            connector = cls.from_string(file.read())
        return connector

    @classmethod
    def from_string(cls, connector_spec: str) -> "ConnectorSpec":
        """
        Import connector specification from YAML string.

        Args:
            connector_spec (str): string containing the connector specification.

        Returns:
            ConnectorSpec: Connector specification.
        """
        conn_spec_dict = yaml.safe_load(connector_spec)
        connector = ConnectorSpec(**conn_spec_dict)

        return connector

    def to_file(self, file_path: str) -> None:
        """
        Export connector specification to a file.

        Args:
            connector (ConnectorSpec): Connector specification.
            file_path (str): Path to output connector specification file.
        """
        with open(file_path, "w", encoding="UTF-8") as file:
            yaml.dump(self.model_dump(by_alias=True, mode="json"), file)
