#!/usr/bin/env python3
"""Compact analyzer for reference-library/raw MIDI corpora. Stdlib only."""

from __future__ import annotations
import argparse, json, statistics, struct, tarfile, zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reference-library" / "raw"
OUT = ROOT / "reference-library" / "analysis"

DRUMS = {
    "kick": {35, 36},
    "snare_clap": {37, 38, 39, 40},
    "closed_hat": {42, 44},
    "open_hat": {46},
    "toms": {41, 43, 45, 47, 48, 50},
    "cymbals": {49, 51, 52, 53, 55, 57, 59},
}

def u16(b, i): return struct.unpack_from(">H", b, i)[0]
def u32(b, i): return struct.unpack_from(">I", b, i)[0]

def vlq(b, i):
    v = 0
    while True:
        x = b[i]; i += 1
        v = (v << 7) | (x & 127)
        if not x & 128:
            return v, i

def parse_midi(b):
    if b[:4] != b"MThd":
        raise ValueError("not SMF")
    fmt, ntrks, ppq = u16(b, 8), u16(b, 10), u16(b, 12)
    if ppq & 0x8000:
        raise ValueError("SMPTE division unsupported")
    pos = 8 + u32(b, 4)
    notes, tempos, sigs, end_tick = [], [], [], 0

    for _ in range(ntrks):
        if b[pos:pos+4] != b"MTrk":
            raise ValueError("missing MTrk")
        end = pos + 8 + u32(b, pos + 4)
        i, tick, run = pos + 8, 0, None
        active = defaultdict(list)

        while i < end:
            d, i = vlq(b, i); tick += d; end_tick = max(end_tick, tick)
            st = b[i]
            if st < 0x80:
                if run is None: raise ValueError("bad running status")
                st = run
            else:
                i += 1
                if st < 0xF0: run = st

            if st == 0xFF:
                typ = b[i]; i += 1
                n, i = vlq(b, i); p = b[i:i+n]; i += n; run = None
                if typ == 0x51 and len(p) == 3:
                    us = int.from_bytes(p, "big")
                    if us: tempos.append((tick, 60_000_000 / us))
                elif typ == 0x58 and len(p) >= 2:
                    sigs.append((tick, p[0], 2 ** p[1]))
                continue
            if st in (0xF0, 0xF7):
                n, i = vlq(b, i); i += n; run = None; continue

            kind, ch = st & 0xF0, st & 15
            if kind in (0x80, 0x90):
                note, vel = b[i], b[i+1]; i += 2
                key = (ch, note)
                if kind == 0x90 and vel:
                    active[key].append((tick, vel))
                elif active[key]:
                    start, v = active[key].pop(0)
                    notes.append((start, tick-start, note, v, ch))
            elif kind in (0xA0, 0xB0, 0xE0): i += 2
            elif kind in (0xC0, 0xD0): i += 1
            else: raise ValueError(f"status {st:02x}")
        pos = end
    return fmt, ppq, notes, tempos, sigs, end_tick

def group(note):
    for name, ns in DRUMS.items():
        if note in ns: return name
    return "other_percussion"

def describe(source, name, data):
    fmt, ppq, notes, tempos, sigs, end_tick = parse_midi(data)
    ts = sigs[0][1:] if sigs else (4, 4)
    bar_ticks = ppq * 4 if ts == (4, 4) else None
    bars = end_tick / bar_ticks if bar_ticks else None
    pitch_mode = Counter(n[2] for n in notes).most_common(1)
    pitch_mode = pitch_mode[0][0] if pitch_mode else None
    onset = [0] * 16
    intervals, drum_groups = Counter(), Counter()
    drum_onset = defaultdict(lambda: [0] * 16)
    velocities = []

    for tick, dur, note, vel, ch in notes:
        step = round((tick % (ppq*4)) / (ppq/4)) % 16
        onset[step] += 1; velocities.append(vel)
        if pitch_mode is not None: intervals[note-pitch_mode] += 1
        if source == "groove" or ch == 9:
            g = group(note); drum_groups[g] += 1; drum_onset[g][step] += 1

    return {
        "source": source, "path": name, "format": fmt, "ppq": ppq,
        "tempo_bpm": round(tempos[0][1], 3) if tempos else None,
        "time_signature": list(ts), "note_count": len(notes),
        "bars_estimate": round(bars, 3) if bars is not None else None,
        "notes_per_bar": round(len(notes)/bars, 3) if bars else None,
        "velocity_min": min(velocities) if velocities else None,
        "velocity_max": max(velocities) if velocities else None,
        "velocity_mean": round(statistics.fmean(velocities), 3) if velocities else None,
        "pitch_mode": pitch_mode, "onset_16": onset,
        "intervals_from_mode": dict(sorted(intervals.items())),
        "drum_groups": dict(sorted(drum_groups.items())),
        "drum_onset_16": dict(sorted(drum_onset.items())),
    }

