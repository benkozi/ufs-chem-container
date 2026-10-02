#!/usr/bin/env python3
"""Evaluate pull request sandbox configuration and parse sandbox version tag."""

import argparse
import logging
import os
import re
import sys

logger = logging.getLogger(__name__)


def evaluate_sandbox(is_labeled: bool, body: str) -> tuple[bool, str]:
    """Evaluate whether sandbox build is requested and validate sandbox version.

    Returns:
        tuple[bool, str]: (is_sandbox, sandbox_version)

    Raises:
        ValueError: If sandbox-version is missing, empty, or format is invalid.
    """
    if not is_labeled:
        logger.info("PR is not labeled with sandbox-build. Standard verification build will proceed.")
        return False, ""

    logger.info("PR is labeled with sandbox-build. Parsing sandbox-version from PR description...")

    # Match sandbox-version=<version> on its own line (with optional markdown delimiters)
    pattern = r"^\s*(?:__|\*\*)?sandbox-version(?:__|\*\*)?\s*=\s*([a-zA-Z0-9_.-]+?)(?:__|\*\*)?\s*$"
    match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
    if not match:
        raise ValueError(
            'PR is labeled "sandbox-build" but lacks "sandbox-version=" on its own line.\n'
            'Add "sandbox-version=<version>" (e.g., 7.7.7-rc.1) on its own line.'
        )

    version = match.group(1).strip()
    # ponytail: regex group enforces non-empty; proceed directly to Docker tag validation
    if not re.match(r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$", version):
        raise ValueError(f'Extracted sandbox version "{version}" is not a valid Docker image tag.')

    logger.info("Valid sandbox configuration detected: version=%s", version)
    return True, version


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Evaluate sandbox configuration for pull requests.")
    parser.add_argument("--is-labeled", default=os.environ.get("IS_LABELED_SANDBOX", "false"))
    parser.add_argument("--body", default=os.environ.get("PR_BODY", ""))
    return parser.parse_args()


def main() -> int:
    """Main execution entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    is_labeled = str(args.is_labeled).strip().lower() in ("true", "1", "yes")

    try:
        is_sandbox, version = evaluate_sandbox(is_labeled, args.body or "")
    except ValueError as exc:
        for line in str(exc).splitlines():
            print(f"::error::{line}")
        return 1

    # ponytail: direct environment file write
    out = os.environ["GITHUB_OUTPUT"]
    with open(out, "a", encoding="utf-8") as f:
        f.write(f"is_sandbox={'true' if is_sandbox else 'false'}\nsandbox_version={version}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
