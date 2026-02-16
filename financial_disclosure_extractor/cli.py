"""
CLI entry point for the financial disclosure extractor.

Usage:
    python -m financial_disclosure_extractor <input_file> [-o output.json]
    cat tanshin.txt | python -m financial_disclosure_extractor -
"""

from __future__ import annotations

import argparse
import sys

from .extractor import extract


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="決算開示抽出専用エンジン — Extract structured data from Japanese earnings disclosures.",
    )
    parser.add_argument(
        "input",
        help="Path to the disclosure text file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to write JSON output (default: stdout).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2).",
    )

    args = parser.parse_args(argv)

    # Read input
    if args.input == "-":
        text = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()

    # Extract
    disclosure = extract(text)
    json_str = disclosure.to_json(indent=args.indent)

    # Write output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
            f.write("\n")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
