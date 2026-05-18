from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass(slots=True)
class CheckResult:
    name: str
    command: list[str]
    ok: bool
    output: str


PY = sys.executable or "python3"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BASE_CHECKS: list[tuple[str, list[str]]] = [
    ("ruff", [PY, "-m", "ruff", "check", "."]),
    ("black", [PY, "-m", "black", "--check", "."]),
    ("mypy", [PY, "-m", "mypy", "bot", "games", "admin_tools", "tests"]),
    ("pytest", [PY, "-m", "pytest", "-q"]),
]

STRICT_OPS_CHECKS: list[tuple[str, list[str]]] = [
    ("reconcile_recent", [PY, "-m", "admin_tools.cli", "reconcile-recent", "--limit", "5"]),
    ("reconcile_verify", [PY, "-m", "admin_tools.cli", "reconcile-verify", "--limit", "5"]),
    ("ws_smoke", [PY, "-m", "admin_tools.cli", "ws-smoke"]),
]


def run_check(name: str, command: list[str]) -> CheckResult:
    proc = subprocess.run(command, capture_output=True, text=True, cwd=PROJECT_ROOT)
    output = (proc.stdout + "\n" + proc.stderr).strip()
    if "No module named" in output:
        output = (
            f"Missing Python dependency while running {name}. "
            f"Try: {PY} -m pip install -e .[dev]\n{output}"
        )
    return CheckResult(name=name, command=command, ok=proc.returncode == 0, output=output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 verification")
    parser.add_argument("--strict", action="store_true", help="Run ops/database strict checks")
    args = parser.parse_args()

    checks = list(BASE_CHECKS)
    if args.strict:
        checks.extend(STRICT_OPS_CHECKS)

    results = [run_check(name, cmd) for name, cmd in checks]

    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}: {' '.join(result.command)}")
        if result.output:
            print(result.output)
            print("-" * 80)

    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
