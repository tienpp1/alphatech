# Release Checklist: Production Upgrade Baseline

**Purpose**: Requirements-quality and production-evidence review for the eight upgrade steps.
**Created**: 2026-09-06
**Feature**: [../spec.md](../spec.md)

**Review Ownership**: This checklist is reviewer-owned. `[x]` means the requirement quality or evidence criterion has been reviewed and satisfied; it does not by itself mean implementation is complete.

## Requirement completeness

- [ ] CHK001 Are User–Customer ownership, guest behavior, contact persistence, and delivery snapshots specified? [Completeness, Spec FR-001/FR-002]
- [ ] CHK002 Are lease, heartbeat, retry, timeout, cancel, and restart recovery requirements specified? [Completeness, Spec FR-004]
- [ ] CHK003 Are product, category, branch dimensions and backtesting/drift requirements specified? [Completeness, Spec FR-005/FR-006]
- [ ] CHK004 Are recommendation action parameters, validation, rollback and approval separation specified? [Gap, Spec FR-008]
- [ ] CHK005 Are CI, staging, observability, backup/restore and production acceptance evidence requirements specified? [Completeness, Spec FR-010/FR-011]

## Requirement clarity and consistency

- [ ] CHK006 Is “owner” defined as authenticated identity rather than submitted email/name/phone? [Clarity, Spec FR-001/FR-003]
- [ ] CHK007 Is the boundary between local automated proof and external production evidence explicit? [Consistency, Spec FR-011]
- [ ] CHK008 Are terminal approval states and idempotency replay semantics unambiguous? [Clarity, Spec FR-007/FR-008]
- [ ] CHK009 Are missing actuals and heuristic drift signals distinguished from measured model quality? [Clarity, Spec FR-006]

## Scenario and recovery coverage

- [ ] CHK010 Are cross-workspace, guest, duplicate, expired-lease, cancelled-job and stale-worker scenarios covered? [Coverage, Edge Cases]
- [ ] CHK011 Are SMTP/OAuth/staging/inbox/restore failures explicitly treated as blocked or failed rather than successful? [Coverage, Spec FR-011]
- [ ] CHK012 Are stale enterprise benchmark fixtures and the two phase-10 demonstrations separately classified? [Consistency, Spec FR-009]

## Acceptance criteria quality

- [ ] CHK013 Can each local success criterion be reproduced with a named test command? [Measurability, Spec SC-001/SC-004]
- [ ] CHK014 Does every external gate require dated evidence without storing secrets or private email content? [Measurability, Spec SC-005]
- [ ] CHK015 Are out-of-scope items (new roles, schema redesign, OAuth provider change, database reset) documented? [Completeness, Assumptions]

## Notes

- Unchecked items require reviewer confirmation before a production release.
- The checklist intentionally remains unchecked until human review and external evidence exist.
