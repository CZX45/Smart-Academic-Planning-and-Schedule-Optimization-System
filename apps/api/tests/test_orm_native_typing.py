"""Prove that native ORM annotations retain a useful negative type gate."""

import subprocess
import sys
from pathlib import Path


def test_native_orm_typing_rejects_invalid_column_values(tmp_path: Path) -> None:
    probe = tmp_path / "invalid_orm_assignment.py"
    probe.write_text(
        "from app.models.academic import Course, StudentProfile\n"
        "def invalid(course: Course, student: StudentProfile) -> None:\n"
        "    course.title = 42\n"
        "    student.home_institution_id = 'not-a-uuid'\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            "pyproject.toml",
            "--cache-dir",
            str(tmp_path / "type-cache"),
            str(probe),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout.count("[assignment]") == 2, result.stdout + result.stderr
