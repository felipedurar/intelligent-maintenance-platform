from __future__ import annotations

from typing import Any

from evaluation.schemas import AgentEvalResult


def evaluate_with_ragas(results: list[AgentEvalResult]) -> dict[str, Any]:
    """Run RAGAS when optional evaluation dependencies are installed.

    The project keeps RAGAS optional so Docker, CI, and local development can still run
    deterministic checks without downloading the heavier evaluation stack.
    """
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
    except Exception as exc:
        return {
            "status": "skipped",
            "reason": f"RAGAS dependencies are not installed or not importable: {exc}",
        }

    rag_rows = [
        {
            "question": result.sample.query,
            "answer": result.answer,
            "contexts": [context.text for context in result.contexts],
            "ground_truth": result.sample.expected_answer,
            "reference": result.sample.expected_answer,
        }
        for result in results
        if result.contexts and result.answer.strip()
    ]
    if not rag_rows:
        return {"status": "skipped", "reason": "No answered samples with retrieved contexts."}

    try:
        dataset = Dataset.from_list(rag_rows)
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        score_dict = dict(scores)
        return {
            "status": "ok",
            "metrics": {key: float(value) for key, value in score_dict.items() if value is not None},
        }
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}
