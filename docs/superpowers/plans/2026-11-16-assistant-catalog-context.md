# Grounded assistant catalog-context repair

**Goal:** Correct the reported highest-price laptop query and related natural
Vietnamese catalog questions using actual workspace product data, not model
memory or synthetic business records.

**Scope:** Reuse the existing deterministic router, catalog tool, conversation
models and Groq synthesis. No new database model, provider, permissions or97
ledger changes. No arbitrary SQL, automatic mutation, public/internal data
mixing, paid training or claim of universal language understanding.

## Work and checks

- [ ] Root: add failing real-router/service tests for polite prefixes, catalog
  price extrema/topN/name/budget, correct sales-vs-price/technician-vs-product
  separation, greeting and bounded follow-up context.
- [ ] Tool implementer: add failing ORM tests and extend only canonical
  get_product_catalog_summary. Price mode accepts sort_by=unit_price,
  ASC/DESC, limit1..20, optional name/SKU search and exact Decimal price bounds
  with inclusive flags. Preserve legacy keys; exclude inactive/deleted/foreign
  related categories; disclose truncation, ties and catalog-price provenance.
- [ ] Root: repair generic `biet` skill match, forward only allowed catalog
  parameters, render exact price facts in deterministic fallback, and rebuild
  bounded prior-user routing context (exclude current message and other users).
  Unsupported stock/specification or price-vs-sales mixtures clarify instead
  of silently dropping constraints. Greetings/help need no provider/retrieval.
- [ ] Verify existing context/security/provider tests, complete Django and JS
  suites on isolated TEST databases, independent final review and secret scan.
- [ ] Preserve dirty primary-workspace changes; integrate only this patch.
  Publish/release when verified, then perform bounded read-only browser checks
  of the reported flow if credentials/provider budget permit. Keep simulated,
  deterministic and live-provider evidence distinct.

**Interfaces:** existing catalog tool adds ranked_products (exact string
unit_price and formatted value), total_matching/displayed_count/limit/truncated,
sort_order/tie_count and price_basis. No descriptions/cost/PII sent as new context.
Root owns intent_router.py, services.py and assistant tests; implementer owns
tools.py and test_catalog_price_context.py. Reviewer reads only.

**Review focus:** untrusted follow-up text cannot supply authority or bypass
permissions; full explicit new questions override history; a category is not a
selected product; budget parsing must retain strict vs inclusive bounds; price
extrema must inspect the full filtered queryset, not the first5 catalog sample.
