from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from typing import Protocol
from uuid import UUID

from app.models.academic import (
    ScenarioAllocationType,
    ScenarioRelationshipType,
    SourceType,
)

ZERO = Decimal("0.0")
SourceKey = tuple[str, UUID]


@dataclass(frozen=True)
class AllocationCandidate:
    candidate_id: UUID
    source_key: SourceKey
    course_id: UUID | None
    course_code: str
    program_version_id: UUID
    relationship_type: ScenarioRelationshipType
    requirement_node_id: UUID
    requirement_code: str
    requirement_display_order: int
    requirement_allows_overlap: bool
    program_priority: int
    credit_amount: Decimal
    is_earned: bool
    is_completed: bool
    is_in_progress: bool
    is_planned: bool
    attempt_number: int
    explanation: str
    student_course_attempt_id: UUID | None = None
    transfer_credit_id: UUID | None = None
    course_waiver_id: UUID | None = None
    course_substitution_id: UUID | None = None


@dataclass(frozen=True)
class ProgramCombinationPolicy:
    primary_program_version_id: UUID
    secondary_program_version_id: UUID
    relationship_type: ScenarioRelationshipType
    maximum_shared_credits: Decimal
    minimum_unique_secondary_credits: Decimal
    minimum_unique_courses: int
    allows_double_counting: bool
    requires_manual_confirmation: bool
    source_type: SourceType
    is_official: bool


@dataclass(frozen=True)
class AllocationObjective:
    satisfied_required_requirements: int
    satisfied_required_credits: Decimal
    remaining_required_credits: Decimal
    shared_credits: Decimal
    unique_secondary_credits: Decimal
    total_earned_credits: Decimal
    manual_review_allocations: int

    def score(self) -> tuple[int, Decimal, Decimal, Decimal, Decimal, int]:
        return (
            self.satisfied_required_requirements,
            self.unique_secondary_credits,
            self.satisfied_required_credits,
            -self.remaining_required_credits,
            -self.shared_credits,
            -self.manual_review_allocations,
        )


@dataclass(frozen=True)
class CandidateAllocation:
    candidate: AllocationCandidate
    allocation_type: ScenarioAllocationType
    is_selected: bool
    is_shared: bool
    is_unique_to_program: bool
    allocation_rank: int
    reason_code: str
    explanation: str

    @property
    def candidate_id(self) -> UUID:
        return self.candidate.candidate_id


@dataclass(frozen=True)
class AllocationResult:
    allocations: list[CandidateAllocation]
    objective: AllocationObjective
    search_limit_reached: bool


class MultiProgramAllocator(Protocol):
    def allocate(
        self,
        candidates: Sequence[AllocationCandidate],
        policies: Sequence[ProgramCombinationPolicy],
    ) -> AllocationResult: ...


