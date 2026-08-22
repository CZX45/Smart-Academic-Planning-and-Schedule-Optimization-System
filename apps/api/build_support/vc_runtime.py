from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterable
from pathlib import Path

VC_REDIST_PATTERN = (
    "Microsoft Visual Studio/*/*/VC/Redist/MSVC/*/x64/Microsoft.VC*.CRT/MSVCP140.dll"
)


def _toolset_version(runtime: Path) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", runtime.parents[2].name))


def resolve_msvcp140(
    *,
    system_root: Path,
    python_base: Path,
    program_files_roots: Iterable[Path],
) -> Path:
    direct_candidates = (
        system_root / "System32" / "MSVCP140.dll",
        python_base / "MSVCP140.dll",
    )
    for candidate in direct_candidates:
        if candidate.is_file():
            return candidate.resolve()

    visual_studio_roots = tuple(program_files_roots)
    visual_studio_candidates = sorted(
        (
            candidate
            for root in visual_studio_roots
            for candidate in root.glob(VC_REDIST_PATTERN)
            if candidate.is_file()
        ),
        key=_toolset_version,
        reverse=True,
    )
    if visual_studio_candidates:
        return visual_studio_candidates[0].resolve()

    searched = [str(candidate) for candidate in direct_candidates]
    searched.extend(str(root / VC_REDIST_PATTERN) for root in visual_studio_roots)
    raise FileNotFoundError(
        "Could not locate the 64-bit Microsoft VC runtime MSVCP140.dll. "
        f"Searched: {', '.join(searched)}"
    )


def resolve_default_msvcp140() -> Path:
    system_root = os.environ.get("SystemRoot")
    if not system_root:
        raise FileNotFoundError("SystemRoot is unavailable; cannot locate MSVCP140.dll.")

    program_files_roots = tuple(
        Path(value)
        for name in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)")
        if (value := os.environ.get(name))
    )
    return resolve_msvcp140(
        system_root=Path(system_root),
        python_base=Path(sys.base_prefix),
        program_files_roots=program_files_roots,
    )


if __name__ == "__main__":
    print(resolve_default_msvcp140())
