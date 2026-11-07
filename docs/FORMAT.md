# Model Catalog JSON Schema (model-catalog/1)

This document describes the schema for model catalog definitions.

## Structure

```json
{
  "schema": "model-catalog/1",
  "version": "YYYY-MM-DD",
  "models": [
    {
      "id": "m-a",
      "provider": "alpha",
      "entries": [
        {
          "valid_from": "YYYY-MM-DD",
          "context_window": 200000,
          "max_output": 8192,
          "input_per_mtok": "3.00",
          "output_per_mtok": "15.00",
          "capabilities": ["tools", "vision"],
          "source": "https://example.com/pricing"
        }
      ]
    }
  ]
}
```

## Constraints

- `schema`: Must be `"model-catalog/1"`.
- `version`: ISO 8601 date string `YYYY-MM-DD`.
- `models`: Array of at most 1,000 models.
- `id`: Unique identifier matching `^[a-z0-9][a-z0-9._:-]{0,99}$`.
- `provider`: Non-empty string.
- `entries`: Array of 1 to 100 entries per model.
- `valid_from`: ISO 8601 date string `YYYY-MM-DD`. Unique within entries for a given model.
- `context_window`, `max_output`: Non-boolean positive integers (> 0).
- `input_per_mtok`, `output_per_mtok`: Decimal price strings matching `^\d+(\.\d{1,6})?$` per million tokens.
- `capabilities`: Array containing items from the fixed vocabulary:
  - `vision`
  - `tools`
  - `json_mode`
  - `streaming`
  - `reasoning`
  - `audio`
  - `batch`
  - `caching`
- `source`: URL or citation string documenting where the entry specifications were sourced.
- Unknown keys anywhere in the catalog raise `CatalogError` with code `invalid_catalog`.
