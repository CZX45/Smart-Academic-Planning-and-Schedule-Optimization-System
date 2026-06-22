from sqlalchemy.dialects.postgresql import insert

from app.db.base import DevSeedRecord
from app.db.session import SessionLocal

MOCK_SEEDS = [
    {
        "seed_key": "mock-institution",
        "label": "Mock institution placeholder",
        "payload": {"confidence_level": "mock", "advisor_confirmation_required": True},
    }
]


def main() -> None:
    with SessionLocal() as session:
        for seed in MOCK_SEEDS:
            statement = insert(DevSeedRecord).values(**seed)
            statement = statement.on_conflict_do_update(
                index_elements=[DevSeedRecord.seed_key],
                set_={"label": statement.excluded.label, "payload": statement.excluded.payload},
            )
            session.execute(statement)
        session.commit()


if __name__ == "__main__":
    main()
