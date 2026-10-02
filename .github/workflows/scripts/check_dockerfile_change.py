#!/usr/bin/env python3
"""Evaluate Git diffs to short-circuit Docker image builds and fast-track release re-tagging."""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def write_github_output(outputs: dict[str, str]) -> None:
    """Write key-value pairs to GITHUB_OUTPUT environment file."""
    # ponytail: 3-line standard environment file export
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as f:
            f.writelines(f"{k}={v}\n" for k, v in outputs.items())


def write_step_summary(params: dict[str, str]) -> None:
    """Append Markdown optimization report to GITHUB_STEP_SUMMARY."""
    if summary_file := os.environ.get("GITHUB_STEP_SUMMARY"):
        rows = [f"| {k} | {v} |" for k, v in params.items()]
        table = (
            "### Container Build Optimization Status\n\n| Parameter | Details |\n|---|---|\n" + "\n".join(rows) + "\n\n"
        )
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(table)


def run_git_command(args: list[str]) -> str:
    """Execute a git command and return stripped stdout, failing on error."""
    try:
        res = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else exc.stdout.strip()
        logger.error("Git command 'git %s' failed (exit code %d): %s", " ".join(args), exc.returncode, stderr)
        raise


def normalize_path(path_str: str) -> str:
    """Normalize file path to repository-relative POSIX format without leading dot-slash."""
    return Path(path_str).as_posix().lstrip("./")


def check_pr_diff(dockerfile: str, target_branch: str) -> bool:
    """Check if dockerfile was modified in the PR compared to the target branch."""
    norm_file = normalize_path(dockerfile)

    # Determine remote/local target ref
    branches_output = run_git_command(["branch", "-a"])
    branches = [b.strip().lstrip("* ") for b in branches_output.splitlines() if b.strip()]

    if target_branch.startswith(("origin/", "ufs-community/")):
        target_ref = target_branch
    elif f"origin/{target_branch}" in branches or f"remotes/origin/{target_branch}" in branches:
        target_ref = f"origin/{target_branch}"
    elif f"ufs-community/{target_branch}" in branches or f"remotes/ufs-community/{target_branch}" in branches:
        target_ref = f"ufs-community/{target_branch}"
    else:
        target_ref = target_branch

    logger.info("Evaluating PR diff for '%s' against target ref '%s'...", norm_file, target_ref)
    diff_output = run_git_command(["diff", "--name-only", f"{target_ref}...HEAD", "--", norm_file])
    changed_files = [normalize_path(line) for line in diff_output.splitlines() if line.strip()]
    is_changed = norm_file in changed_files
    logger.info("Git diff against %s: changed=%s", target_ref, is_changed)
    return is_changed


def check_release_diff(dockerfile: str, release_version: str) -> tuple[bool, str]:
    """Check if dockerfile was modified since the preceding release tag.

    Returns:
        tuple[bool, str]: (is_changed, previous_tag)
    """
    norm_file = normalize_path(dockerfile)
    logger.info("Evaluating release diff for '%s' (release_version=%s)...", norm_file, release_version)

    # Query all tags sorted by creation date descending
    tag_output = run_git_command(["tag", "--sort=-creatordate"])
    all_tags = [t.strip() for t in tag_output.splitlines() if t.strip()]

    if not all_tags:
        logger.info("No preceding release tag found in repository; treating as first release (build required).")
        return True, ""

    v_tag = f"v{release_version.lstrip('v')}" if release_version else ""
    prior_tags = [t for t in all_tags if t != v_tag]

    if not prior_tags:
        logger.info("No prior release tag found before '%s'; treating as first release (build required).", v_tag)
        return True, ""

    prev_tag = prior_tags[0]
    logger.info("Found preceding release tag '%s'. Checking diff...", prev_tag)
    diff_output = run_git_command(["diff", "--name-only", prev_tag, "HEAD", "--", norm_file])
    changed_files = [normalize_path(line) for line in diff_output.splitlines() if line.strip()]
    is_changed = norm_file in changed_files
    logger.info("Git diff against %s: changed=%s", prev_tag, is_changed)
    return is_changed, prev_tag


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Evaluate Dockerfile changes for CI optimization.")
    parser.add_argument("--dockerfile", required=True, help="Path to Dockerfile.")
    parser.add_argument(
        "--event-name",
        required=True,
        choices=["pull_request", "push", "release", "workflow_dispatch"],
        help="GitHub workflow event name or context.",
    )
    parser.add_argument("--target-branch", default="", help="Target base branch for PR evaluation (e.g. develop).")
    parser.add_argument("--is-sandbox", action="store_true", help="Whether this is a sandbox build.")
    parser.add_argument("--sandbox-version", default="", help="Version tag for sandbox build.")
    parser.add_argument("--release-version", default="", help="Published version string for release.")
    parser.add_argument("--is-prerelease", action="store_true", help="Whether release is a prerelease.")
    parser.add_argument("--image-name", default="", help="Target container image name.")
    parser.add_argument("--org", default=os.environ.get("DOCKER_ORG", "noaaepic"), help="Docker organization.")
    parser.add_argument("--force-build", action="store_true", help="Force image build regardless of diff.")

    return parser.parse_args()


