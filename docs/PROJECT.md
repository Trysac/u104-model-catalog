# Project Record\n\n## Objective\n\nProvide a versioned, validated, and immutable-by-design catalog of LLM specifications to prevent cost and routing errors caused by stale, hard-coded model data.\n\n## Scope\n\n- Parsing and validation of versioned catalog JSON files (schema `model-catalog/1`).\n- In-memory `Catalog` API for retrieving and querying model data.\n- Command-line interface for manual inspection and filtering.\n\n## Out of Scope\n\n- Runtime price fetching from external APIs.\n- Automated cost estimation or routing logic.\n- Any I/O outside of the initial file loading.

## Factory run u104b (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4455 | 12840 | 0 | 0 | 0.0257 |
| fix-1 | gemini-3.1-flash-lite | no | 32429 | 772 | 0 | 14009 | 0.0096 |
| audit | gemini-3.1-flash-lite | no | 81924 | 354 | 0 | 368858 | 0.0302 |
| docs | gemini-3.1-flash-lite | no | 168764 | 1585 | 0 | 0 | 0.0446 |

Total: $0.1102. Prices: Anthropic list prices.
