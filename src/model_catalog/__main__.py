"""CLI entry point for model_catalog."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from model_catalog import CatalogError, load_catalog


def _parse_date_arg(val: str) -> date:
    try:
        return date.fromisoformat(val)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{val}': must be YYYY-MM-DD") from exc


def _parse_decimal_arg(val: str) -> Decimal:
    try:
        return Decimal(val)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"Invalid decimal '{val}'") from exc


def main(argv: list[str] | None = None) -> int:
    """Execute model_catalog CLI commands."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="model-catalog", description="LLM model catalog lookup and query CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    get_parser = subparsers.add_parser("get", help="Get a single model by ID")
    get_parser.add_argument("file", help="Path to catalog JSON file")
    get_parser.add_argument("id", help="Model ID to look up")
    get_parser.add_argument(
        "--at", type=_parse_date_arg, default=None, help="Point in time (YYYY-MM-DD)"
    )

    query_parser = subparsers.add_parser("query", help="Query models with filtering")
    query_parser.add_argument("file", help="Path to catalog JSON file")
    query_parser.add_argument("--provider", default=None, help="Filter by provider")
    query_parser.add_argument(
        "--min-context", type=int, default=None, help="Filter by minimum context window"
    )
    query_parser.add_argument(
        "--capability",
        dest="capabilities",
        action="append",
        default=[],
        help="Filter by capability (repeatable)",
    )
    query_parser.add_argument(
        "--max-input-price",
        type=_parse_decimal_arg,
        default=None,
        help="Filter by maximum input price per Mtok",
    )
    query_parser.add_argument(
        "--at", type=_parse_date_arg, default=None, help="Point in time (YYYY-MM-DD)"
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code != 0 else 0

    if not args.command:
        parser.print_help(sys.stderr)
        return 2

    try:
        catalog = load_catalog(args.file)
    except CatalogError as err:
        if err.code in ("invalid_catalog", "too_large"):
            sys.stderr.write(f"Error: {err}\n")
            return 2
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"I/O error: {exc}\n")
        return 2

    if args.command == "get":
        try:
            m = catalog.get(args.id, at=args.at)
        except CatalogError as err:
            sys.stderr.write(f"Error: {err}\n")
            return 1
        sys.stdout.write(
            f"{m.id}\t{m.provider}\t{m.context_window}\t{m.input_per_mtok}\t{m.output_per_mtok}\n"
        )
        return 0

    if args.command == "query":
        try:
            models = catalog.query(
                provider=args.provider,
                min_context=args.min_context,
                capabilities=args.capabilities,
                max_input_price=args.max_input_price,
                at=args.at,
            )
        except CatalogError as err:
            sys.stderr.write(f"Error: {err}\n")
            return 1

        for m in models:
            sys.stdout.write(
                f"{m.id}\t{m.provider}\t{m.context_window}\t{m.input_per_mtok}\t{m.output_per_mtok}\n"
            )
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
