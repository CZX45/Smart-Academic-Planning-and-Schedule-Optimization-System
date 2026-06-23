from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from app.models.academic import CourseRuleExpression, CourseRuleExpressionNodeType


class CourseRuleExpressionValidationError(ValueError):
    """Raised when a stored course-rule expression tree is structurally invalid."""


OPERATOR_NODES = {
    CourseRuleExpressionNodeType.AND,
    CourseRuleExpressionNodeType.OR,
    CourseRuleExpressionNodeType.NOT,
}


def validate_course_rule_expression_tree(nodes: Sequence[CourseRuleExpression]) -> None:
    if not nodes:
        raise CourseRuleExpressionValidationError("Course rule expression tree requires a root.")

    rule_ids = {node.course_rule_id for node in nodes}
    if len(rule_ids) != 1:
        raise CourseRuleExpressionValidationError("Expression nodes must belong to one rule.")

    nodes_by_id = {node.id: node for node in nodes}
    if len(nodes_by_id) != len(nodes):
        raise CourseRuleExpressionValidationError("Expression node IDs must be unique.")

    roots = [node for node in nodes if node.parent_id is None]
    if len(roots) != 1:
        raise CourseRuleExpressionValidationError("Expression tree must have exactly one root.")

    children_by_parent: dict[UUID, list[CourseRuleExpression]] = defaultdict(list)
    for node in nodes:
        if node.parent_id is None:
            continue
        if node.parent_id == node.id:
            raise CourseRuleExpressionValidationError("Expression node cannot parent itself.")
        if node.parent_id not in nodes_by_id:
            raise CourseRuleExpressionValidationError("Expression parent must be in the tree.")
        children_by_parent[node.parent_id].append(node)

    for node in nodes:
        child_count = len(children_by_parent[node.id])
        if node.node_type is CourseRuleExpressionNodeType.NOT and child_count != 1:
            raise CourseRuleExpressionValidationError("NOT expression nodes must have one child.")
        if (
            node.node_type
            in {
                CourseRuleExpressionNodeType.AND,
                CourseRuleExpressionNodeType.OR,
            }
            and child_count < 2
        ):
            raise CourseRuleExpressionValidationError("AND and OR expression nodes need children.")
        if node.node_type not in OPERATOR_NODES and child_count:
            raise CourseRuleExpressionValidationError("Leaf expression nodes cannot have children.")

    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node_id: UUID) -> None:
        if node_id in visiting:
            raise CourseRuleExpressionValidationError("Expression tree cannot contain cycles.")
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in children_by_parent[node_id]:
            visit(child.id)
        visiting.remove(node_id)
        visited.add(node_id)

    visit(roots[0].id)
    if len(visited) != len(nodes):
        raise CourseRuleExpressionValidationError("Expression tree contains disconnected nodes.")
