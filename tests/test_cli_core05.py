import json
import subprocess
import sys
from pathlib import Path

from sipl.cli import (
    EXIT_INPUT_ERROR,
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_SYNTAX_ERROR,
    main,
)

ROOT = Path(__file__).resolve().parent.parent
POSITIVE_DIR = ROOT / "examples" / "positive"
NEGATIVE_DIR = ROOT / "examples" / "negative"


def test_cli_check_and_parse_json(capsys: object) -> None:
    gcd = str(POSITIVE_DIR / "01_gcd.sipl")
    assert main(["check", gcd, "--json"]) == EXIT_OK
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    data = json.loads(out)
    assert data == {"ok": True, "command": "check", "file": gcd, "valid": True}

    assert main(["parse", gcd, "--json"]) == EXIT_OK
    out_parse = capsys.readouterr().out  # type: ignore[attr-defined]
    parsed = json.loads(out_parse)
    assert parsed["ok"] is True
    assert parsed["command"] == "parse"
    assert parsed["ast"]["type"] == "Program"


def test_cli_run_with_set_and_state_file(tmp_path: Path, capsys: object) -> None:
    gcd = str(POSITIVE_DIR / "01_gcd.sipl")
    state_file = tmp_path / "state.json"
    state_file.write_text('{"M": 100, "N": 16}', encoding="utf-8")

    # --set M=8 перевизначає M=100 з файлу
    code = main(["run", gcd, "--state-file", str(state_file), "--set", "M=8", "--json"])
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert data["ok"] is True
    assert data["command"] == "run"
    assert data["final_state"] == {"M": 8, "N": 8}
    assert data["steps"] > 0


def test_cli_trace_json(capsys: object) -> None:
    power = str(POSITIVE_DIR / "02_power.sipl")
    code = main(["trace", power, "--set", "X=5", "--set", "Y=2", "--json"])
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert data["ok"] is True
    assert data["command"] == "trace"
    assert data["final_state"]["R"] == 25
    assert isinstance(data["trace"], list)
    assert data["trace"][-1]["event"] == "ExecutionFinished"


def test_cli_error_exit_codes_and_json(tmp_path: Path, capsys: object) -> None:
    bad_syntax = str(NEGATIVE_DIR / "02_missing_end.sipl")
    assert main(["check", bad_syntax, "--json"]) == EXIT_SYNTAX_ERROR
    err_syn = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert err_syn["ok"] is False
    assert err_syn["error"]["type"] == "SiplSyntaxError"
    assert err_syn["error"]["span"] is not None

    gcd = str(POSITIVE_DIR / "01_gcd.sipl")
    assert main(["trace", gcd, "--json"]) == EXIT_RUNTIME_ERROR
    err_rt = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert err_rt["ok"] is False
    assert err_rt["error"]["type"] == "UndefinedVariableError"
    assert "trace" in err_rt

    loop_file = tmp_path / "loop.sipl"
    loop_file.write_text("begin while 1 = 1 do skip end", encoding="utf-8")
    assert main(["run", str(loop_file), "--max-steps", "5", "--json"]) == EXIT_RUNTIME_ERROR
    err_loop = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert err_loop["error"]["type"] == "StepLimitExceededError"

    assert main(["run", str(tmp_path / "missing.sipl"), "--json"]) == EXIT_INPUT_ERROR
    err_inp = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert err_inp["ok"] is False
    assert err_inp["error"]["type"] == "CliInputError"


def test_cli_subprocess_integration() -> None:
    gcd = str(POSITIVE_DIR / "01_gcd.sipl")
    proc = subprocess.run(
        [sys.executable, "-m", "sipl.cli", "run", gcd, "--set", "M=24", "--set", "N=18", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == EXIT_OK
    payload = json.loads(proc.stdout)
    assert payload["final_state"] == {"M": 6, "N": 6}