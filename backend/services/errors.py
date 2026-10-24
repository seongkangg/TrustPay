"""Service-level errors, mapped to the JSON error format in docs/api-contracts.md by main.py."""


class ServiceError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(
        self, message: str, *, invoice_id: str | None = None, correlation_id: str | None = None
    ):
        super().__init__(message)
        self.message = message
        self.invoice_id = invoice_id
        self.correlation_id = correlation_id


class NotFoundError(ServiceError):
    status_code = 404
    code = "NOT_FOUND"


class InvalidStateError(ServiceError):
    status_code = 409
    code = "INVALID_TRANSITION"


class ForbiddenError(ServiceError):
    status_code = 403
    code = "FORBIDDEN"


class UpstreamUnavailableError(ServiceError):
    status_code = 503
    code = "MOCK_SYSTEM_UNAVAILABLE"
