from pathlib import Path
import sysconfig

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata


ROOT = Path(SPEC).resolve().parents[1]

datas = [(str(ROOT / "app"), "app")]
binaries = []
hiddenimports = []

for package in (
    "fastapi",
    "pydantic",
    "pydantic_core",
    "pydantic_settings",
    "sqlalchemy",
    "psycopg",
    "psycopg_binary",
    "starlette",
    "uvicorn",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hiddenimports)
    datas.extend(copy_metadata(package, recursive=True))

pydantic_core_init = next(
    (
        Path(source)
        for source, target in datas
        if target == "pydantic_core" and Path(source).name == "__init__.py"
    ),
    None,
)
if pydantic_core_init is not None:
    pydantic_core_dir = pydantic_core_init.parent
else:
    pydantic_core_dir = Path(sysconfig.get_paths()["purelib"]) / "pydantic_core"
for pydantic_core_binary in pydantic_core_dir.glob("_pydantic_core*.pyd"):
    binaries.append((str(pydantic_core_binary), "pydantic_core"))
hiddenimports.append("pydantic_core._pydantic_core")

for package in ("app", "psycopg", "uvicorn", "fastapi", "starlette"):
    hiddenimports.extend(collect_submodules(package))

psycopg_binary_init = next(
    (
        Path(source)
        for source, target in datas
        if target == "psycopg_binary" and Path(source).name == "__init__.py"
    ),
    None,
)
if psycopg_binary_init is not None:
    psycopg_binary_libs = psycopg_binary_init.parent.parent / "psycopg_binary.libs"
else:
    psycopg_binary_libs = Path(sysconfig.get_paths()["purelib"]) / "psycopg_binary.libs"
if psycopg_binary_libs.is_dir():
    datas.extend(
        (str(path), "psycopg_binary.libs")
        for path in psycopg_binary_libs.iterdir()
        if path.is_file()
    )


def is_excluded_resource(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return normalized.endswith(".pyc") or any(
        f"/{segment}/" in normalized or normalized.endswith(f"/{segment}")
        for segment in ("tests", "testing", "fixtures", "__pycache__")
    )


datas = [
    entry
    for entry in datas
    if not any(is_excluded_resource(str(value)) for value in entry[:2])
]

a = Analysis(
    [str(ROOT / "app" / "run.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    noarchive=False,
)
def normalized_destination(entry: tuple[str, ...]) -> str:
    return str(entry[0]).replace("\\", "/").lower()


a.binaries = [
    entry
    for entry in a.binaries
    if "psycopg_binary.libs" not in normalized_destination(entry)
]
a.datas = [
    entry
    for entry in a.datas
    if not any(is_excluded_resource(str(value)) for value in entry[:2])
]
binary_destinations = {normalized_destination(entry) for entry in a.binaries}
a.datas = [
    entry for entry in a.datas if normalized_destination(entry) not in binary_destinations
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    name="sapsos-api",
    contents_directory=".",
    exclude_binaries=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="sapsos-api",
)
