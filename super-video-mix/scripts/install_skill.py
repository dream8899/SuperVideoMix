#!/usr/bin/env python3
"""Install or validate SuperVideoMix without platform-specific shell dependencies."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_NAME = "super-video-mix"
SKILL_DIR = Path(__file__).resolve().parents[1]


def default_target(agent: str) -> Path | None:
    home = Path.home()
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME", home / ".codex")) / "skills"
    if agent == "claude-code":
        return Path(os.environ.get("CLAUDE_CODE_HOME", home / ".claude")) / "skills"
    return None


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def check() -> int:
    missing = []
    python_ok = sys.version_info >= (3, 10)
    for command in ("ffmpeg", "ffprobe"):
        if not command_exists(command):
            missing.append(command)
    if not (SKILL_DIR / "SKILL.md").is_file():
        missing.append("SKILL.md")
    print(f"Python: {sys.version.split()[0]} ({'ok' if python_ok else 'need 3.10+'})")
    print(f"Skill: {SKILL_DIR}")
    print(f"FFmpeg/ffprobe: {'ok' if not missing else 'missing ' + ', '.join(missing)}")
    return 0 if python_ok and not missing else 1


def install(target_root: Path, force: bool) -> int:
    destination = target_root / SKILL_NAME
    if destination.exists():
        if not force:
            print(f"Refusing to overwrite existing skill: {destination}. Use --force after backup/review.", file=sys.stderr)
            return 2
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        SKILL_DIR,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    print(f"Installed {SKILL_NAME} to {destination}")
    return 0


def link(target_root: Path, force: bool) -> int:
    destination = target_root / SKILL_NAME
    if destination.exists() or destination.is_symlink():
        if not force:
            print(f"Refusing to overwrite existing skill: {destination}. Use --force after backup/review.", file=sys.stderr)
            return 2
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    target_root.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(SKILL_DIR, target_is_directory=True)
    print(f"Linked {SKILL_NAME} to {destination} -> {SKILL_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or validate SuperVideoMix.")
    parser.add_argument("--agent", choices=("codex", "claude-code", "generic"), default="generic")
    parser.add_argument("--target-dir", type=Path, help="Directory containing skills; required for --agent generic.")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation after review.")
    parser.add_argument("--link", action="store_true", help="Create a symbolic link to this source instead of copying it.")
    parser.add_argument("--check", action="store_true", help="Validate dependencies and source files only.")
    arguments = parser.parse_args()
    if arguments.check:
        return check()
    target = arguments.target_dir or default_target(arguments.agent)
    if target is None:
        parser.error("--target-dir is required for --agent generic")
    target = target.expanduser().resolve()
    return link(target, arguments.force) if arguments.link else install(target, arguments.force)


if __name__ == "__main__":
    raise SystemExit(main())