def acidvoice():
    for p in sorted((RAW/"acidvoice").glob("*.mid")):
        yield p.name, p.read_bytes()

def zipped():
    p = RAW/"groove"/"groove-v1.0.0-midionly.zip"
    with zipfile.ZipFile(p) as z:
        for x in z.infolist():
            if not x.is_dir() and x.filename.lower().endswith((".mid", ".midi")):
                yield x.filename, z.read(x)

def tarred():
    p = RAW/"nrgcp"/"nrgcp_midi_dataset.tar.gz"
    with tarfile.open(p, "r:*") as t:
        for x in t:
            if x.isfile() and x.name.lower().endswith((".mid", ".midi")):
                f = t.extractfile(x)
                if f: yield x.name, f.read()

def stats(vals):
    vals = [x for x in vals if x is not None]
    if not vals: return None
    return {"min": min(vals), "median": statistics.median(vals),
            "mean": round(statistics.fmean(vals), 3), "max": max(vals)}

def aggregate(records):
    onset = [0]*16; intervals = Counter(); drums = Counter()
    drum_onset = defaultdict(lambda:[0]*16)
    for r in records:
        for i,x in enumerate(r["onset_16"]): onset[i] += x
        intervals.update({int(k):v for k,v in r["intervals_from_mode"].items()})
        drums.update(r["drum_groups"])
        for g, xs in r["drum_onset_16"].items():
            for i,x in enumerate(xs): drum_onset[g][i] += x
    return {
        "files": len(records), "notes": sum(r["note_count"] for r in records),
        "tempo_bpm": stats([r["tempo_bpm"] for r in records]),
        "notes_per_bar": stats([r["notes_per_bar"] for r in records]),
        "file_mean_velocity": stats([r["velocity_mean"] for r in records]),
        "onset_16": onset, "intervals_from_mode": dict(sorted(intervals.items())),
        "drum_groups": dict(sorted(drums.items())),
        "drum_onset_16": dict(sorted(drum_onset.items())),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["all","acidvoice","groove","nrgcp"], default="all")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--details", action="store_true")
    a = ap.parse_args()
    factories = {"acidvoice": acidvoice, "groove": zipped, "nrgcp": tarred}
    chosen = list(factories) if a.source == "all" else [a.source]
    report = {"schema": 1, "step_grid": "1/16 within 4/4 bar", "sources": {}}
    detail_rows = []
    OUT.mkdir(parents=True, exist_ok=True)

    for src in chosen:
        rows, errors = [], []
        for i, (name, data) in enumerate(factories[src]()):
            if a.limit is not None and i >= a.limit: break
            try: rows.append(describe(src, name, data))
            except Exception as e: errors.append({"path": name, "error": f"{type(e).__name__}: {e}"})
        report["sources"][src] = aggregate(rows)
        report["sources"][src]["errors"] = errors
        if src == "acidvoice": report["sources"][src]["patterns"] = rows
        detail_rows += rows

    (OUT/"summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if a.details:
        with (OUT/"files.jsonl").open("w", encoding="utf-8") as f:
            for r in detail_rows: f.write(json.dumps(r, ensure_ascii=False)+"\n")
    print(OUT/"summary.json")

if __name__ == "__main__":
    main()
