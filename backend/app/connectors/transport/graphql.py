"""AutoFlow AI - GraphQL transport (generated from metadata)."""

from typing import Any, Dict, Optional

from app.connectors.transport.http import HTTPTransport


class GraphQLTransport:
    """GraphQL client over the HTTP transport."""

    def __init__(self, endpoint: str = "",
                 http: Optional[HTTPTransport] = None,
                 headers: Optional[Dict[str, str]] = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.http = http or HTTPTransport(base_url="",
                                          default_headers=headers)

    def set_default_header(self, name: str, value: str) -> None:
        self.http.set_default_header(name, value)

    def set_default_query_param(self, name: str, value: str) -> None:
        self.http.set_default_query_param(name, value)

    def execute(self, query: str, variables: Optional[dict] = None,
                operation_name: str = "") -> dict:
        """Execute a GraphQL query or mutation."""
        payload: Dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            payload["operationName"] = operation_name
        result = self.http.request("POST", self.endpoint, json_body=payload)
        if isinstance(result, dict) and result.get("errors"):
            raise ValueError(f"graphql error: {result['errors']}")
        return result if isinstance(result, dict) else {}

    def query(self, query: str, variables: Optional[dict] = None) -> dict:
        return self.execute(query, variables=variables)

    def mutation(self, query: str, variables: Optional[dict] = None) -> dict:
        return self.execute(query, variables=variables)

    def introspection(self, include_deprecated: bool = True) -> dict:
        """Fetch the GraphQL schema via introspection query."""
        query = """query IntrospectionQuery($inc: Boolean!) {
          __schema {
            types {
              name
              kind
              fields(includeDeprecated: $inc) { name }
            }
          }
        }"""
        return self.execute(query, {"inc": include_deprecated})

    def request(self, method: str, url: str, **kwargs: Any) -> dict:
        """Compat shim so auth strategies can attach headers."""
        return self.http.request(method, url, **kwargs)
