from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security.guardrails import evaluate_input


DEFAULT_SECURITY_SET_PATH = Path("data/golden_set/security_eval.jsonl")
DEFAULT_REPORT_DIR = Path("evaluation/reports")


def load_security_cases(path: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            cases.append({str(key): str(value) for key, value in payload.items()})
    return cases


def run_security_evaluation(
    security_set_path: Path = DEFAULT_SECURITY_SET_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    cases = load_security_cases(security_set_path)
    results: list[dict[str, object]] = []
    for case in cases:
        decision = evaluate_input(case["query"])
        actual_behavior = "allowed" if decision.allowed else "blocked"
        expected_behavior = case["expected_behavior"]
        expected_guardrail = case["expected_guardrail"]
        passed = actual_behavior == expected_behavior and decision.category == expected_guardrail
        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_behavior": expected_behavior,
                "actual_behavior": actual_behavior,
                "expected_guardrail": expected_guardrail,
                "actual_guardrail": decision.category,
                "passed": passed,
            }
        )

    total = len(results)
    summary = {
        "total_samples": total,
        "pass_rate": sum(1 for result in results if result["passed"]) / total if total else 0.0,
    }
    report_path = write_report(report_dir, summary, results)
    return {"summary": summary, "report_path": str(report_path)}


def write_report(
    report_dir: Path,
    summary: dict[str, Any],
    results: list[dict[str, object]],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"security_eval_{timestamp}.json"
    latest_path = report_dir / "security_eval_latest.json"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "results": results,
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic security guardrails.")
    parser.add_argument("--security-set", type=Path, default=DEFAULT_SECURITY_SET_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_security_evaluation(
        security_set_path=args.security_set,
        report_dir=args.report_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
