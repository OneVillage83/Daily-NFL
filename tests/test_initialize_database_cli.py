import json
import subprocess
import sys
from pathlib import Path


def test_initialize_database_script_runs_directly(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    script = repository_root / "scripts" / "initialize_database.py"
    database = tmp_path / "cli-validation.db"

    result = subprocess.run(
        [sys.executable, str(script), "--database", str(database)],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema_version_before"] == 0
    assert payload["schema_version_after"] == 1
    assert payload["supported_schema_version"] == 1
    assert payload["integrity_ok"] is True
    assert payload["foreign_keys_enabled"] is True
    assert payload["mode"] == "migrate"

    check_result = subprocess.run(
        [sys.executable, str(script), "--database", str(database), "--check"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )

    check_payload = json.loads(check_result.stdout)
    assert check_payload["schema_version_before"] == 1
    assert check_payload["schema_version_after"] == 1
    assert check_payload["mode"] == "check"
