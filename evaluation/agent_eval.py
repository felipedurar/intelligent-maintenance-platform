from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow

from agent.orchestrator import AgentOrchestrator
from evaluation.judges import OpenAIJudge, deterministic_scores
from evaluation.ragas_eval import evaluate_with_ragas
from evaluation.schemas import AgentEvalResult, GoldenSample, RetrievedContext
from rag.retriever import get_rag_retriever


DEFAULT_GOLDEN_SET_PATH = Path("data/golden_set/agent_eval.jsonl")
DEFAULT_REPORT_DIR = Path("evaluation/reports")


def load_golden_set(path: Path) -> list[GoldenSample]:
    samples: list[GoldenSample] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            samples.append(
                GoldenSample(
                    id=str(payload.get("id") or f"sample-{line_number}"),
                    query=str(payload["query"]),
                    expected_answer=str(payload["expected_answer"]),
                    expected_tools=[str(tool) for tool in payload.get("expected_tools", [])],
                    expected_contexts=[
                        str(context) for context in payload.get("expected_contexts", [])
                    ],
                )
            )
    return samples


def collect_contexts(query: str, limit: int = 5) -> list[RetrievedContext]:
    rag_result = get_rag_retriever().search(query, limit=limit)
    contexts: list[RetrievedContext] = []
    for item in rag_result.get("results", []):
        if not isinstance(item, dict):
            continue
        contexts.append(
            RetrievedContext(
                text=str(item.get("text", "")),
                source=str(item.get("source", "")),
                score=float(item["score"]) if item.get("score") is not None else None,
            )
        )
    return contexts


def run_agent_sample(
    sample: GoldenSample,
    orchestrator: AgentOrchestrator,
    use_judge: bool,
    context_limit: int,
) -> AgentEvalResult:
    response = orchestrator.answer(sample.query, session_id=f"eval-{sample.id}")
    answer = str(response.get("answer", ""))
    tool_calls = [str(tool) for tool in response.get("tool_calls", [])]
    sources = [str(source) for source in response.get("sources", [])]
    metadata = response.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    contexts = collect_contexts(sample.query, limit=context_limit)
    if not sources:
        sources = [context.source for context in contexts]

    result = AgentEvalResult(
        sample=sample,
        answer=answer,
        tool_calls=tool_calls,
        sources=sources,
        contexts=contexts,
        metadata=metadata,
        deterministic_scores=deterministic_scores(sample, answer, tool_calls, sources),
    )
    if use_judge:
        try:
            judge_scores = OpenAIJudge().evaluate(result)
        except Exception as exc:
            judge_scores = {"status": "failed", "reason": str(exc)}
        result = AgentEvalResult(
            sample=result.sample,
            answer=result.answer,
            tool_calls=result.tool_calls,
            sources=result.sources,
            contexts=result.contexts,
            metadata=result.metadata,
            deterministic_scores=result.deterministic_scores,
            judge_scores=judge_scores,
        )
    return result


