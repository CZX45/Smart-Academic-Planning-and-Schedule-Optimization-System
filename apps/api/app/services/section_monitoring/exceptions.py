from dataclasses import dataclass


@dataclass(frozen=True)
class SectionMonitoringValidationError(Exception):
    code: str
    message: str