def main() -> int:
    """Main execution entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    try:
        norm_dockerfile = normalize_path(args.dockerfile)
        logger.info("Evaluating Dockerfile '%s' under event '%s'", norm_dockerfile, args.event_name)

        dockerfile_changed = True
        prev_tag = ""

        if args.force_build:
            logger.info("Force build requested via flag.")
            dockerfile_changed = True
        elif args.event_name == "pull_request":
            target = args.target_branch or "develop"
            dockerfile_changed = check_pr_diff(norm_dockerfile, target)
        elif args.event_name in ("push", "release"):
            dockerfile_changed, prev_tag = check_release_diff(norm_dockerfile, args.release_version)
        elif args.event_name == "workflow_dispatch":
            if args.target_branch:
                dockerfile_changed = check_pr_diff(norm_dockerfile, args.target_branch)
            else:
                dockerfile_changed = True

        # Determine action and target outputs
        action = "build"
        build_needed = True
        source_image = ""
        target_tags = ""

        if not dockerfile_changed:
            if args.event_name == "pull_request":
                if args.is_sandbox:
                    action = "retag"
                    build_needed = False
                    source_image = f"{args.org}/{args.image_name}-dev:latest"
                    target_tags = f"{args.org}/{args.image_name}-sandbox:{args.sandbox_version}"
                else:
                    action = "skip"
                    build_needed = False
            elif args.event_name in ("push", "release"):
                action = "retag"
                build_needed = False
                # For releases, promote dev:latest or re-tag existing image
                source_image = (
                    f"{args.org}/{args.image_name}:latest"
                    if args.is_prerelease
                    else f"{args.org}/{args.image_name}-dev:latest"
                )
                target_tags = f"{args.org}/{args.image_name}:{args.release_version} {args.org}/{args.image_name}:latest"

        logger.info(
            "Optimization outcome: changed=%s, build_needed=%s, action=%s",
            dockerfile_changed,
            build_needed,
            action,
        )

        # Export outputs to GITHUB_OUTPUT
        outputs = {
            "dockerfile_changed": "true" if dockerfile_changed else "false",
            "build_needed": "true" if build_needed else "false",
            "action": action,
            "source_image": source_image,
            "target_tags": target_tags,
        }
        write_github_output(outputs)

        # Export summary to GITHUB_STEP_SUMMARY
        summary_params = {
            "Dockerfile": f"`{norm_dockerfile}`",
            "Event Context": f"`{args.event_name}`",
            "Dockerfile Changed": "✅ Yes" if dockerfile_changed else "❌ No",
            "Preceding Release Tag": f"`{prev_tag}`" if prev_tag else "*(none)*",
            "Optimization Action": (
                "🔨 **Build image**"
                if action == "build"
                else (
                    f"🏷️ **Re-tag existing manifest** (`{source_image}` ➔ `{target_tags}`)"
                    if action == "retag"
                    else "⚡ **Short-circuited (Build skipped)**"
                )
            ),
        }
        write_step_summary(summary_params)

        return 0
    except subprocess.CalledProcessError as exc:
        stderr_msg = exc.stderr.strip() if exc.stderr else (exc.stdout.strip() if exc.stdout else "")
        print(f"::error::Git command 'git {' '.join(exc.cmd[1:])}' failed (exit {exc.returncode}): {stderr_msg}")
        return exc.returncode


if __name__ == "__main__":
    sys.exit(main())
