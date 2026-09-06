#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_REPO = "stack-template"
LANGS = ("python", "go", "rust")
DEST_BASE = Path(os.environ.get("SCAFFOLD_DEST", str(Path.home() / "Documents")))
NAME_PATTERN = r"[a-z0-9-]+"
PLACEHOLDER = "stackapp"


def main():
    args = parse_args()
    dest = DEST_BASE / args.name
    if dest.exists():
        sys.exit(f"{dest} already exists")
    config = load_config()
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / TEMPLATE_REPO
        clone_template(config["GH_OWNER"], clone)
        copy_template(clone, args.lang, dest)
    rename_placeholder(dest, args.lang, args.name)
    init_repo(dest, args.name)
    if args.dry_run:
        print(f"dry run: created {dest} from templates/{args.lang}, skipped repo creation")
        return
    publish(dest, args.name, config)
    print(f"created {config['GH_OWNER']}/{args.name} from templates/{args.lang}")


def parse_args():
    parser = argparse.ArgumentParser(description="Scaffold a new service from stack-template")
    parser.add_argument("name")
    parser.add_argument("lang", choices=LANGS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(NAME_PATTERN, args.name):
        sys.exit("name must be lowercase letters, digits, dashes")
    return args


def load_config():
    config = {}
    for line in (ROOT / ".taskconfig").read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip():
            config[key.strip()] = value.strip()
    return config


def clone_template(owner, clone):
    run("gh", "repo", "clone", f"{owner}/{TEMPLATE_REPO}", str(clone), "--", "--depth", "1")


def copy_template(clone, lang, dest):
    shutil.copytree(clone / "templates" / lang, dest)


def rename_placeholder(dest, lang, name):
    replacement = name if lang == "go" else name.replace("-", "_")
    for path in dest.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            if PLACEHOLDER.encode() in data:
                path.write_bytes(data.replace(PLACEHOLDER.encode(), replacement.encode()))
    for path in sorted(dest.rglob(f"*{PLACEHOLDER}*"), reverse=True):
        path.rename(path.with_name(path.name.replace(PLACEHOLDER, replacement)))


def init_repo(dest, name):
    run("git", "init", "-b", "main", cwd=dest)
    run("git", "add", ".", cwd=dest)
    run("git", "add", "-f", "AGENTS.md", cwd=dest)
    run("git", "commit", "-m", f"Initial {name} service", cwd=dest)


def publish(dest, name, config):
    repo = f"{config['GH_OWNER']}/{name}"
    run("gh", "repo", "create", repo, "--private", "--source", ".", "--push", cwd=dest)
    token = subprocess.run(
        [str(ROOT / "scripts" / "deploy-token.sh")], check=True, capture_output=True, text=True
    ).stdout.strip()
    run("gh", "secret", "set", "DEPLOY_TOKEN", "-R", repo, "--body", token)
    run("gh", "secret", "set", "DEPLOY_URL", "-R", repo, "--body", f"{config['HOOKS_BASE']}/deploy-{name}")


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


if __name__ == "__main__":
    main()
