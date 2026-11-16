# Groq internal generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Groq Free text synthesizer to the existing internal RAG without changing embeddings, permissions, data or public chat.

**Architecture:** Keep retrieval and business tools authoritative. Dispatch only the final prose-generation call to an exact HTTPS Groq endpoint; failures return the existing deterministic answer, never another provider. Preserve legacy Gemini unless explicitly selected away.

**Tech Stack:** Django, Python urllib, existing provider_http, unittest.

**Spec:** Approved in chat: internal first, Groq gpt-oss-120b, separate embedding config, citations/workspace/RBAC retained, safe fallback, no secrets/PII export; owner supplied key on16/11.

## Global Constraints

- Existing worktree98d8300; do not stage main workspace's unrelated changes.
- No schema/data/reindex/97-ledger changes. No paid provider switch or account upgrade.
- LLM_GENERATION_PROVIDER=groq is explicit opt-in; GROQ_API_KEY never reused for embeddings.
- Existing Gemini behavior retained by default; no Groq/Gemini cross-provider fallback.
- One Groq request per synthesis,12s timeout,8000-character prompt bound,65536-byte response bound, max_completion_tokens1024, reasoning_effort low, include_reasoning false.
- Only complete nonempty textual stop responses from requested model are accepted. Tool calls/refusals/truncation/malformed data fail closed; do not expose reasoning.
- Block recognizable sensitive content before sending. This is defense in depth, not proof arbitrary prose is PII-free; do not test live against business DB.

## Review Focus

1. Enabling Groq must not change embedding vectors/threshold or trigger Gemini with the wrong key.
2. Bad provider data,409/429, timeout, oversized responses and truncated output must fall back truthfully without credential leakage.
3. No-context and simulations must not make external calls.
4. Inputs containing recognizable email/phone/credentials must not reach the transport; no claim of universal PII detection.
5. Existing RAG sources/RBAC/public separation must remain; source citations are not proof live prose is factually perfect.

### Task 1: Chat-only Groq adapter and regression integration

**Files:** Create apps/knowledge/groq_generation.py and tests/test_groq_generation.py; modify apps/knowledge/services.py, config/settings.py, config/settings_evidence_test.py, .env.example, .github/workflows/quality.yml and status/context/changelog/test inventory docs.

**Interfaces:** Adapter generate_groq_answer(prompt: str, api_key: str, model: str) -> tuple[str | None, str | None], returning answer and safe failure reason. services dispatch reuses existing generation metadata and deterministic body. Existing function signatures stay compatible.

- [x] Write tests on real generation pipeline and outbound payload/response boundary (only transport mocked); verify expected RED.
- [x] Implement explicit opt-in adapter, privacy/size guard, safe errors and truthful metadata; run focused tests GREEN.
- [x] Add regression that Groq key/config leaves offline embedding vectors and retrieval threshold unchanged on isolated TEST DB.
- [x] Run existing generation/embedding/provider/RAG/security regressions, update test manifest, then full suite on randomized TEST DB; retain all failures/logs.
- [x] Fresh read-only whole-change review and fix important issues with RED/GREEN regressions.
- [x] Commit scoped change only after fresh green checks; do not push/deploy as a side effect of local integration.

### Task 2: Bounded live proof and local handoff

**Files:** Evidence under output/groq_generation_20261116; local .env gets only nonsecret selector if checks pass.

**Interfaces:** Production code from Task1 with user-provided GROQ_API_KEY; no DB reads/business data in prompts.

- [x] At most3 synthetic grounded queries, no PII; record actual mode/model/latency/answers and failure reasons, never credentials.
- [x] Enable local selector only if live probe succeeds; do not equate probe with production deployment or model-quality benchmark.
- [x] Apply only feature patch to primary dirty workspace without overwriting unrelated edits; verify focused tests there.
- [x] Report code/test/live outcomes and exact remaining Render config/rollout work honestly.
