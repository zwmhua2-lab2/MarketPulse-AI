"""Export the backend FastAPI OpenAPI document for frontend type generation.

The document is produced by importing the application object, so generation needs no
running server, no database and no environment file — every ``Settings`` field carries a
default. The output is deterministic (sorted keys, UTF-8, LF, trailing newline), which is
what lets ``check:api-drift`` compare a fresh regeneration byte for byte.

Usage:
    py -3.14 frontend/scripts/export-openapi.py <output_path>

The output path is required so this can never drop a stray document into the working
tree; the npm scripts always write into a scratch directory.
"""

from __future__ import annotations

import json
import pathlib
import sys

FRONTEND_DIR = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_DIR.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marketpulse.api.app import app  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    output = pathlib.Path(argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    document = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(document + "\n")
    print(f"openapi document written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
