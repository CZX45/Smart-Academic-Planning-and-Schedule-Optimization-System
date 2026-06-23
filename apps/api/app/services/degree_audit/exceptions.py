class DegreeAuditError(Exception):
    """Base error for degree audit service failures."""


class DegreeAuditValidationError(DegreeAuditError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