class DeterministicMultiProgramAllocator:
    def __init__(self, search_limit: int = 4096) -> None:
        self._search_limit = search_limit

    def allocate(
        self,
        candidates: Sequence[AllocationCandidate],
        policies: Sequence[ProgramCombinationPolicy],
    ) -> AllocationResult:
        ordered_candidates = sorted(candidates, key=candidate_sort_key)
        if not ordered_candidates:
            return AllocationResult(
                allocations=[],
                objective=AllocationObjective(0, ZERO, ZERO, ZERO, ZERO, ZERO, 0),
                search_limit_reached=False,
            )

        policy_map = {
            (
                policy.primary_program_version_id,
                policy.secondary_program_version_id,
                policy.relationship_type,
            ): policy
            for policy in policies
        }
        choices_by_source = self._choices_by_source(ordered_candidates, policy_map)
        best_selection: tuple[AllocationCandidate, ...] = ()
        best_objective = AllocationObjective(0, ZERO, ZERO, ZERO, ZERO, ZERO, 0)
        best_tie = tuple[str, ...]()
        evaluated = 0
        limit_reached = False

        def visit(
            source_index: int,
            selected: tuple[AllocationCandidate, ...],
        ) -> None:
            nonlocal best_selection, best_objective, best_tie, evaluated, limit_reached
            if evaluated >= self._search_limit:
                limit_reached = True
                return
            if source_index >= len(choices_by_source):
                evaluated += 1
                if not self._is_valid_selection(selected, policy_map):
                    return
                objective = objective_for(selected, policy_map)
                tie = tuple(stable_candidate_key(candidate) for candidate in selected)
                if objective.score() > best_objective.score() or (
                    objective.score() == best_objective.score() and tie < best_tie
                ):
                    best_selection = selected
                    best_objective = objective
                    best_tie = tie
                return
            for choice in choices_by_source[source_index]:
                if evaluated >= self._search_limit:
                    limit_reached = True
                    return
                visit(source_index + 1, selected + choice)

        visit(0, ())
        selected_ids = {candidate.candidate_id for candidate in best_selection}
        shared_sources = sources_used_more_than_once(best_selection)
        allocations: list[CandidateAllocation] = []
        rank = 0
        for candidate in ordered_candidates:
            is_selected = candidate.candidate_id in selected_ids
            is_shared = is_selected and candidate.source_key in shared_sources
            if not is_selected:
                allocation_type = ScenarioAllocationType.UNALLOCATED
                reason_code = "NOT_SELECTED_BY_GLOBAL_OBJECTIVE"
                explanation = "Candidate was not selected by the global scenario allocation."
            elif is_shared:
                allocation_type = ScenarioAllocationType.SHARED
                reason_code = "SHARED_BY_RULE"
                explanation = (
                    "Course is shared because the requirement and directional "
                    "program-combination rule allow overlap."
                )
            elif candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR:
                allocation_type = ScenarioAllocationType.PRIMARY
                reason_code = "PRIMARY_REQUIREMENT_ALLOCATION"
                explanation = "Course is allocated to the primary major requirement."
            else:
                allocation_type = ScenarioAllocationType.UNIQUE_SECONDARY
                reason_code = "UNIQUE_SECONDARY_CREDIT"
                explanation = "Course is allocated uniquely to the secondary program."
            allocations.append(
                CandidateAllocation(
                    candidate=candidate,
                    allocation_type=allocation_type,
                    is_selected=is_selected,
                    is_shared=is_shared,
                    is_unique_to_program=(
                        is_selected
                        and not is_shared
                        and candidate.relationship_type
                        is not ScenarioRelationshipType.PRIMARY_MAJOR
                    ),
                    allocation_rank=rank if is_selected else len(ordered_candidates) + rank,
                    reason_code=reason_code,
                    explanation=explanation,
                )
            )
            rank += 1
        return AllocationResult(
            allocations=sorted(allocations, key=lambda allocation: allocation.allocation_rank),
            objective=best_objective,
            search_limit_reached=limit_reached,
        )

    def _choices_by_source(
        self,
        candidates: Sequence[AllocationCandidate],
        policy_map: dict[
            tuple[UUID, UUID, ScenarioRelationshipType],
            ProgramCombinationPolicy,
        ],
    ) -> list[list[tuple[AllocationCandidate, ...]]]:
        by_source: dict[SourceKey, list[AllocationCandidate]] = defaultdict(list)
        for candidate in candidates:
            by_source[candidate.source_key].append(candidate)

        choices: list[list[tuple[AllocationCandidate, ...]]] = []
        for source_key in sorted(by_source):
            source_candidates = sorted(by_source[source_key], key=candidate_sort_key)
            source_choices: list[tuple[AllocationCandidate, ...]] = [()]
            source_choices.extend((candidate,) for candidate in source_candidates)
            for left, right in combinations(source_candidates, 2):
                pair = (left, right)
                if is_shareable(pair, policy_map):
                    source_choices.append(pair)
            choices.append(
                sorted(
                    source_choices,
                    key=lambda choice: tuple(
                        stable_candidate_key(candidate) for candidate in choice
                    ),
                )
            )
        return choices

    def _is_valid_selection(
        self,
        selected: Sequence[AllocationCandidate],
        policy_map: dict[
            tuple[UUID, UUID, ScenarioRelationshipType],
            ProgramCombinationPolicy,
        ],
    ) -> bool:
        requirement_ids: set[UUID] = set()
        for candidate in selected:
            if candidate.requirement_node_id in requirement_ids:
                return False
            requirement_ids.add(candidate.requirement_node_id)

        by_source: dict[SourceKey, list[AllocationCandidate]] = defaultdict(list)
        for candidate in selected:
            by_source[candidate.source_key].append(candidate)
        for source_candidates in by_source.values():
            if len(source_candidates) > 1 and not is_shareable(source_candidates, policy_map):
                return False

        shared_by_policy: dict[tuple[UUID, UUID, ScenarioRelationshipType], Decimal] = defaultdict(
            lambda: ZERO
        )
        for source_candidates in by_source.values():
            if len(source_candidates) <= 1:
                continue
            primary = next(
                candidate
                for candidate in source_candidates
                if candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
            )
            for secondary in source_candidates:
                if secondary is primary:
                    continue
                key = (
                    primary.program_version_id,
                    secondary.program_version_id,
                    secondary.relationship_type,
                )
                shared_by_policy[key] += secondary.credit_amount if secondary.is_earned else ZERO
        return all(
            shared_credits <= policy_map[key].maximum_shared_credits
            for key, shared_credits in shared_by_policy.items()
        )


