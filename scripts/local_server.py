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
import hashlib
import json
import os
import subprocess
import tarfile
import threading
import webbrowser
import zipfile
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
ALLOWED_FILES = {"current.json", "overview.json", "overview.md"}
MAX_BODY = 32 * 1024 * 1024
LIBRARY_ROOT = Path(
    os.environ.get("MIDI_REFERENCE_ROOT", str(ROOT.parent / "midi-reference"))
).resolve()
LIBRARY_LOCK = threading.Lock()
LIBRARY_ENTRIES: list[dict] = []
LIBRARY_LOCATORS: dict[str, tuple[str, str, str | None]] = {}


def infer_library_tags(source: str, member: str) -> tuple[str, str]:
    text = f"{source} {member}".lower().replace("_", " ").replace("-", " ")

    if "tech house" in text or "techhouse" in text:
        genre = "tech-house"
    elif "minimal" in text or "deep tech" in text:
        genre = "minimal-deep-tech"
    elif "acid" in text or "303" in text:
        genre = "acid"
    elif "house" in text:
        genre = "house"
    elif "groove" in text:
        genre = "groove"
    elif "nrg" in text or "edm" in text or "trance" in text:
        genre = "edm"
    else:
        genre = "other"

    if any(word in text for word in ("bassline", "bass line", " bass ", "/bass", "\\bass", "sub bass")):
        kind = "bass"
    elif any(word in text for word in ("drum", "kick", "snare", "clap", "hihat", "hi hat", "hat ", "perc")):
        kind = "drums"
    elif "acid" in text or "303" in text:
        kind = "acid"
    elif "chord" in text:
        kind = "chords"
    elif any(word in text for word in ("melody", "lead", "synth", "arp")):
        kind = "melody"
    else:
        kind = "midi"
    return genre, kind


def library_source_name(path: Path) -> str:
    name = path.name
    low = name.lower()
    for suffix in (".tar.gz", ".tgz", ".zip", ".tar"):
        if low.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def build_library_catalog(force: bool = False) -> dict:
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS
    with LIBRARY_LOCK:
        if LIBRARY_ENTRIES and not force:
            entries = LIBRARY_ENTRIES
        else:
            entries: list[dict] = []
            locators: dict[str, tuple[str, str, str | None]] = {}
            if LIBRARY_ROOT.exists():
                files = sorted(p for p in LIBRARY_ROOT.rglob("*") if p.is_file())
                archive_paths = []
                loose_paths = []
                for path in files:
                    low = path.name.lower()
                    if low.endswith((".mid", ".midi")):
                        loose_paths.append(path)
                    elif low.endswith((".zip", ".tar.gz", ".tgz", ".tar")):
                        archive_paths.append(path)

                for path in loose_paths:
                    rel = path.relative_to(LIBRARY_ROOT).as_posix()
                    source = path.parent.name or "loose"
                    genre, kind = infer_library_tags(source, rel)
                    key = f"file|{rel}"
                    item_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
                    entries.append(
                        {
                            "id": item_id,
                            "name": path.name,
                            "source": source,
                            "genre": genre,
                            "kind": kind,
                            "container": rel,
                            "member": None,
                            "size": path.stat().st_size,
                        }
                    )
                    locators[item_id] = ("file", str(path), None)

                for archive in archive_paths:
                    rel = archive.relative_to(LIBRARY_ROOT).as_posix()
                    source = library_source_name(archive)
                    low = archive.name.lower()
                    try:
                        if low.endswith(".zip"):
                            with zipfile.ZipFile(archive) as zf:
                                members = [
                                    (info.filename, info.file_size)
                                    for info in zf.infolist()
                                    if not info.is_dir()
                                    and info.filename.lower().endswith((".mid", ".midi"))
                                ]
                        else:
                            with tarfile.open(archive, "r:*") as tf:
                                members = [
                                    (member.name, member.size)
                                    for member in tf.getmembers()
                                    if member.isfile()
                                    and member.name.lower().endswith((".mid", ".midi"))
                                ]
                    except (OSError, zipfile.BadZipFile, tarfile.TarError):
                        continue

                    for member, size in members:
                        genre, kind = infer_library_tags(source, member)
                        key = f"archive|{rel}|{member}"
                        item_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
                        entries.append(
                            {
                                "id": item_id,
                                "name": Path(member).name,
                                "source": source,
                                "genre": genre,
                                "kind": kind,
                                "container": rel,
                                "member": member,
                                "size": size,
                            }
                        )
                        locators[item_id] = ("archive", str(archive), member)

            entries.sort(key=lambda item: (item["genre"], item["kind"], item["source"], item["name"].lower()))
            LIBRARY_ENTRIES = entries
            LIBRARY_LOCATORS = locators

        counts = {
            "total": len(entries),
            "genre": dict(Counter(item["genre"] for item in entries)),
            "kind": dict(Counter(item["kind"] for item in entries)),
            "source": dict(Counter(item["source"] for item in entries)),
        }
        return {
            "root": str(LIBRARY_ROOT),
            "entries": entries,
            "counts": counts,
        }


def read_library_midi(item_id: str) -> tuple[bytes, dict]:
    build_library_catalog()
    locator = LIBRARY_LOCATORS.get(item_id)
    entry = next((item for item in LIBRARY_ENTRIES if item["id"] == item_id), None)
    if locator is None or entry is None:
        raise FileNotFoundError("Library MIDI id not found")

    mode, path_text, member = locator
    path = Path(path_text)
    if mode == "file":
        return path.read_bytes(), entry
    if path.name.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            return zf.read(member), entry
    with tarfile.open(path, "r:*") as tf:
        fh = tf.extractfile(member)
        if fh is None:
            raise FileNotFoundError("MIDI member not found in archive")
        return fh.read(), entry



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

    def _send_bytes(self, status: int, data: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            safe = filename.replace('"', "_")
            self.send_header("Content-Disposition", f'inline; filename="{safe}"')
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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/library":
            try:
                self._send_json(200, build_library_catalog())
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/midi":
            try:
                item_id = (parse_qs(parsed.query).get("id") or [""])[0]
                data, entry = read_library_midi(item_id)
                self._send_bytes(200, data, "audio/midi", entry["name"])
            except FileNotFoundError as exc:
                self._send_json(404, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
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
        if path == "/api/library/rescan":
            try:
                self._send_json(200, build_library_catalog(force=True))
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
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
    print(f"Style Library root = {LIBRARY_ROOT}")
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
