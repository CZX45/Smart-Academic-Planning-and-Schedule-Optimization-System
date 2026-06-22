import json
from pathlib import Path

from app.main import app

OUT = Path(__file__).resolve().parents[2] / "openapi.json"
OUT.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {OUT}")