def is_shareable(
    candidates: Sequence[AllocationCandidate],
    policy_map: dict[tuple[UUID, UUID, ScenarioRelationshipType], ProgramCombinationPolicy],
) -> bool:
    if len(candidates) < 2:
        return False
    if not all(
        candidate.requirement_allows_overlap and candidate.is_earned for candidate in candidates
    ):
        return False
    primary = [
        candidate
        for candidate in candidates
        if candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
    ]
    if len(primary) != 1:
        return False
    primary_candidate = primary[0]
    for candidate in candidates:
        if candidate is primary_candidate:
            continue
        policy = policy_map.get(
            (
                primary_candidate.program_version_id,
                candidate.program_version_id,
                candidate.relationship_type,
            )
        )
        if policy is None or not policy.allows_double_counting:
            return False
    return True


def objective_for(
    selected: Sequence[AllocationCandidate],
    policy_map: dict[tuple[UUID, UUID, ScenarioRelationshipType], ProgramCombinationPolicy],
) -> AllocationObjective:
    selected_sources = {candidate.source_key for candidate in selected if candidate.is_earned}
    shared_sources = sources_used_more_than_once(selected)
    shared_credits = sum(
        (
            max(candidate.credit_amount for candidate in selected if candidate.source_key == source)
            for source in shared_sources
        ),
        ZERO,
    )
    unique_secondary_credits = sum(
        (
            candidate.credit_amount
            for candidate in selected
            if candidate.relationship_type is not ScenarioRelationshipType.PRIMARY_MAJOR
            and candidate.source_key not in shared_sources
            and candidate.is_earned
        ),
        ZERO,
    )
    manual_review_allocations = 0
    for candidate in selected:
        if candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR:
            continue
        primary = next(
            (
                primary_candidate
                for primary_candidate in selected
                if primary_candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
            ),
            None,
        )
        if primary is None:
            continue
        policy = policy_map.get(
            (
                primary.program_version_id,
                candidate.program_version_id,
                candidate.relationship_type,
            )
        )
        if policy is None or policy.requires_manual_confirmation:
            manual_review_allocations += 1
    return AllocationObjective(
        satisfied_required_requirements=len(selected),
        satisfied_required_credits=sum((candidate.credit_amount for candidate in selected), ZERO),
        remaining_required_credits=ZERO,
        shared_credits=shared_credits,
        unique_secondary_credits=unique_secondary_credits,
        total_earned_credits=sum(
            (
                max(
                    candidate.credit_amount
                    for candidate in selected
                    if candidate.source_key == source
                )
                for source in selected_sources
            ),
            ZERO,
        ),
        manual_review_allocations=manual_review_allocations,
    )


def sources_used_more_than_once(candidates: Sequence[AllocationCandidate]) -> set[SourceKey]:
    counts: dict[SourceKey, int] = defaultdict(int)
    for candidate in candidates:
        counts[candidate.source_key] += 1
    return {source_key for source_key, count in counts.items() if count > 1}


def candidate_sort_key(candidate: AllocationCandidate) -> tuple[int, int, int, str, str, int, str]:
    return (
        candidate.program_priority,
        0 if candidate.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR else 1,
        candidate.requirement_display_order,
        candidate.requirement_code,
        candidate.course_code,
        candidate.attempt_number,
        str(candidate.candidate_id),
    )


def stable_candidate_key(candidate: AllocationCandidate) -> str:
    return "|".join(str(part) for part in candidate_sort_key(candidate))
