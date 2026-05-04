# OWASP Mapping

This document maps relevant OWASP Top 10 for LLM Applications risks to the Datathon AI
Platform. It focuses on implemented controls, available evidence, and residual production risk.

## Summary

| OWASP risk | Relevance | Current status |
|---|---|---|
| Prompt Injection | High | Guardrails and tests implemented |
| Sensitive Information Disclosure | High | Output sanitization and secret blocking implemented |
| Insecure Output Handling | Medium | Sanitization and domain constraints implemented |
| Excessive Agency | High | Tool scope and decision-support wording implemented |
| Insecure Plugin/Tool Use | Medium | Strict tool schemas and limited tool set implemented |
| Data and Vector Store Poisoning | Medium | Controlled RAG source set implemented |
| Supply Chain and Model Integrity | High | MLflow registry and approval gate implemented |
| Model Denial of Service | Medium | Basic input scope and length controls, production hardening pending |

## Detailed Mapping

| Risk | How it appears in this project | Potential impact | Implemented mitigation | Evidence |
|---|---|---|---|---|
| Prompt Injection | User asks the assistant to ignore instructions, reveal hidden prompts, or bypass safety controls. | Secret leakage, unsafe tool calls, unreliable answers. | Regex-based prompt-injection detection blocks override and exfiltration patterns before the LLM is called. | `src/security/guardrails.py`, `data/golden_set/security_eval.jsonl`, `evaluation/reports/security_eval_latest.json` |
| Sensitive Information Disclosure | User asks for OpenAI keys, database passwords, internal prompts, or config values. | Credential compromise, internal-control exposure. | Input blocking for secret extraction attempts and output redaction for API keys, JWT-like tokens, database URLs, and password/token fields. | `src/security/guardrails.py`, security eval cases `sec-001`, `sec-002` |
| Insecure Output Handling | LLM output may claim the platform automatically stops machines or expose unsafe operational instructions. | Over-trust, unsafe maintenance action, misleading automation claims. | Output sanitizer rewrites unsafe automation claims and system prompt leakage. System prompt frames the model as decision support only. | `src/security/guardrails.py`, `src/agent/orchestrator.py`, `docs_governance/SYSTEM_CARD.md` |
| Excessive Agency | Agent can call prediction and metadata tools, which may be mistaken for operational authority. | Users may treat model output as a maintenance command. | Tool set is limited to documentation search, model metadata, and prediction. The assistant does not trigger maintenance actions. | `src/agent/orchestrator.py`, `docs_governance/SYSTEM_CARD.md` |
| Insecure Plugin/Tool Use | LLM tool calls could pass invalid or malicious parameters. | Invalid predictions, unexpected tool execution. | OpenAI tool schemas define required fields and enums. FastAPI prediction schemas validate request payloads. | `src/agent/orchestrator.py`, `src/platform_api/routes/predictions.py`, `tests/test_platform_api.py` |
| Data and Vector Store Poisoning | Malicious or low-quality documents could be indexed into RAG. | Grounded answers may cite poisoned context. | RAG indexing is controlled by project-owned documentation paths, not arbitrary user upload. Indexing is run by worker scripts, not public chat requests. | `src/rag/indexer.py`, `scripts/run_rag_indexing.sh`, `docs/architecture.md` |
| Supply Chain and Model Integrity | A model version could be promoted without review or lineage. | Wrong model in production, weak auditability. | MLflow tracks runs and artifacts. Training registers `candidate`; `promote_model.py` requires benchmark/fairness reports, approver, reason, and pending status before assigning `champion`. | `src/training/train_model.py`, `src/training/promote_model.py`, `tests/test_model_promotion.py` |
| Model Denial of Service | Large or unrelated prompts could consume model/tool resources. | Cost increase, latency, degraded service. | Topic restriction blocks unrelated requests. Guardrails constrain prompt scope. Production should add API rate limiting and authentication. | `src/security/guardrails.py`, `evaluation/reports/security_eval_latest.json` |

## Security Evaluation Evidence

Latest deterministic security evaluation:

- File: `evaluation/reports/security_eval_latest.json`
- Generated at: 2026-05-03
- Samples: 5
- Pass rate: 1.0

Covered scenarios:

- prompt injection;
- system prompt extraction;
- secret extraction;
- off-topic malicious request;
- off-topic harmless request;
- allowed predictive-maintenance request.

## Residual Risks

- Regex guardrails are useful for a Datathon prototype but are not a complete LLM firewall.
- Production should add authenticated access, rate limits, centralized audit logs, WAF/API
  gateway policies, and environment-specific secret management.
- RAG poisoning controls depend on keeping indexing restricted to trusted repositories and
  approved document sources.
- OpenAI managed serving reduces infrastructure burden but introduces external provider
  dependency and requires vendor/security review for production.

## Required Production Hardening

Before real production use:

1. enforce API authentication and RBAC;
2. add rate limiting per API key/user;
3. add centralized security logs and alerting;
4. require reviewed pull requests for RAG source changes;
5. enforce cloud secret manager usage;
6. add dependency scanning and container vulnerability scanning;
7. run recurring red-team evaluation after prompt, tool, or RAG changes.
