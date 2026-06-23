from app.services.degree_audit.grade_policy import GradePolicy


def test_grade_policy_compares_letter_grades_by_configured_order() -> None:
    policy = GradePolicy()

    assert policy.satisfies_minimum("A-", "B").is_satisfied is True
    assert policy.satisfies_minimum("C", "C").is_satisfied is True
    assert policy.satisfies_minimum("D+", "C").is_satisfied is False


def test_grade_policy_does_not_treat_pass_fail_as_letter_grade() -> None:
    policy = GradePolicy()

    pass_result = policy.satisfies_minimum("P", "C")
    satisfactory_result = policy.satisfies_minimum("S", None)
    unsatisfactory_result = policy.satisfies_minimum("U", None)

    assert pass_result.is_satisfied is False
    assert pass_result.warning_code == "PASS_FAIL_MINIMUM_GRADE_REVIEW"
    assert satisfactory_result.is_satisfied is True
    assert unsatisfactory_result.is_satisfied is False


def test_grade_policy_warns_for_unknown_and_incomplete_grades() -> None:
    policy = GradePolicy()

    unknown_result = policy.satisfies_minimum("ZZ", "C")
    incomplete_result = policy.satisfies_minimum("I", "C")

    assert unknown_result.is_satisfied is False
    assert unknown_result.warning_code == "UNKNOWN_GRADE"
    assert incomplete_result.is_satisfied is False
    assert incomplete_result.warning_code == "INCOMPLETE_GRADE"
