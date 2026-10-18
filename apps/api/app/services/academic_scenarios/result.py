from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.models.academic import ScenarioRelationshipType


@dataclass(frozen=True)
class ScenarioProgramInput:
    program_version_id: UUID
    relationship_type: ScenarioRelationshipType
    priority: int
