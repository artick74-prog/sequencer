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
import re
import shutil
import subprocess
import tarfile
import threading
import webbrowser
import zipfile
from datetime import datetime, timezone
from collections import Counter, defaultdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from midi_classifier import classify_midi

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
ALLOWED_FILES = {"current.json", "overview.json", "overview.md", "chiptune-current.json", "chiptune-overview.md"}
MAX_BODY = 32 * 1024 * 1024
LIBRARY_ROOT = Path(
    os.environ.get("MIDI_REFERENCE_ROOT", str(ROOT.parent / "midi-reference"))
).resolve()
LIBRARY_LOCK = threading.Lock()
LIBRARY_ENTRIES: list[dict] = []
LIBRARY_LOCATORS: dict[str, tuple[str, str, str | None]] = {}
LIBRARY_MODE: str | None = None
CLASSIFICATION_CACHE_VERSION = 2
CLASSIFICATION_CACHE_PATH = LIBRARY_ROOT / ".style-library-classification-v2.json"
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


def slugify_pack_part(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return text or "other"


def catalog_payload(entries: list[dict], mode: str, pack_count: int = 0) -> dict:
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


def load_pack_catalog_locked() -> dict:
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS, LIBRARY_MODE
    payload = json.loads(PACK_INDEX_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not isinstance(payload.get("entries"), list):
        raise ValueError("Unsupported Style Library pack index")

    entries = payload["entries"]
    locators: dict[str, tuple[str, str, str | None]] = {}
    for item in entries:
        pack_rel = item.get("pack")
        pack_member = item.get("packMember")
        item_id = item.get("id")
        if not item_id or not pack_rel or not pack_member:
            raise ValueError("Invalid entry in Style Library pack index")
        locators[item_id] = ("pack", str((PACK_ROOT / pack_rel).resolve()), pack_member)

    LIBRARY_ENTRIES = entries
    LIBRARY_LOCATORS = locators
    LIBRARY_MODE = "packs"
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


def build_library_catalog(force: bool = False, prefer_packs: bool = True) -> dict:
    global LIBRARY_ENTRIES, LIBRARY_LOCATORS, LIBRARY_MODE
    with LIBRARY_LOCK:
        if prefer_packs and PACK_INDEX_PATH.exists():
            if LIBRARY_MODE == "packs" and LIBRARY_ENTRIES and not force:
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

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
