from __future__ import annotations

import json
from pathlib import Path

from evaluation.agent_eval import load_golden_set, run_evaluation
from evaluation.judges import deterministic_scores
from evaluation.schemas import GoldenSample


class FakeOrchestrator:
    def answer(self, message: str, session_id: str | None = None) -> dict[str, object]:
        return {
            "answer": f"Answer for {message}",
            "tool_calls": ["search_project_docs"],
            "sources": ["README.md"],
            "metadata": {"session_id": session_id},
        }


class FakeRetriever:
    def search(self, query: str, limit: int = 5) -> dict[str, object]:
        return {
            "status": "ok",
            "results": [
                {
                    "text": "The platform predicts industrial machine failure risk.",
                    "source": "README.md",
                    "score": 0.95,
                }
            ],
        }


def test_load_golden_set_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "case-1",
                "query": "What is this?",
                "expected_answer": "A predictive maintenance platform.",
                "expected_tools": ["search_project_docs"],
                "expected_contexts": ["README.md"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    samples = load_golden_set(path)

    assert samples[0].id == "case-1"
    assert samples[0].expected_tools == ["search_project_docs"]


def test_deterministic_scores_measure_tool_and_context_recall() -> None:
    sample = GoldenSample(
        id="case-1",
        query="What is this?",
        expected_answer="A predictive maintenance platform.",
        expected_tools=["search_project_docs", "get_active_model"],
        expected_contexts=["README.md"],
    )

    scores = deterministic_scores(
        sample=sample,
        answer="It predicts machine failure.",
        tool_calls=["search_project_docs"],
        sources=["README.md"],
    )

    assert scores["answer_present"] == 1.0
    assert scores["tool_recall"] == 0.5
    assert scores["context_recall"] == 1.0


def test_run_evaluation_writes_reports(monkeypatch, tmp_path: Path) -> None:
    golden_set = tmp_path / "golden.jsonl"
    golden_set.write_text(
        json.dumps(
            {
                "id": "case-1",
                "query": "What is this?",
                "expected_answer": "A predictive maintenance platform.",
                "expected_tools": ["search_project_docs"],
                "expected_contexts": ["README.md"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("evaluation.agent_eval.AgentOrchestrator", lambda: FakeOrchestrator())
    monkeypatch.setattr("evaluation.agent_eval.get_rag_retriever", lambda: FakeRetriever())

    result = run_evaluation(
        golden_set_path=golden_set,
        report_dir=tmp_path / "reports",
        use_judge=False,
        use_ragas=False,
        log_mlflow=False,
    )

    latest_report = tmp_path / "reports" / "agent_eval_latest.json"
    latest_markdown = tmp_path / "reports" / "agent_eval_latest.md"
    assert Path(result["report_path"]).exists()
    assert latest_report.exists()
    assert latest_markdown.exists()
    assert result["summary"]["pass_rate"] == 1.0
