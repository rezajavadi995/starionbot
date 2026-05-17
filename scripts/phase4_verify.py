from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass


@dataclass(slots=True)
class CheckResult:
    name: str
    command: list[str]
    ok: bool
    output: str


BASE_CHECKS: list[tuple[str, list[str]]] = [
    ("ruff", ["ruff", "check", "."]),
    ("black", ["black", "--check", "."]),
    ("mypy", ["mypy", "bot", "games", "admin_tools", "tests"]),
    ("pytest", ["pytest", "-q"]),
]

STRICT_OPS_CHECKS: list[tuple[str, list[str]]] = [
    ("reconcile_recent", ["python", "-m", "admin_tools.cli", "reconcile-recent", "--limit", "5"]),
    ("reconcile_verify", ["python", "-m", "admin_tools.cli", "reconcile-verify", "--limit", "5"]),
    ("ws_smoke", ["python", "-m", "admin_tools.cli", "ws-smoke"]),
]


def run_check(name: str, command: list[str]) -> CheckResult:
    proc = subprocess.run(command, capture_output=True, text=True)
    output = (proc.stdout + "\n" + proc.stderr).strip()
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
