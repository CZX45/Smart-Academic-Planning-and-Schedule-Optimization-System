from __future__ import annotations

from collections.abc import Callable
from itertools import chain

from sqlalchemy import CheckConstraint, MetaData
from sqlalchemy.schema import SchemaItem, Table

type IncludeObject = Callable[[SchemaItem, str | None, str, bool, SchemaItem | None], bool]


def build_alembic_include_object(metadata: MetaData) -> IncludeObject:
    def include_object(
        object_: SchemaItem,
        name: str | None,
        type_: str,
        reflected: bool,
        compare_to: SchemaItem | None,
    ) -> bool:
        if (
            type_ != "check_constraint"
            or not reflected
            or compare_to is not None
            or name is None
            or not isinstance(object_, CheckConstraint)
            or not isinstance(object_.table, Table)
        ):
            return True

        metadata_table = metadata.tables.get(object_.table.key)
        if metadata_table is None:
            return True

        constraints = chain(
            metadata_table.constraints,
            *(column.constraints for column in metadata_table.columns),
        )
        for constraint in constraints:
            if (
                isinstance(constraint, CheckConstraint)
                and constraint.name == name
                and constraint._type_bound
            ):
                return False

        return True

    return include_object
