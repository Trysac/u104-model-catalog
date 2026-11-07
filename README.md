# model-catalog

[![PyPI version](https://img.shields.io/pypi/v/trysac-model-catalog)](https://pypi.org/project/trysac-model-catalog/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-model-catalog)](LICENSE)
[![CI](https://github.com/Trysac/u104-model-catalog/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u104-model-catalog/actions/workflows/ci.yml)

Versioned, validated catalog of LLM models with context window, Decimal prices and capabilities, point-in-time lookups and filter queries over caller-supplied data

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-model-catalog
# or
uv add trysac-model-catalog
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import model_catalog

# normalize() trims surrounding whitespace and lower-cases the text.
print(model_catalog.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    model_catalog.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
