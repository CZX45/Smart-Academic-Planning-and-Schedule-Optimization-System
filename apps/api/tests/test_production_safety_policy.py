from app.main import app

PROHIBITED_ENDPOINT_TERMS = [
    "auto-register",
    "auto_register",
    "register-course",
    "register_course",
    "drop-course",
    "drop_course",
    "swap-course",
    "swap_course",
    "join-waitlist",
    "join_waitlist",
    "reserve-seat",
    "reserve_seat",
    "seat-grab",
    "seat_grab",
    "poll-portal",
    "poll_portal",
]


def test_openapi_paths_do_not_expose_prohibited_registration_or_polling_actions() -> None:
    for path, path_item in app.openapi()["paths"].items():
        normalized_path = path.lower()
        assert all(term not in normalized_path for term in PROHIBITED_ENDPOINT_TERMS)
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "patch", "put", "delete"}:
                continue
            operation_id = str(operation.get("operationId", "")).lower()
            summary = str(operation.get("summary", "")).lower()
            assert all(term not in operation_id for term in PROHIBITED_ENDPOINT_TERMS)
            assert all(term not in summary for term in PROHIBITED_ENDPOINT_TERMS)
