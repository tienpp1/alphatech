# Internal assistant context repair — 16 November 2026

## Report and verified cause

The reported question was `cho tôi biết chiếc laptop có giá cao nhất`.
The existing router treated `biết` as both a competency trigger and evidence
of a person, incorrectly calling `get_technician_skills_summary`. Removing the
polite prefix alone still left no catalog-price ranking route. The catalog tool
returned five name-ordered samples; those cannot prove a maximum or minimum.

Conversation history also passed only role/content/tools while its resolver
expected intent/parameters, and included the current question itself. Groq is
downstream answer generation; it cannot repair missing or wrongly selected
business evidence. This change does not fine-tune Groq or alter model weights.

## Implemented behavior

- Reuse `get_product_catalog_summary` and existing `CATALOG_LIST` intent for
  catalog prices. Price extrema/topN inspect the entire eligible queryset
  before slicing, not the five sample rows. Maximum20 results per request.
- Support Vietnamese/accentless price high/low, price ordering, literal product
  name/SKU, a single brand/name filter, and VND budgets expressed in ordinary
  thousands/millions or grouped integer VND. Intersect supported bounds; retain
  strict `dưới/trên` versus inclusive `tối đa/tối thiểu/từ…đến` semantics.
- Keep catalog unit_price separate from sales quantity, completed-order revenue,
  cost, stock availability and profit. Unsupported mixed/specification/stock/
  exclusion/multi-brand constraints clarify instead of silently being dropped.
- Retain full Decimal price precision and deterministic tie order. Disclose
  equal-price alternatives, displayed/matching counts and truncation.
- Require existing retail.view_product before querying. New price mode includes
  active, nondeleted products in the selected workspace, with same-workspace
  category relation; no cost, supplier notes or descriptions in new payloads.
  Shared permission policy and legacy summary contract remain unchanged.
- A polite `cho tôi biết` does not establish technician/person context. Actual
  technician-skill, sales, stock, service and policy routes keep their contracts.
- Reconstruct intent/parameters from at most3 previous user messages in the
  already-owned workspace/session, excluding the current question and assistant
  prose. Only bounded ellipses inherit compatible tools; complete new questions
  override history. Brand/category/budget switches use the canonical parser.
  Price rankings do not silently become a selected product or historical price.
- Greetings, thanks and a short capabilities response use deterministic
  Vietnamese text with no business retrieval or provider call. Permission denial
  is reported as permission denial, not as absence of documents.
- Groq receives grounded tool facts and applied filters. Prompt distinguishes
  current catalog prices from revenue/stock and forbids inferring rankings from
  samples. Existing provider/privacy limits and deterministic fallback remain.

No schema/migration, transaction seed, price mutation, new permission, public
copilot change, embedding/retrieval re-index or97-ledger adjustment is included.

## Verification and limitations

Evidence directory on the operator machine:
`D:/ai_business_platform/output/assistant_context_20261116/`.

- Original router/service RED:11 test methods,17 failed assertions/subtests and
  2 missing-context errors; logs retained. Tool RED:18 tests with45 expected
  assertion/subtest failures and no errors; these are not passing results.
- ORM tool GREEN18/18,0.388s; independent existing regression163/163,13.313s.
- Integrated focused final261/261 OK19.377s, no skip, own TEST DB destroyed.
  Includes all reported review fixes with explicit RED→GREEN logs. Simulated
  Groq tests prove context delivery/metadata, not live-provider answer quality.
- Aggregate JavaScript76/76 passed, no skips,1962.0885ms;5 standalone
  collaboration transport groups passed. Existing tests were not deleted/skipped.
- Independent review required fixes for condition retention and follow-up scope;
  final targeted review approved the repaired branches.
- Full1648/1648 tests OK858.055s, no skips, own randomized TEST database
  destroyed, exit0. All6 modified app/test source hashes match before/after the
  run (`full_receipt.json`). Primary dirty workspace focused34/34 OK13.470s;
  this is not a full-suite pass for that entire unrelated working tree.
- Bandit on4 modified modules:0 findings/errors. Known-pattern release scan:
  894 source files,0 findings, not exhaustive secret detection. CI/live remain
  separate gates pending their receipts.
- An initial full run was interrupted to include the final explicit-sort fix;
  retained as `full_interrupted.log`, not PASS. A fresh full run records its own
  randomized TEST name and before/after source hashes in `full_receipt.json`.
  No broad test-database cleanup or business-database reset was performed.

This is bounded application-language support, not proof of universal language
understanding. Raw fractional-VND input can clarify; unmodeled configurations,
live market prices, a blind holdout, unseen languages and universal LLM accuracy
are not certified. No current production or live-Groq success is claimed here.
