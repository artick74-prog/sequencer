#!/usr/bin/env python3
"""Local bridge for Hardware MIDI Host.

Serves the repository on localhost and gives midi-host.html two same-origin API
endpoints:
  POST /api/sync   -> write project files, commit, push
  POST /api/reload -> git pull --ff-only, return projects/current.json

The server binds to 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
ALLOWED_FILES = {"current.json", "overview.json", "overview.md", "selection.json"}
MAX_BODY = 32 * 1024 * 1024


class GitError(RuntimeError):
    pass


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git command failed").strip()
        raise GitError(detail)
    return proc


def current_branch() -> str:
    name = run_git("branch", "--show-current").stdout.strip()
    return name or "main"


def short_sha() -> str:
    return run_git("rev-parse", "--short", "HEAD").stdout.strip()


def ensure_remote_is_safe_to_push(branch: str) -> None:
    run_git("fetch", "origin", branch)
    local = run_git("rev-parse", "HEAD").stdout.strip()
    remote = run_git("rev-parse", f"origin/{branch}").stdout.strip()
    if local == remote:
        return

    local_is_ancestor = run_git(
        "merge-base", "--is-ancestor", local, remote, check=False
    ).returncode == 0
    if local_is_ancestor:
        raise GitError(
            "GitHub has newer changes. Click Reload from AI first, then load/edit your MIDI again."
        )

    remote_is_ancestor = run_git(
        "merge-base", "--is-ancestor", remote, local, check=False
    ).returncode == 0
    if remote_is_ancestor:
        return

    raise GitError(
        "Local and GitHub histories have diverged. Resolve Git first, then retry Sync to AI."
    )


def has_tracked_worktree_changes() -> bool:
    proc = run_git("status", "--porcelain", "--untracked-files=no")
    return bool(proc.stdout.strip())


def commit_staged(message: str) -> bool:
    staged = run_git("diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return False
    if staged.returncode != 1:
        raise GitError((staged.stderr or staged.stdout or "git diff failed").strip())

    name = run_git("config", "user.name", check=False).stdout.strip()
    email = run_git("config", "user.email", check=False).stdout.strip()
    args = []
    if not name:
        args += ["-c", "user.name=MIDI Host"]
    if not email:
        args += ["-c", "user.email=midi-host@localhost"]
    run_git(*args, "commit", "-m", message)
    return True


class Handler(SimpleHTTPRequestHandler):
    server_version = "SequencerLocalBridge/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length")
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ValueError("Request too large")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            try:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "root": str(ROOT),
                        "branch": current_branch(),
                        "commit": short_sha(),
                    },
                )
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/sync":
            self._handle_sync()
            return
        if path == "/api/reload":
            self._handle_reload()
            return
        self._send_json(404, {"ok": False, "error": "Unknown API endpoint"})

    def _handle_sync(self) -> None:
        try:
            payload = self._read_json()
            files = payload.get("files")
            if not isinstance(files, dict) or not files:
                raise ValueError("files must be a non-empty object")

            unknown = set(files) - ALLOWED_FILES
            if unknown:
                raise ValueError("Unsupported file(s): " + ", ".join(sorted(unknown)))

            for name, text in files.items():
                if not isinstance(text, str):
                    raise ValueError(f"{name} must be text")

            branch = current_branch()
            ensure_remote_is_safe_to_push(branch)

            PROJECTS.mkdir(parents=True, exist_ok=True)
            written = []
            for name, text in files.items():
                target = PROJECTS / name
                temp = target.with_name(target.name + ".tmp")
                temp.write_text(text, encoding="utf-8", newline="\n")
                os.replace(temp, target)
                written.append(f"projects/{name}")

            run_git("add", "--", *written)
            project_name = str(payload.get("projectName") or "project")
            project_name = " ".join(project_name.replace("\r", " ").replace("\n", " ").split())[:80]
            changed = commit_staged(f"Sync from MIDI Host: {project_name}")

            # Push even when this sync produced no new commit, so an existing local
            # ahead commit cannot remain invisible to the assistant.
            run_git("push", "origin", branch)

            self._send_json(
                200,
                {
                    "ok": True,
                    "changed": changed,
                    "commit": short_sha(),
                    "branch": branch,
                    "files": written,
                },
            )
        except (ValueError, GitError, OSError, json.JSONDecodeError) as exc:
            self._send_json(409, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})

    def _handle_reload(self) -> None:
        try:
            if has_tracked_worktree_changes():
                raise GitError(
                    "There are uncommitted tracked files. Sync to AI first or commit/revert them before Reload."
                )
            branch = current_branch()
            run_git("pull", "--ff-only", "origin", branch)

            current = PROJECTS / "current.json"
            if not current.exists():
                raise FileNotFoundError("projects/current.json does not exist")
            project = json.loads(current.read_text(encoding="utf-8"))
            if not isinstance(project, dict) or not isinstance(project.get("tracks"), list):
                raise ValueError("projects/current.json is invalid or missing tracks[]")

            self._send_json(
                200,
                {
                    "ok": True,
                    "commit": short_sha(),
                    "branch": branch,
                    "project": project,
                },
            )
        except (ValueError, GitError, OSError, json.JSONDecodeError) as exc:
            self._send_json(409, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Sequencer with local Git sync bridge")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--open", action="store_true", help="Open midi-host.html in the default browser")
    args = parser.parse_args()

    os.chdir(ROOT)
    address = ("127.0.0.1", args.port)
    server = ThreadingHTTPServer(address, Handler)
    url = f"http://localhost:{args.port}/midi-host.html"

    print(f"Sequencer local bridge: {url}")
    print("Sync to AI = save + git commit + push")
    print("Reload from AI = git pull + reload current.json")
    print("Press Ctrl+C to stop.")

    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
