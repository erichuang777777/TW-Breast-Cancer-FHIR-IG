from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=1)
def load_qbc_spec() -> dict:
    path = files("qbc_workbench").joinpath("data/qbc_fields.json")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def field_specs() -> dict[str, dict]:
    return {field["tag"]: field for field in load_qbc_spec()["fields"]}
