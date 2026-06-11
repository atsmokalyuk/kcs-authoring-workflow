"""Contract validation errors for KCS packet payloads."""


class ContractValidationError(ValueError):
    """Raised when a packet payload does not match the KCS-1 contract."""
