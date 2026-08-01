"""AutoFlow AI - gRPC transport (generated from metadata).

gRPC client shim. Uses ``grpcio`` when available; otherwise raises a
clear error at call time (import-safe without the dependency).
"""

from typing import Any, Dict, List, Optional


class GRPCTransport:
    """Minimal gRPC channel wrapper."""

    def __init__(self, endpoint: str = "",
                 proto_path: str = "",
                 service_name: str = "",
                 tls: bool = False,
                 api_key: str = "") -> None:
        self.endpoint = endpoint
        self.proto_path = proto_path
        self.service_name = service_name
        self.tls = tls
        self.api_key = api_key
        self._channel = None
        self._stub = None
        self._grpc = None
        try:
            import grpc  # type: ignore
            self._grpc = grpc
        except ImportError:  # pragma: no cover - optional dependency
            self._grpc = None

    def connect(self) -> None:
        if self._grpc is None:
            raise RuntimeError("grpcio is not installed")
        import grpc as g  # noqa: F811 - local alias
        creds = g.secure_channel_credentials if self.tls else None
        if creds is not None:
            self._channel = g.secure_channel(self.endpoint, creds)
        else:
            self._channel = g.insecure_channel(self.endpoint)

    def _metadata(self) -> List[tuple]:
        if self.api_key:
            return [("authorization", f"Bearer {self.api_key}")]
        return []

    def unary_call(self, method: str, request: dict) -> dict:
        """Invoke a unary method; requires a compiled proto service."""
        raise NotImplementedError(
            "gRPC unary_call requires a compiled proto stub; "
            "wire the generated client via GRPCTransport.")

    def close(self) -> None:
        if self._channel is not None:
            self._channel.close()
            self._channel = None

    def set_default_header(self, name: str, value: str) -> None:
        pass

    def set_default_query_param(self, name: str, value: str) -> None:
        pass
