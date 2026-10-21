#!/usr/bin/env python3
"""Deploy an already reviewed Git ref with a database backup and rollback guard.

This script intentionally refuses to work with a dirty checkout or without an
explicit ref. It builds images before changing the running containers.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def run(*args: str, capture: bool = False) -> str:
    print("+", " ".join(args), flush=True)
    result = subprocess.run(args, check=False, text=True, capture_output=capture)
    if result.returncode:
        if capture and result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    return result.stdout.strip() if capture else ""


def git(*args: str, capture: bool = False) -> str:
    return run("git", *args, capture=capture)


def compose(args: list[str], *, capture: bool = False) -> str:
    return run("docker", "compose", "--env-file", ".env", *COMPOSE_FILES, *args, capture=capture)


COMPOSE_FILES = [
    "-f",
    "deploy/compose.base.yml",
    "-f",
    "deploy/compose.db.yml",
    "-f",
    "deploy/compose.migrate.yml",
    "-f",
    "deploy/compose.api.yml",
    "-f",
    "deploy/compose.worker.yml",
    "-f",
    "deploy/compose.web.yml",
    "-f",
    "deploy/compose.proxy.yml",
    "-f",
    "deploy/compose.prod.yml",
]


def check_ready(url: str, timeout: float = 5) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/v1/health/ready", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def image_id(image: str) -> str | None:
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe production deployment from Git")
    parser.add_argument("--ref", required=True, help="reviewed commit or tag to deploy")
    parser.add_argument("--url", default="http://127.0.0.1", help="public URL for readiness checks")
    parser.add_argument("--backup-dir", default="backups", help="directory for pg_dump files")
    parser.add_argument("--yes", action="store_true", help="confirm the production deployment")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Refusing production deployment without --yes")
    if not Path(".env").is_file():
        raise SystemExit("Missing .env in repository root")
    if shutil.which("docker") is None:
        raise SystemExit("docker is not available")

    status = git("status", "--porcelain", capture=True)
    if status:
        raise SystemExit("Working tree is not clean; commit or stash local changes first")

    git("fetch", "--prune", "origin")
    target = git("rev-parse", "--verify", f"{args.ref}^{{commit}}", capture=True)
    current = git("rev-parse", "HEAD", capture=True)
    if target == current:
        print("Requested ref is already deployed in this checkout.")

    if not check_ready(args.url):
        raise SystemExit("Current production is not ready; refusing to deploy over an unhealthy release")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = backup_dir / f"itmatch-{stamp}.dump"
    rollback_api = f"itmatch/api:rollback-{stamp}"
    rollback_web = f"itmatch/web:rollback-{stamp}"
    old_api = image_id("itmatch/api:local")
    old_web = image_id("itmatch/web:local")

    git("switch", "--detach", target)
    try:
        if old_api:
            run("docker", "tag", old_api, rollback_api)
        if old_web:
            run("docker", "tag", old_web, rollback_web)

        compose(["config", "-q"])
        compose(["build", "api", "web", "worker", "migrate"])

        print(f"Creating database backup: {backup}", flush=True)
        with backup.open("wb") as output:
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "--env-file",
                    ".env",
                    *COMPOSE_FILES,
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
                ],
                check=False,
                stdout=output,
            )
        if result.returncode:
            raise SystemExit("Database backup failed; running release was not changed")
        backup.chmod(0o600)

        compose(["run", "--rm", "migrate"])
        compose(["up", "-d", "--no-build", "api", "worker", "web"])

        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if check_ready(args.url):
                print("Deployment completed and readiness check passed.")
                return 0
            time.sleep(2)

        print("New release did not become ready; restoring previous images.", file=sys.stderr)
        if old_api:
            run("docker", "tag", rollback_api, "itmatch/api:local")
        if old_web:
            run("docker", "tag", rollback_web, "itmatch/web:local")
        compose(["up", "-d", "--no-build", "api", "worker", "web"])
        raise SystemExit("Deployment rolled back. Database migration was not automatically reversed.")
    finally:
        print(f"Deployed checkout: {target}", flush=True)


if __name__ == "__main__":
    main()
