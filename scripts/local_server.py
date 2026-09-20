#!/usr/bin/env python3
"""Local bridge for Hardware MIDI Host.

Serves the repository on localhost and gives the local UI same-origin API endpoints:
  POST /api/sync   -> write project files, commit, push
  POST /api/reload -> git pull --ff-only, return projects/current.json
  POST /api/update -> one-click git pull of main + local bridge restart

The server binds to 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import webbrowser
import zipfile
from datetime import datetime, timezone
from collections import Counter, defaultdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from midi_classifier import classify_midi, parse_midi

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
ALLOWED_FILES = {"current.json", "overview.json", "overview.md", "chiptune-current.json", "chiptune-overview.md", "chiptune-loop-ratings.json", "chiptune-loop-aliases.json", "chiptune-loop-selection.json"}
MAX_BODY = 32 * 1024 * 1024
LIBRARY_ROOT = Path(
    os.environ.get("MIDI_REFERENCE_ROOT", str(ROOT.parent / "midi-reference"))
).resolve()
LIBRARY_LOCK = threading.Lock()
LIBRARY_PROGRESS_LOCK = threading.Lock()
LIBRARY_PROGRESS: dict = {
    "active": False,
    "stage": "idle",
    "current": 0,
    "total": 0,
    "percent": 0,
    "catalogTotal": 0,
    "message": "MIDI library is idle",
}
LIBRARY_ENTRIES: list[dict] = []
LIBRARY_LOCATORS: dict[str, tuple[str, str, str | None]] = {}
LIBRARY_MODE: str | None = None
CLASSIFICATION_CACHE_VERSION = 3
CLASSIFICATION_CACHE_PATH = LIBRARY_ROOT / ".style-library-classification-v3.json"
PACK_ROOT = LIBRARY_ROOT / "packs"
PACK_BUILD_ROOT = LIBRARY_ROOT / "packs.__building__"
PACK_OLD_ROOT = LIBRARY_ROOT / "packs.__old__"
PACK_INDEX_PATH = PACK_ROOT / "library-index.json"
PACK_MAX_FILES = max(100, int(os.environ.get("STYLE_PACK_MAX_FILES", "1000")))
MIDI_CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", str(LIBRARY_ROOT.parent))) / "SequencerStyleLibrary" / "midi-v1"
try:
    GM_PROGRAM_NAMES = json.loads((ROOT / "scripts" / "gm-instruments.json").read_text(encoding="utf-8")).get("programs", [])
except (OSError, ValueError, json.JSONDecodeError):
    GM_PROGRAM_NAMES = []

GM_FAMILY_NAMES = [
    "Piano", "Chromatic Percussion", "Organ", "Guitar",
    "Bass", "Strings", "Ensemble", "Brass",
    "Reed", "Pipe", "Synth Lead", "Synth Pad",
    "Synth Effects", "Ethnic", "Percussive", "Sound Effects",
]
LIBRARY_REPORT_MD = ROOT / "reference-library" / "library-inventory.md"
LIBRARY_REPORT_CSV = ROOT / "reference-library" / "library-inventory.csv"


def set_library_progress(
    *,
    active: bool,
    stage: str,
    current: int = 0,
    total: int = 0,
    percent: float | int | None = None,
    catalog_total: int = 0,
    message: str = "",
) -> None:
    current = max(0, int(current or 0))
    total = max(0, int(total or 0))
    if percent is None:
        percent = (current / total * 100.0) if total > 0 else (100.0 if not active else 0.0)
    pct = max(0.0, min(100.0, float(percent)))
    with LIBRARY_PROGRESS_LOCK:
        LIBRARY_PROGRESS.update({
            "active": bool(active),
            "stage": str(stage or "idle"),
            "current": current,
            "total": total,
            "percent": round(pct, 1),
            "catalogTotal": max(0, int(catalog_total or 0)),
            "message": str(message or ""),
        })


def library_progress_snapshot() -> dict:
    with LIBRARY_PROGRESS_LOCK:
        return {"ok": True, **LIBRARY_PROGRESS}


def gm_program_label(program: int) -> str:
    if 0 <= program < len(GM_PROGRAM_NAMES):
        return str(GM_PROGRAM_NAMES[program])
    return f"Program {program}"


def gm_family_label(program: int) -> str:
    if 0 <= program <= 127:
        return GM_FAMILY_NAMES[program // 8]
    return "Unknown"


def markdown_count_table(counter: Counter, first_col: str) -> list[str]:
    lines = [f"| {first_col} | Count |", "|---|---:|"]
    for key, count in counter.most_common():
        lines.append(f"| {str(key).replace('|', '/')} | {count:,} |")
    if len(lines) == 2:
        lines.append("| — | 0 |")
    return lines


def build_library_inventory_report() -> dict:
    payload = build_library_catalog()
    entries = list(payload.get("entries") or [])
    total = len(entries)

    by_source = Counter(str(item.get("source") or "unknown") for item in entries)
    by_genre = Counter(str(item.get("genre") or "unknown") for item in entries)
    by_kind = Counter(str(item.get("kind") or "unclassified") for item in entries)
    by_method = Counter(str(item.get("classificationMethod") or "unknown") for item in entries)
    by_family = Counter()
    by_program = Counter()
    no_program = 0

    for item in entries:
        programs = []
        for raw in item.get("classificationPrograms") or []:
            try:
                program = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= program <= 127:
                programs.append(program)
        programs = sorted(set(programs))
        if not programs:
            no_program += 1
            continue
        for program in programs:
            by_family[gm_family_label(program)] += 1
            by_program[f"GM {program} · {gm_program_label(program)}"] += 1

    source_roles = defaultdict(Counter)
    source_genres = defaultdict(Counter)
    for item in entries:
        source = str(item.get("source") or "unknown")
        source_roles[source][str(item.get("kind") or "unclassified")] += 1
        source_genres[source][str(item.get("genre") or "unknown")] += 1

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    md = [
        "# MIDI Library Inventory",
        "",
        f"Generated: {now}",
        f"Library root: {LIBRARY_ROOT}",
        f"Mode: **{payload.get('mode') or 'raw'}**",
        f"ZIP packs: **{int(payload.get('packCount') or 0):,}**",
        f"Total MIDI: **{total:,}**",
        "",
        "Generated from the local Style Library index. Original MIDI files stay local.",
        "",
        "## Sources",
        "",
    ]
    md.extend(markdown_count_table(by_source, "Source"))
    md.extend(["", "## Styles / genres", ""])
    md.extend(markdown_count_table(by_genre, "Style"))
    md.extend(["", "## Musical roles", ""])
    md.extend(markdown_count_table(by_kind, "Role"))
    md.extend(["", "## Classification methods", ""])
    md.extend(markdown_count_table(by_method, "Method"))
    md.extend(["", "## GM instrument families", ""])
    md.extend(markdown_count_table(by_family, "Family"))
    md.extend([
        "",
        f"MIDI without encoded GM Program Change in the catalogue: **{no_program:,}**",
        "",
        "## GM programs",
        "",
    ])
    md.extend(markdown_count_table(by_program, "Program"))

    md.extend(["", "## Source breakdown", ""])
    for source, count in by_source.most_common():
        roles = ", ".join(f"{k}: {v:,}" for k, v in source_roles[source].most_common())
        genres = ", ".join(f"{k}: {v:,}" for k, v in source_genres[source].most_common())
        md.extend([
            f"### {source}",
            "",
            f"- MIDI: **{count:,}**",
            f"- Roles: {roles or '—'}",
            f"- Styles: {genres or '—'}",
            "",
        ])

    md.extend([
        "## Full catalogue",
        "",
        "The exhaustive row-by-row list is stored next to this note as library-inventory.csv.",
        "CSV columns: id, name, source, genre, role, GM programs, instrument families, container, member, pack.",
        "",
    ])

    LIBRARY_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY_REPORT_MD.write_text("\n".join(md), encoding="utf-8", newline="\n")

    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer)
    writer.writerow([
        "id", "name", "source", "genre", "role",
        "gm_programs", "instrument_families",
        "container", "member", "pack",
    ])
    for item in sorted(
        entries,
        key=lambda x: (
            str(x.get("source") or ""),
            str(x.get("genre") or ""),
            str(x.get("kind") or ""),
            str(x.get("name") or ""),
        ),
    ):
        programs = []
        for raw in item.get("classificationPrograms") or []:
            try:
                p = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= p <= 127:
                programs.append(p)
        programs = sorted(set(programs))
        writer.writerow([
            item.get("id") or "",
            item.get("name") or "",
            item.get("source") or "",
            item.get("genre") or "",
            item.get("kind") or "",
            "; ".join(f"GM {p} {gm_program_label(p)}" for p in programs),
            "; ".join(sorted({gm_family_label(p) for p in programs})),
            item.get("container") or "",
            item.get("member") or "",
            item.get("pack") or "",
        ])
    LIBRARY_REPORT_CSV.write_text(csv_buffer.getvalue(), encoding="utf-8", newline="")

    branch = current_branch()
    ensure_remote_is_safe_to_push(branch)
    rel_md = str(LIBRARY_REPORT_MD.relative_to(ROOT)).replace(chr(92), "/")
    rel_csv = str(LIBRARY_REPORT_CSV.relative_to(ROOT)).replace(chr(92), "/")
    run_git("add", "--", rel_md, rel_csv)
    changed = commit_staged("Update MIDI library inventory")
    run_git("push", "origin", branch)

    return {
        "ok": True,
        "changed": changed,
        "commit": short_sha(),
        "branch": branch,
        "total": total,
        "sources": len(by_source),
        "genres": len(by_genre),
        "roles": len(by_kind),
        "withoutProgram": no_program,
        "files": [rel_md, rel_csv],
    }


def slugify_cloud_project(value: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    if raw:
        return raw[:64]
    digest = hashlib.sha1(str(value).encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"project-{digest}"


def allocate_cloud_project_id(project_name: str) -> str:
    root = PROJECTS / "cloud"
    root.mkdir(parents=True, exist_ok=True)
    base = slugify_cloud_project(project_name or "project")
    candidate = base
    suffix = 2
    while (root / candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def safe_track_filename(index: int, name: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(name or "Track")).strip(" ._")
    stem = re.sub(r"\\s+", " ", stem)[:80] or "Track"
    return f"{index:03d} - {stem}.mid"


def decode_midi_b64(value: str, label: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} MIDI payload is missing")
    try:
        data = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{label} MIDI payload is invalid") from exc
    if len(data) < 14 or not data.startswith(b"MThd"):
        raise ValueError(f"{label} is not a valid Standard MIDI file")
    return data


def list_cloud_projects() -> dict:
    root = PROJECTS / "cloud"
    projects = []
    if root.exists():
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            manifest_path = folder / "manifest.json"
            project_path = folder / "midi-host" / "project.json"
            if not manifest_path.exists() or not project_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                project = json.loads(project_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                continue

            ppq = int(project.get("ppq") or 480)
            length_ticks = int(project.get("lengthTicks") or 0)
            bars = 0
            if ppq > 0 and length_ticks > 0:
                bars = max(1, round(length_ticks / (ppq * 4)))

            tracks = project.get("tracks") if isinstance(project.get("tracks"), list) else []
            projects.append({
                "id": str(manifest.get("id") or folder.name),
                "name": str(manifest.get("name") or project.get("name") or folder.name),
                "path": f"projects/cloud/{folder.name}",
                "createdAt": manifest.get("createdAt"),
                "updatedAt": manifest.get("updatedAt"),
                "tempo": project.get("tempo") or 120,
                "ppq": ppq,
                "bars": bars,
                "trackCount": len(tracks),
                "editors": manifest.get("editors") or {},
            })

    projects.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
    return {"ok": True, "projects": projects, "count": len(projects)}


def load_cloud_project(project_id: str) -> dict:
    project_id = str(project_id or "").strip()
    if not project_id:
        raise ValueError("Project id is required")

    safe_id = slugify_cloud_project(project_id)
    if safe_id != project_id:
        raise ValueError("Invalid project id")

    root = (PROJECTS / "cloud" / safe_id).resolve()
    cloud_root = (PROJECTS / "cloud").resolve()
    if cloud_root not in root.parents:
        raise ValueError("Invalid cloud project path")

    manifest_path = root / "manifest.json"
    project_path = root / "midi-host" / "project.json"
    session_path = root / "midi-host" / "session.json"

    if not manifest_path.exists() or not project_path.exists():
        raise FileNotFoundError(f"Cloud project not found: {project_id}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    project = json.loads(project_path.read_text(encoding="utf-8"))
    session = {}
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))

    if not isinstance(project, dict) or not isinstance(project.get("tracks"), list):
        raise ValueError("Cloud project JSON is invalid")

    return {
        "ok": True,
        "projectId": safe_id,
        "projectPath": f"projects/cloud/{safe_id}",
        "manifest": manifest if isinstance(manifest, dict) else {},
        "project": project,
        "session": session if isinstance(session, dict) else {},
    }


def save_cloud_project(payload: dict) -> dict:
    project_name = " ".join(
        str(payload.get("projectName") or "Project").replace("\r", " ").replace("\n", " ").split()
    )[:120] or "Project"

    requested_id = str(payload.get("projectId") or "").strip()
    project_id = slugify_cloud_project(requested_id) if requested_id else allocate_cloud_project_id(project_name)

    root = (PROJECTS / "cloud" / project_id).resolve()
    cloud_root = (PROJECTS / "cloud").resolve()
    if cloud_root not in root.parents:
        raise ValueError("Invalid cloud project path")

    project_json = payload.get("project")
    overview_json = payload.get("overview")
    session_json = payload.get("session")
    overview_md = payload.get("overviewMd")
    if not isinstance(project_json, dict) or not isinstance(project_json.get("tracks"), list):
        raise ValueError("project must contain tracks[]")
    if overview_json is not None and not isinstance(overview_json, dict):
        raise ValueError("overview must be an object")
    if session_json is not None and not isinstance(session_json, dict):
        raise ValueError("session must be an object")
    if overview_md is not None and not isinstance(overview_md, str):
        raise ValueError("overviewMd must be text")

    arrangement = decode_midi_b64(payload.get("arrangementMidi"), "Arrangement")
    track_payloads = payload.get("trackMidis")
    if not isinstance(track_payloads, list):
        raise ValueError("trackMidis must be an array")

    library_clips = payload.get("libraryClips") or []
    if not isinstance(library_clips, list):
        raise ValueError("libraryClips must be an array")

    branch = current_branch()
    ensure_remote_is_safe_to_push(branch)

    tracks_dir = root / "midi-host" / "tracks"
    clips_dir = root / "midi-host" / "clips"
    root.mkdir(parents=True, exist_ok=True)
    (root / "midi-host").mkdir(parents=True, exist_ok=True)
    if tracks_dir.exists():
        shutil.rmtree(tracks_dir)
    if clips_dir.exists():
        shutil.rmtree(clips_dir)
    tracks_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = root / "manifest.json"
    created_at = None
    if manifest_path.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            created_at = previous_manifest.get("createdAt")
        except (OSError, ValueError, json.JSONDecodeError):
            created_at = None
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    created_at = created_at or now
    written_paths = []

    def write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temp, path)
        written_paths.append(path)

    def write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(data)
        os.replace(temp, path)
        written_paths.append(path)

    track_manifest = []
    for i, item in enumerate(track_payloads, start=1):
        if not isinstance(item, dict):
            raise ValueError("trackMidis entries must be objects")
        name = str(item.get("name") or f"Track {i}")
        midi = decode_midi_b64(item.get("midi"), name)
        filename = safe_track_filename(i, name)
        target = tracks_dir / filename
        write_bytes(target, midi)
        track_manifest.append({"index": i, "name": name, "file": f"midi-host/tracks/{filename}"})

    clip_manifest = []
    seen_clip_ids = set()
    for i, clip in enumerate(library_clips, start=1):
        if not isinstance(clip, dict):
            continue
        clip_id = str(clip.get("id") or "").strip()
        if not clip_id or clip_id in seen_clip_ids:
            continue
        seen_clip_ids.add(clip_id)
        try:
            midi_data, entry = read_library_midi(clip_id)
        except FileNotFoundError:
            continue

        clip_name = str(
            clip.get("originalName") or clip.get("name") or entry.get("name") or f"clip-{i}"
        )
        filename = safe_track_filename(i, clip_name)
        target = clips_dir / filename
        write_bytes(target, midi_data)
        clip_manifest.append({
            "id": clip_id,
            "name": str(clip.get("name") or clip_name),
            "originalName": str(entry.get("name") or clip_name),
            "source": str(clip.get("source") or entry.get("source") or ""),
            "genre": str(clip.get("genre") or entry.get("genre") or ""),
            "role": str(clip.get("role") or entry.get("kind") or ""),
            "file": f"midi-host/clips/{filename}",
        })

    project_json = dict(project_json)
    project_json["cloudProject"] = {
        "id": project_id,
        "path": f"projects/cloud/{project_id}",
        "savedAt": now,
    }

    write_text(root / "midi-host" / "project.json", json.dumps(project_json, ensure_ascii=False, indent=2))
    write_text(root / "midi-host" / "overview.json", json.dumps(overview_json or {}, ensure_ascii=False, indent=2))
    write_text(root / "midi-host" / "overview.md", overview_md or "# Arrangement overview\n")
    write_text(root / "midi-host" / "session.json", json.dumps(session_json or {}, ensure_ascii=False, indent=2))
    write_bytes(root / "midi-host" / "arrangement.mid", arrangement)

    manifest = {
        "schema": 1,
        "id": project_id,
        "name": project_name,
        "createdAt": created_at,
        "updatedAt": now,
        "editors": {"midiHost": True, "chiptune": False},
        "files": {
            "midiHostProject": "midi-host/project.json",
            "session": "midi-host/session.json",
            "overviewJson": "midi-host/overview.json",
            "overviewMarkdown": "midi-host/overview.md",
            "arrangementMidi": "midi-host/arrangement.mid",
            "tracks": track_manifest,
            "clips": clip_manifest,
        },
    }
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    readme = [
        f"# {project_name}",
        "",
        "Cloud project snapshot generated by MIDI Host.",
        "",
        f"- Project ID: {project_id}",
        f"- Updated: {now}",
        f"- Tracks: {len(track_manifest)}",
        f"- BPM: {project_json.get('tempo', 120)}",
        f"- PPQ: {project_json.get('ppq', 480)}",
        "",
        "Files:",
        "- midi-host/project.json — complete editable MIDI Host project state",
        "- midi-host/session.json — editor/session settings",
        "- midi-host/arrangement.mid — complete Standard MIDI arrangement",
        "- midi-host/tracks/ — one Standard MIDI file per project track",
        "- midi-host/clips/ — original Style Library MIDI files actually used in the project",
        "- midi-host/overview.json / overview.md — structural analysis and markers",
        "",
        "Future Chiptune Sequencer data can live in this same project folder under chiptune/.",
        "",
    ]
    write_text(root / "README.md", "\n".join(readme))

    rel_root = str(root.relative_to(ROOT)).replace(chr(92), "/")
    run_git("add", "--", rel_root)
    changed = commit_staged(f"Save cloud project: {project_name}")
    run_git("push", "origin", branch)

    return {
        "ok": True,
        "changed": changed,
        "projectId": project_id,
        "projectPath": rel_root,
        "commit": short_sha(),
        "branch": branch,
        "trackCount": len(track_manifest),
        "clipCount": len(clip_manifest),
        "files": [str(path.relative_to(ROOT)).replace(chr(92), "/") for path in written_paths],
    }


def slugify_pack_part(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return text or "other"


DRUM_FILL_RE = re.compile(r"(?:^|[^a-z0-9])(?:drum[-_ ]?fill|fills?)(?:[^a-z0-9]|$)", re.IGNORECASE)


def library_entry_is_drum_fill(item: dict) -> bool:
    """Keep drum fills separate from ordinary drum grooves when filenames identify them."""
    roles = {str(role).lower() for role in (item.get("classificationRoles") or [])}
    kind = str(item.get("kind") or "").lower()
    is_drums = kind in {"drums", "drum-fill"} or "drums" in roles
    if not is_drums:
        return False
    text = " ".join(
        str(item.get(key) or "")
        for key in ("name", "member", "container", "source")
    )
    return bool(DRUM_FILL_RE.search(text))


def apply_library_display_categories(entries: list[dict]) -> None:
    for item in entries:
        if library_entry_is_drum_fill(item):
            item["kind"] = "drum-fill"


def catalog_payload(entries: list[dict], mode: str, pack_count: int = 0) -> dict:
    apply_library_display_categories(entries)
    counts = {
        "total": len(entries),
        "genre": dict(Counter(item["genre"] for item in entries)),
        "kind": dict(Counter(item["kind"] for item in entries)),
        "source": dict(Counter(item["source"] for item in entries)),
        "classificationMethod": dict(
            Counter(item.get("classificationMethod", "unknown") for item in entries)
        ),
    }
    return {
        "root": str(LIBRARY_ROOT),
        "mode": mode,
        "packRoot": str(PACK_ROOT) if mode == "packs" else None,
        "packCount": pack_count,
        "entries": entries,
        "counts": counts,
    }


def library_material_type(item: dict) -> str:
    """Separate ordinary loops from very long constructor/performance material."""
    bars = item.get("barsEstimate")
    try:
        if bars is not None:
            return "constructor" if float(bars) > 16.0 else "loop"
    except (TypeError, ValueError):
        pass

    explicit = str(item.get("contentType") or "").strip().lower()
    if explicit in {"loop", "constructor"}:
        return explicit
    if str(item.get("kind") or "").lower() == "arrangement":
        return "constructor"
    return "loop"


def midi_bars_estimate(data: bytes, member: str = "") -> float | None:
    """Estimate musical length in bars from note ends; GMD time signature is in filename."""
    try:
        parsed = parse_midi(data)
    except Exception:
        return None

    ppq = int(parsed.get("ppq") or 0)
    notes = parsed.get("notes") or []
    if ppq <= 0 or not notes:
        return None

    max_tick = max(int(start) + max(1, int(duration)) for start, duration, *_ in notes)
    numerator = 4
    denominator = 4
    match = re.search(r"_(\d+)-(\d+)\.(?:mid|midi)$", str(member), re.IGNORECASE)
    if match:
        try:
            numerator = max(1, int(match.group(1)))
            denominator = max(1, int(match.group(2)))
        except ValueError:
            numerator, denominator = 4, 4

    ticks_per_bar = ppq * numerator * 4 / denominator
    if ticks_per_bar <= 0:
        return None
    return round(max_tick / ticks_per_bar, 3)


def enrich_pack_material_types(entries: list[dict], locators: dict[str, tuple[str, str, str | None]]) -> None:
    """Read Groove Dataset MIDI and report visible progress while measuring lengths."""
    by_pack: defaultdict[str, list[dict]] = defaultdict(list)
    for item in entries:
        source = str(item.get("source") or "").lower()
        if "groove-v1.0.0" in source or source == "groove":
            locator = locators.get(str(item.get("id") or ""))
            if locator and locator[0] == "pack":
                by_pack[locator[1]].append(item)
        else:
            item["contentType"] = library_material_type(item)

    total = sum(len(items) for items in by_pack.values())
    processed = 0
    set_library_progress(
        active=True,
        stage="measuring",
        current=0,
        total=total,
        percent=5,
        catalog_total=len(entries),
        message="Measuring Groove MIDI lengths",
    )

    for pack_path, items in by_pack.items():
        try:
            with zipfile.ZipFile(pack_path) as zf:
                for item in items:
                    locator = locators.get(str(item.get("id") or ""))
                    member = locator[2] if locator else None
                    if not member:
                        item["contentType"] = library_material_type(item)
                    else:
                        try:
                            data = zf.read(member)
                            bars = midi_bars_estimate(data, str(item.get("member") or member))
                        except (KeyError, OSError, ValueError):
                            bars = None
                        if bars is not None:
                            item["barsEstimate"] = bars
                        item["contentType"] = library_material_type(item)

                    processed += 1
                    if processed == total or processed % 8 == 0:
                        scan_pct = (processed / total) if total else 1.0
                        set_library_progress(
                            active=True,
                            stage="measuring",
                            current=processed,
                            total=total,
                            percent=5 + scan_pct * 90,
                            catalog_total=len(entries),
                            message="Measuring Groove MIDI lengths",
                        )
        except (OSError, ValueError, zipfile.BadZipFile):
            for item in items:
                item["contentType"] = library_material_type(item)
                processed += 1
                if processed == total or processed % 8 == 0:
                    scan_pct = (processed / total) if total else 1.0
                    set_library_progress(
                        active=True,
                        stage="measuring",
                        current=processed,
                        total=total,
                        percent=5 + scan_pct * 90,
                        catalog_total=len(entries),
                        message="Measuring Groove MIDI lengths",
                    )


def load_pack_catalog_locked() -> dict:
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS, LIBRARY_MODE
    set_library_progress(
        active=True,
        stage="index",
        percent=1,
        message="Reading MIDI library index",
    )
    payload = json.loads(PACK_INDEX_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not isinstance(payload.get("entries"), list):
        raise ValueError("Unsupported Style Library pack index")

    # Pack indexes can outlive classifier improvements. Re-tag entries while
    # loading so a one-click app update immediately exposes corrected styles
    # without forcing a costly repack of the local MIDI library.
    entries = [dict(item) for item in payload["entries"]]
    locators: dict[str, tuple[str, str, str | None]] = {}
    for item in entries:
        pack_rel = item.get("pack")
        pack_member = item.get("packMember")
        item_id = item.get("id")
        if not item_id or not pack_rel or not pack_member:
            raise ValueError("Invalid entry in Style Library pack index")
        source = str(item.get("source") or "")
        member = str(item.get("member") or pack_member or item.get("name") or "")
        inferred_genre, _ = infer_library_tags(source, member)
        if inferred_genre:
            item["genre"] = inferred_genre
        locators[item_id] = ("pack", str((PACK_ROOT / pack_rel).resolve()), pack_member)

    enrich_pack_material_types(entries, locators)

    LIBRARY_ENTRIES = entries
    LIBRARY_LOCATORS = locators
    LIBRARY_MODE = "packs"
    set_library_progress(
        active=False,
        stage="ready",
        current=len(entries),
        total=len(entries),
        percent=100,
        catalog_total=len(entries),
        message="MIDI library ready",
    )
    return catalog_payload(entries, "packs", len(payload.get("packs") or []))


def midi_cache_path(item_id: str) -> Path:
    return MIDI_CACHE_DIR / item_id[:2] / f"{item_id}.bin"


def read_cached_midi(item_id: str) -> bytes | None:
    try:
        return midi_cache_path(item_id).read_bytes()
    except OSError:
        return None


def write_cached_midi(item_id: str, data: bytes) -> None:
    try:
        target = midi_cache_path(item_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        temp.write_bytes(data)
        os.replace(temp, target)
    except OSError:
        pass


def load_classification_cache() -> dict[str, dict]:
    try:
        payload = json.loads(CLASSIFICATION_CACHE_PATH.read_text(encoding="utf-8"))
        if payload.get("version") != CLASSIFICATION_CACHE_VERSION:
            return {}
        entries = payload.get("entries")
        return entries if isinstance(entries, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def save_classification_cache(entries: dict[str, dict]) -> None:
    try:
        payload = {"version": CLASSIFICATION_CACHE_VERSION, "entries": entries}
        temp = CLASSIFICATION_CACHE_PATH.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temp, CLASSIFICATION_CACHE_PATH)
    except OSError:
        # The library may live on a read-only volume. Classification still works;
        # only the persistent speed-up is lost.
        pass


def classify_library_item(
    item_id: str,
    fingerprint: str,
    source: str,
    member: str,
    data_loader,
    cache: dict[str, dict],
    force: bool,
) -> dict:
    cached = cache.get(item_id)
    if (
        isinstance(cached, dict)
        and cached.get("fingerprint") == fingerprint
        and cached.get("kind")
    ):
        return cached

    data = data_loader()
    result = classify_midi(data, source=source, member=member)
    write_cached_midi(item_id, data)
    record = {"fingerprint": fingerprint, **result}
    cache[item_id] = record
    return record


GROOVE_PRIMARY_STYLES = (
    "afrobeat",
    "afrocuban",
    "blues",
    "country",
    "dance",
    "funk",
    "gospel",
    "highlife",
    "hiphop",
    "jazz",
    "latin",
    "middleeastern",
    "neworleans",
    "pop",
    "punk",
    "reggae",
    "rock",
    "soul",
)


def groove_primary_style(source: str, member: str) -> str | None:
    """Return the official primary GMD style encoded in the MIDI filename."""
    source_text = source.lower()
    if "groove-v1.0.0" not in source_text and source_text != "groove":
        return None

    # GMD filenames are e.g. 1_funk-groove1_138_beat_4-4.mid.
    # Match whole normalized tokens so "rock" does not accidentally match
    # unrelated words and secondary labels such as "groove1" stay untouched.
    filename = Path(member).name.lower()
    tokens = set(re.sub(r"[^a-z0-9]+", " ", filename).split())
    return next((style for style in GROOVE_PRIMARY_STYLES if style in tokens), None)


def infer_library_tags(source: str, member: str) -> tuple[str, str]:
    text = f"{source} {member}".lower().replace("_", " ").replace("-", " ")

    gmd_style = groove_primary_style(source, member)
    if gmd_style:
        genre = gmd_style
    elif "tech house" in text or "techhouse" in text:
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

    if gmd_style:
        kind = "drums"
    elif any(word in text for word in ("bassline", "bass line", " bass ", "/bass", "\\bass", "sub bass")):
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


def build_library_catalog(force: bool = False, prefer_packs: bool = True) -> dict:
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS, LIBRARY_MODE
    with LIBRARY_LOCK:
        if prefer_packs and PACK_INDEX_PATH.exists():
            if LIBRARY_MODE == "packs" and LIBRARY_ENTRIES and not force:
                set_library_progress(
                    active=False,
                    stage="ready",
                    current=len(LIBRARY_ENTRIES),
                    total=len(LIBRARY_ENTRIES),
                    percent=100,
                    catalog_total=len(LIBRARY_ENTRIES),
                    message="MIDI library ready",
                )
                return catalog_payload(
                    LIBRARY_ENTRIES,
                    "packs",
                    len({item.get("pack") for item in LIBRARY_ENTRIES if item.get("pack")}),
                )
            try:
                return load_pack_catalog_locked()
            except (OSError, ValueError, json.JSONDecodeError):
                # Fall back to raw sources if the derived pack index is damaged.
                pass

        if LIBRARY_MODE == "raw" and LIBRARY_ENTRIES and not force:
            entries = LIBRARY_ENTRIES
        else:
            entries: list[dict] = []
            locators: dict[str, tuple[str, str, str | None]] = {}
            classification_cache = load_classification_cache()
            cache_changed = False

            if LIBRARY_ROOT.exists():
                excluded_roots = {PACK_ROOT, PACK_BUILD_ROOT, PACK_OLD_ROOT}
                files = sorted(
                    p for p in LIBRARY_ROOT.rglob("*")
                    if p.is_file() and not any(root == p or root in p.parents for root in excluded_roots)
                )
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
                    genre, _ = infer_library_tags(source, rel)
                    key = f"file|{rel}"
                    item_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
                    stat = path.stat()
                    fingerprint = f"file:{stat.st_size}:{stat.st_mtime_ns}"
                    previous = classification_cache.get(item_id)
                    classification = classify_library_item(
                        item_id,
                        fingerprint,
                        source,
                        rel,
                        path.read_bytes,
                        classification_cache,
                        force,
                    )
                    if classification is not previous:
                        cache_changed = True
                    entries.append(
                        {
                            "id": item_id,
                            "name": path.name,
                            "source": source,
                            "genre": genre,
                            "kind": classification["kind"],
                            "classificationConfidence": classification.get("confidence", 0.0),
                            "classificationMethod": classification.get("method", "content"),
                            "classificationReason": classification.get("reason", ""),
                            "classificationRoles": classification.get("roles", []),
                            "classificationPrograms": classification.get("programs", []),
                            "container": rel,
                            "member": None,
                            "size": stat.st_size,
                        }
                    )
                    locators[item_id] = ("file", str(path), None)

                for archive in archive_paths:
                    rel = archive.relative_to(LIBRARY_ROOT).as_posix()
                    source = library_source_name(archive)
                    low = archive.name.lower()
                    archive_stat = archive.stat()
                    archive_fingerprint = f"{archive_stat.st_size}:{archive_stat.st_mtime_ns}"
                    try:
                        if low.endswith(".zip"):
                            with zipfile.ZipFile(archive) as zf:
                                members = [
                                    info
                                    for info in zf.infolist()
                                    if not info.is_dir()
                                    and info.filename.lower().endswith((".mid", ".midi"))
                                ]
                                for info in members:
                                    member = info.filename
                                    size = info.file_size
                                    genre, _ = infer_library_tags(source, member)
                                    key = f"archive|{rel}|{member}"
                                    item_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
                                    fingerprint = f"zip:{archive_fingerprint}:{size}:{info.CRC}"
                                    previous = classification_cache.get(item_id)
                                    classification = classify_library_item(
                                        item_id,
                                        fingerprint,
                                        source,
                                        member,
                                        lambda info=info: zf.read(info),
                                        classification_cache,
                                        force,
                                    )
                                    if classification is not previous:
                                        cache_changed = True
                                    entries.append(
                                        {
                                            "id": item_id,
                                            "name": Path(member).name,
                                            "source": source,
                                            "genre": genre,
                                            "kind": classification["kind"],
                                            "classificationConfidence": classification.get("confidence", 0.0),
                                            "classificationMethod": classification.get("method", "content"),
                                            "classificationReason": classification.get("reason", ""),
                                            "classificationRoles": classification.get("roles", []),
                                            "classificationPrograms": classification.get("programs", []),
                                            "container": rel,
                                            "member": member,
                                            "size": size,
                                        }
                                    )
                                    locators[item_id] = ("archive", str(archive), member)
                        else:
                            with tarfile.open(archive, "r:*") as tf:
                                # Iterate sequentially: repeatedly seeking inside a large
                                # compressed tar archive would make the first full
                                # classification unnecessarily slow.
                                for tar_member in tf:
                                    if (
                                        not tar_member.isfile()
                                        or not tar_member.name.lower().endswith((".mid", ".midi"))
                                    ):
                                        continue
                                    member = tar_member.name
                                    size = tar_member.size
                                    genre, _ = infer_library_tags(source, member)
                                    key = f"archive|{rel}|{member}"
                                    item_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
                                    fingerprint = (
                                        f"tar:{archive_fingerprint}:{size}:"
                                        f"{tar_member.mtime}:{tar_member.offset_data}"
                                    )
                                    previous = classification_cache.get(item_id)

                                    def load_tar_member(tm=tar_member):
                                        fh = tf.extractfile(tm)
                                        if fh is None:
                                            raise FileNotFoundError("MIDI member not found in archive")
                                        return fh.read()

                                    classification = classify_library_item(
                                        item_id,
                                        fingerprint,
                                        source,
                                        member,
                                        load_tar_member,
                                        classification_cache,
                                        force,
                                    )
                                    if classification is not previous:
                                        cache_changed = True
                                    entries.append(
                                        {
                                            "id": item_id,
                                            "name": Path(member).name,
                                            "source": source,
                                            "genre": genre,
                                            "kind": classification["kind"],
                                            "classificationConfidence": classification.get("confidence", 0.0),
                                            "classificationMethod": classification.get("method", "content"),
                                            "classificationReason": classification.get("reason", ""),
                                            "classificationRoles": classification.get("roles", []),
                                            "classificationPrograms": classification.get("programs", []),
                                            "container": rel,
                                            "member": member,
                                            "size": size,
                                        }
                                    )
                                    locators[item_id] = ("archive", str(archive), member)
                    except (OSError, zipfile.BadZipFile, tarfile.TarError, ValueError):
                        continue

            if cache_changed:
                save_classification_cache(classification_cache)

            entries.sort(
                key=lambda item: (
                    item["genre"],
                    item["kind"],
                    item["source"],
                    item["name"].lower(),
                )
            )
            LIBRARY_ENTRIES = entries
            LIBRARY_LOCATORS = locators
            LIBRARY_MODE = "raw"

        set_library_progress(
            active=False,
            stage="ready",
            current=len(entries),
            total=len(entries),
            percent=100,
            catalog_total=len(entries),
            message="MIDI library ready",
        )
        return catalog_payload(entries, "raw")


def warm_raw_archive_cache() -> dict:
    """Fill only missing archive cache entries, scanning each required archive once."""
    missing: dict[tuple[str, str], str] = {}
    missing_archives: set[str] = set()
    for item_id, (mode, path_text, member) in LIBRARY_LOCATORS.items():
        if mode != "archive" or not member:
            continue
        if read_cached_midi(item_id) is None:
            missing[(path_text, member)] = item_id
            missing_archives.add(path_text)

    if not missing:
        return {"files": 0, "bytes": 0}

    cached_files = 0
    cached_bytes = 0
    for path_text in sorted(missing_archives):
        archive = Path(path_text)
        if archive.name.lower().endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    item_id = missing.get((path_text, info.filename))
                    if not item_id:
                        continue
                    data = zf.read(info)
                    write_cached_midi(item_id, data)
                    cached_files += 1
                    cached_bytes += len(data)
        else:
            with tarfile.open(archive, "r:*") as tf:
                for member_info in tf:
                    if not member_info.isfile():
                        continue
                    item_id = missing.get((path_text, member_info.name))
                    if not item_id:
                        continue
                    fh = tf.extractfile(member_info)
                    if fh is None:
                        continue
                    data = fh.read()
                    write_cached_midi(item_id, data)
                    cached_files += 1
                    cached_bytes += len(data)

    return {"files": cached_files, "bytes": cached_bytes}


def source_bytes_for_pack(item_id: str, locator: tuple[str, str, str | None]) -> bytes:
    mode, path_text, member = locator
    if mode == "file":
        return Path(path_text).read_bytes()

    cached = read_cached_midi(item_id)
    if cached is not None:
        return cached

    path = Path(path_text)
    if mode == "pack" or path.name.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            return zf.read(member)
    with tarfile.open(path, "r:*") as tf:
        fh = tf.extractfile(member)
        if fh is None:
            raise FileNotFoundError("MIDI member not found in archive")
        return fh.read()


def build_style_packs(max_files: int = PACK_MAX_FILES) -> dict:
    """Rebuild derived ZIP packs grouped by genre / role / source."""
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS, LIBRARY_MODE

    raw = build_library_catalog(force=True, prefer_packs=False)
    if not raw["entries"]:
        raise FileNotFoundError(f"No MIDI files found under {LIBRARY_ROOT}")

    # build_library_catalog walks TAR.GZ sequentially when classification is new.
    # This second pass only fills any missing cache files and is still sequential.
    warm = warm_raw_archive_cache()

    entries = [dict(item) for item in LIBRARY_ENTRIES]
    locators = dict(LIBRARY_LOCATORS)

    if PACK_BUILD_ROOT.exists():
        shutil.rmtree(PACK_BUILD_ROOT)
    PACK_BUILD_ROOT.mkdir(parents=True, exist_ok=True)

    grouped: defaultdict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for item in entries:
        grouped[(item["genre"], item["kind"], item["source"])].append(item)

    index_entries: list[dict] = []
    pack_rows: list[dict] = []
    total_pack_estimate = sum(
        max(1, (len(group) + max_files - 1) // max_files)
        for group in grouped.values()
    )
    print(
        f"Style Library: {len(entries)} MIDI classified; "
        f"building {total_pack_estimate} categorized ZIP packs..."
    )

    try:
        for (genre, kind, source), group in sorted(grouped.items()):
            group.sort(key=lambda item: (item["name"].lower(), item["id"]))
            genre_slug = slugify_pack_part(genre)
            kind_slug = slugify_pack_part(kind)
            source_slug = slugify_pack_part(source)+"-"+hashlib.sha1(source.encode("utf-8")).hexdigest()[:6]
            total_parts = max(1, (len(group) + max_files - 1) // max_files)

            for part_idx in range(total_parts):
                chunk = group[part_idx * max_files:(part_idx + 1) * max_files]
                filename = f"{source_slug}__{part_idx + 1:03d}.zip"
                pack_rel = Path(genre_slug) / kind_slug / filename
                pack_path = PACK_BUILD_ROOT / pack_rel
                pack_path.parent.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(
                    pack_path,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                ) as zf:
                    for item in chunk:
                        item_id = item["id"]
                        locator = locators.get(item_id)
                        if locator is None:
                            raise FileNotFoundError(f"Missing source locator for {item_id}")
                        data = source_bytes_for_pack(item_id, locator)
                        member_name = f"{item_id}__{Path(item['name']).name}"
                        zf.writestr(member_name, data)

                        packed = dict(item)
                        packed["pack"] = pack_rel.as_posix()
                        packed["packMember"] = member_name
                        index_entries.append(packed)

                pack_rows.append({
                    "path": pack_rel.as_posix(),
                    "genre": genre,
                    "kind": kind,
                    "source": source,
                    "files": len(chunk),
                })
                built = len(pack_rows)
                if built == 1 or built % 10 == 0 or built == total_pack_estimate:
                    print(f"Style Library packs: {built}/{total_pack_estimate}")

        index_entries.sort(
            key=lambda item: (
                item["genre"],
                item["kind"],
                item["source"],
                item["name"].lower(),
            )
        )
        index_payload = {
            "schema": 1,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "maxFilesPerPack": max_files,
            "total": len(index_entries),
            "packs": pack_rows,
            "entries": index_entries,
        }
        (PACK_BUILD_ROOT / "library-index.json").write_text(
            json.dumps(index_payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        if PACK_OLD_ROOT.exists():
            shutil.rmtree(PACK_OLD_ROOT, ignore_errors=True)
        if PACK_ROOT.exists():
            PACK_ROOT.rename(PACK_OLD_ROOT)
        try:
            PACK_BUILD_ROOT.rename(PACK_ROOT)
        except Exception:
            if PACK_OLD_ROOT.exists() and not PACK_ROOT.exists():
                PACK_OLD_ROOT.rename(PACK_ROOT)
            raise
        if PACK_OLD_ROOT.exists():
            shutil.rmtree(PACK_OLD_ROOT, ignore_errors=True)

        with LIBRARY_LOCK:
            result = load_pack_catalog_locked()

        return {
            "ok": True,
            "total": len(index_entries),
            "packs": len(pack_rows),
            "maxFilesPerPack": max_files,
            "cachedFiles": warm["files"],
            "cachedBytes": warm["bytes"],
            "root": str(PACK_ROOT),
            "counts": result["counts"],
        }
    finally:
        if PACK_BUILD_ROOT.exists():
            shutil.rmtree(PACK_BUILD_ROOT, ignore_errors=True)


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
    if mode == "pack":
        with zipfile.ZipFile(path) as zf:
            return zf.read(member), entry

    cached = read_cached_midi(item_id)
    if cached is not None:
        return cached, entry

    if path.name.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            data = zf.read(member)
    else:
        with tarfile.open(path, "r:*") as tf:
            fh = tf.extractfile(member)
            if fh is None:
                raise FileNotFoundError("MIDI member not found in archive")
            data = fh.read()

    write_cached_midi(item_id, data)
    return data, entry


def optimize_library(genre: str = "edm", kind: str = "unclassified") -> dict:
    """Warm archive MIDI cache and reclassify the requested unresolved subset."""
    global LIBRARY_ENTRIES
    build_library_catalog()

    targets = {
        item["id"]
        for item in LIBRARY_ENTRIES
        if (not genre or item.get("genre") == genre)
        and (not kind or item.get("kind") == kind)
    }
    classification_cache = load_classification_cache()
    entry_by_id = {item["id"]: item for item in LIBRARY_ENTRIES}
    locator_to_id = {
        (path_text, member): item_id
        for item_id, (mode, path_text, member) in LIBRARY_LOCATORS.items()
        if mode == "archive"
    }

    archive_paths = sorted({
        path_text
        for mode, path_text, _ in LIBRARY_LOCATORS.values()
        if mode == "archive"
    })

    cached_files = 0
    cached_bytes = 0
    reclassified = 0
    program_counts: Counter[int] = Counter()
    role_counts: Counter[str] = Counter()

    for path_text in archive_paths:
        archive = Path(path_text)
        low = archive.name.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith((".mid", ".midi")):
                        continue
                    item_id = locator_to_id.get((path_text, info.filename))
                    if not item_id:
                        continue
                    data = read_cached_midi(item_id)
                    if data is None:
                        data = zf.read(info)
                        write_cached_midi(item_id, data)
                    cached_files += 1
                    cached_bytes += len(data)

                    if item_id in targets:
                        entry = entry_by_id[item_id]
                        result = classify_midi(
                            data,
                            source=entry.get("source", ""),
                            member=entry.get("member") or entry.get("container", ""),
                        )
                        old = classification_cache.get(item_id, {})
                        classification_cache[item_id] = {
                            "fingerprint": old.get("fingerprint", ""),
                            **result,
                        }
                        entry["kind"] = result["kind"]
                        entry["classificationConfidence"] = result.get("confidence", 0.0)
                        entry["classificationMethod"] = result.get("method", "content")
                        entry["classificationReason"] = result.get("reason", "")
                        entry["classificationRoles"] = result.get("roles", [])
                        entry["classificationPrograms"] = result.get("programs", [])
                        program_counts.update(result.get("programs", []))
                        role_counts.update(result.get("roles", []))
                        reclassified += 1
        else:
            with tarfile.open(archive, "r:*") as tf:
                for member_info in tf:
                    if (
                        not member_info.isfile()
                        or not member_info.name.lower().endswith((".mid", ".midi"))
                    ):
                        continue
                    item_id = locator_to_id.get((path_text, member_info.name))
                    if not item_id:
                        continue
                    data = read_cached_midi(item_id)
                    if data is None:
                        fh = tf.extractfile(member_info)
                        if fh is None:
                            continue
                        data = fh.read()
                        write_cached_midi(item_id, data)
                    cached_files += 1
                    cached_bytes += len(data)

                    if item_id in targets:
                        entry = entry_by_id[item_id]
                        result = classify_midi(
                            data,
                            source=entry.get("source", ""),
                            member=entry.get("member") or entry.get("container", ""),
                        )
                        old = classification_cache.get(item_id, {})
                        classification_cache[item_id] = {
                            "fingerprint": old.get("fingerprint", ""),
                            **result,
                        }
                        entry["kind"] = result["kind"]
                        entry["classificationConfidence"] = result.get("confidence", 0.0)
                        entry["classificationMethod"] = result.get("method", "content")
                        entry["classificationReason"] = result.get("reason", "")
                        entry["classificationRoles"] = result.get("roles", [])
                        entry["classificationPrograms"] = result.get("programs", [])
                        program_counts.update(result.get("programs", []))
                        role_counts.update(result.get("roles", []))
                        reclassified += 1

    # Loose files are already fast to read, but reclassify selected targets too.
    for item_id in targets:
        locator = LIBRARY_LOCATORS.get(item_id)
        if not locator or locator[0] != "file":
            continue
        entry = entry_by_id[item_id]
        data = Path(locator[1]).read_bytes()
        result = classify_midi(
            data,
            source=entry.get("source", ""),
            member=entry.get("container", ""),
        )
        old = classification_cache.get(item_id, {})
        classification_cache[item_id] = {
            "fingerprint": old.get("fingerprint", ""),
            **result,
        }
        entry["kind"] = result["kind"]
        entry["classificationConfidence"] = result.get("confidence", 0.0)
        entry["classificationMethod"] = result.get("method", "content")
        entry["classificationReason"] = result.get("reason", "")
        entry["classificationRoles"] = result.get("roles", [])
        entry["classificationPrograms"] = result.get("programs", [])
        program_counts.update(result.get("programs", []))
        role_counts.update(result.get("roles", []))
        reclassified += 1

    save_classification_cache(classification_cache)
    LIBRARY_ENTRIES.sort(
        key=lambda item: (
            item["genre"],
            item["kind"],
            item["source"],
            item["name"].lower(),
        )
    )

    counts = {
        "total": len(LIBRARY_ENTRIES),
        "genre": dict(Counter(item["genre"] for item in LIBRARY_ENTRIES)),
        "kind": dict(Counter(item["kind"] for item in LIBRARY_ENTRIES)),
    }
    return {
        "ok": True,
        "cachedFiles": cached_files,
        "cachedBytes": cached_bytes,
        "reclassified": reclassified,
        "targetGenre": genre,
        "targetKind": kind,
        "roleCounts": dict(role_counts),
        "programCounts": {str(key): value for key, value in sorted(program_counts.items())},
        "instrumentCounts": {
            f"{key} {GM_PROGRAM_NAMES[key] if key < len(GM_PROGRAM_NAMES) else 'Program '+str(key)}": value
            for key, value in sorted(program_counts.items())
        },
        "counts": counts,
    }



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

    def end_headers(self) -> None:
        # Local UI files change frequently during development; never serve a stale HTML/JS page.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
        if path == "/api/projects":
            try:
                self._send_json(200, list_cloud_projects())
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/project/load":
            try:
                project_id = (parse_qs(parsed.query).get("id") or [""])[0]
                self._send_json(200, load_cloud_project(project_id))
            except FileNotFoundError as exc:
                self._send_json(404, {"ok": False, "error": str(exc)})
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                self._send_json(409, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/status":
            self._send_json(200, library_progress_snapshot())
            return
        if path == "/api/library":
            try:
                self._send_json(200, build_library_catalog())
            except Exception as exc:
                set_library_progress(
                    active=False,
                    stage="error",
                    percent=0,
                    message=f"MIDI library error: {exc}",
                )
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
        if path == "/api/update":
            self._handle_update()
            return
        if path == "/api/project/save":
            try:
                self._send_json(200, save_cloud_project(self._read_json()))
            except (ValueError, GitError, OSError, json.JSONDecodeError) as exc:
                self._send_json(409, {"ok": False, "error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/rescan":
            try:
                # Rescan rebuilds the catalogue but reuses prior classification.
                # Heavy classification/repacking lives in /api/library/repack.
                self._send_json(200, build_library_catalog(force=True))
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/optimize":
            try:
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                genre = (query.get("genre") or ["edm"])[0]
                kind = (query.get("kind") or ["unclassified"])[0]
                self._send_json(200, optimize_library(genre=genre, kind=kind))
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/repack":
            try:
                self._send_json(200, build_style_packs())
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
            return
        if path == "/api/library/report":
            try:
                self._send_json(200, build_library_inventory_report())
            except (ValueError, GitError, OSError, json.JSONDecodeError) as exc:
                self._send_json(409, {"ok": False, "error": str(exc)})
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

    def _handle_update(self) -> None:
        try:
            if has_tracked_worktree_changes():
                raise GitError(
                    "There are uncommitted tracked files. Sync/commit/revert them before Update."
                )

            branch = current_branch()
            if branch != "main":
                raise GitError(
                    f"One-click Update is only allowed on main; current branch is {branch!r}."
                )

            old_full = run_git("rev-parse", "HEAD").stdout.strip()
            old_short = short_sha()
            run_git("fetch", "origin", "main")
            remote_full = run_git("rev-parse", "origin/main").stdout.strip()

            if old_full == remote_full:
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "changed": False,
                        "commit": old_short,
                        "branch": branch,
                        "message": "Already up to date.",
                        "restart": False,
                        "files": [],
                    },
                )
                return

            run_git("pull", "--ff-only", "origin", "main")
            new_full = run_git("rev-parse", "HEAD").stdout.strip()
            new_short = short_sha()
            changed_files = [
                line.strip()
                for line in run_git("diff", "--name-only", old_full, new_full).stdout.splitlines()
                if line.strip()
            ]

            self._send_json(
                200,
                {
                    "ok": True,
                    "changed": old_full != new_full,
                    "oldCommit": old_short,
                    "commit": new_short,
                    "branch": branch,
                    "message": f"Updated {old_short} → {new_short}",
                    "restart": old_full != new_full,
                    "files": changed_files,
                },
            )

            if old_full != new_full:
                # The pulled commit may update this server itself. Shut down cleanly;
                # main() will exec the freshly pulled local_server.py on the same port.
                setattr(self.server, "restart_requested", True)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        except (GitError, OSError) as exc:
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
    if not PACK_INDEX_PATH.exists():
        print("Style Library packs are missing; building optimized ZIP packs once...")
        try:
            report = build_style_packs()
            print(
                f"Style Library packs ready: {report['packs']} ZIP packs, "
                f"{report['total']} MIDI"
            )
        except Exception as exc:
            print(f"Style Library pack build failed; falling back to raw library: {exc}")

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

    restart_requested = False
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        restart_requested = bool(getattr(server, "restart_requested", False))
        server.server_close()

    if restart_requested:
        print("Update pulled. Restarting local bridge on the same port...")
        os.execv(
            sys.executable,
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--port",
                str(args.port),
            ],
        )


if __name__ == "__main__":
    main()