def aggregate_results(results: list[AgentEvalResult], ragas: dict[str, Any]) -> dict[str, Any]:
    total = len(results)
    deterministic_keys = sorted(
        {key for result in results for key in result.deterministic_scores.keys()}
    )
    deterministic_means = {
        key: sum(result.deterministic_scores.get(key, 0.0) for result in results) / total
        if total
        else 0.0
        for key in deterministic_keys
    }

    judge_numeric_keys = sorted(
        {
            key
            for result in results
            for key, value in (result.judge_scores or {}).items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
    )
    judge_means = {
        key: sum(float((result.judge_scores or {}).get(key, 0.0)) for result in results) / total
        if total
        else 0.0
        for key in judge_numeric_keys
    }

    return {
        "total_samples": total,
        "pass_rate": sum(1 for result in results if result.passed) / total if total else 0.0,
        "deterministic": deterministic_means,
        "judge": judge_means,
        "ragas": ragas,
    }


def result_to_dict(result: AgentEvalResult) -> dict[str, Any]:
    return {
        "id": result.sample.id,
        "query": result.sample.query,
        "expected_answer": result.sample.expected_answer,
        "answer": result.answer,
        "expected_tools": result.sample.expected_tools,
        "tool_calls": result.tool_calls,
        "expected_contexts": result.sample.expected_contexts,
        "sources": result.sources,
        "contexts": [
            {"source": context.source, "score": context.score, "text": context.text}
            for context in result.contexts
        ],
        "metadata": result.metadata,
        "deterministic_scores": result.deterministic_scores,
        "judge_scores": result.judge_scores,
        "passed": result.passed,
    }


def write_reports(report_dir: Path, summary: dict[str, Any], results: list[AgentEvalResult]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"agent_eval_{timestamp}.json"
    latest_path = report_dir / "agent_eval_latest.json"
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "results": [result_to_dict(result) for result in results],
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    markdown_path = report_dir / "agent_eval_latest.md"
    markdown_path.write_text(render_markdown_report(payload), encoding="utf-8")
    return report_path


def render_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Agent Evaluation Report",
        "",
        f"Generated at: `{payload['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Total samples: `{summary['total_samples']}`",
        f"- Pass rate: `{summary['pass_rate']:.2%}`",
    ]
    for section in ("deterministic", "judge"):
        metrics = summary.get(section, {})
        if metrics:
            lines.extend(["", f"## {section.title()} Metrics", ""])
            lines.extend(f"- `{key}`: `{value:.4f}`" for key, value in metrics.items())

    ragas = summary.get("ragas", {})
    lines.extend(["", "## RAGAS", "", f"- Status: `{ragas.get('status', 'unknown')}`"])
    for key, value in ragas.get("metrics", {}).items():
        lines.append(f"- `{key}`: `{value:.4f}`")
    if ragas.get("reason"):
        lines.append(f"- Reason: {ragas['reason']}")

    lines.extend(["", "## Samples", ""])
    for result in payload["results"]:
        lines.extend(
            [
                f"### {result['id']}",
                "",
                f"- Passed: `{result['passed']}`",
                f"- Query: {result['query']}",
                f"- Tools: `{', '.join(result['tool_calls']) or 'none'}`",
                f"- Sources: `{', '.join(result['sources']) or 'none'}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def log_to_mlflow(summary: dict[str, Any], report_path: Path) -> None:
    mlflow.set_experiment("ai4i-agent-evaluation")
    with mlflow.start_run(run_name="agent-golden-set-eval"):
        mlflow.log_metric("pass_rate", float(summary["pass_rate"]))
        for prefix in ("deterministic", "judge"):
            for key, value in summary.get(prefix, {}).items():
                mlflow.log_metric(f"{prefix}_{key}", float(value))
        for key, value in summary.get("ragas", {}).get("metrics", {}).items():
            mlflow.log_metric(f"ragas_{key}", float(value))
        mlflow.log_artifact(str(report_path))


def run_evaluation(
    golden_set_path: Path = DEFAULT_GOLDEN_SET_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
    use_judge: bool = False,
    use_ragas: bool = False,
    require_ragas: bool = False,
    log_mlflow: bool = False,
    context_limit: int = 5,
) -> dict[str, Any]:
    samples = load_golden_set(golden_set_path)
    orchestrator = AgentOrchestrator()
    results = [
        run_agent_sample(
            sample=sample,
            orchestrator=orchestrator,
            use_judge=use_judge,
            context_limit=context_limit,
        )
        for sample in samples
    ]
    ragas = evaluate_with_ragas(results) if use_ragas else {"status": "skipped"}
    if require_ragas and ragas.get("status") != "ok":
        reason = ragas.get("reason") or "RAGAS did not return status=ok."
        raise RuntimeError(f"Required RAGAS evaluation failed: {reason}")
    summary = aggregate_results(results, ragas)
    report_path = write_reports(report_dir, summary, results)
    if log_mlflow:
        try:
            log_to_mlflow(summary, report_path)
        except Exception as exc:
            summary["mlflow_warning"] = str(exc)
    return {"summary": summary, "report_path": str(report_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the predictive-maintenance agent.")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--judge", action="store_true", help="Enable OpenAI LLM-as-judge.")
    parser.add_argument("--ragas", action="store_true", help="Enable optional RAGAS evaluation.")
    parser.add_argument(
        "--require-ragas",
        action="store_true",
        help="Fail if RAGAS metrics are skipped or fail.",
    )
    parser.add_argument("--mlflow", action="store_true", help="Log summary metrics and report to MLflow.")
    parser.add_argument("--context-limit", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_evaluation(
        golden_set_path=args.golden_set,
        report_dir=args.report_dir,
        use_judge=args.judge,
        use_ragas=args.ragas,
        require_ragas=args.require_ragas,
        log_mlflow=args.mlflow,
        context_limit=args.context_limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
