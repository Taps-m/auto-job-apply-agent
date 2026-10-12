class ServiceError(Exception):
    """A user-facing error with an HTTP status and optional data (e.g. the id of a duplicate)."""

    def __init__(self, message: str, status: int = 400, data: dict | None = None):
        super().__init__(message)
        self.status = status
        self.data = data or {}
