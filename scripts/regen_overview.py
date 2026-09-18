#!/usr/bin/env python3
"""Regenerate projects/overview.md + overview.json ASCII from current.json (1/32 grid)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "projects" / "current.json"
OUT_MD = ROOT / "projects" / "overview.md"
OUT_JSON = ROOT / "projects" / "overview.json"

NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
GM_TRACK_RE = re.compile(r"^(\d{1,3})\s+")


def gm_program_from_name(name: str) -> int | None:
    m = GM_TRACK_RE.match(name or "")
    if not m:
        return None
    program = int(m.group(1))
    return program if 0 <= program <= 127 else None


def midi_to_name(m: int) -> str:
    return NOTE[m % 12] + str(m // 12 - 1)


def main() -> None:
    p = json.loads(CURRENT.read_text(encoding="utf-8"))
    ppq = p.get("ppq", 480)
    tpb = ppq * 4
    total_bars = max(1, round(p.get("lengthTicks", tpb) / tpb))
    slots = 32
    slot_ticks = ppq / 8
    snap = slot_ticks * 0.5

    markers = sorted(
        [
            {"tick": m["tick"], "bar": m["tick"] // tpb + 1, "text": m["text"]}
            for m in p.get("markers", [])
        ],
        key=lambda x: x["tick"],
    )
    sections: list[dict] = []
    if markers:
        for i, m in enumerate(markers):
            start = m["bar"]
            end = (markers[i + 1]["bar"] - 1) if i + 1 < len(markers) else total_bars
            sections.append({"name": m["text"], "startBar": start, "endBar": max(start, end)})
    else:
        sections = [{"name": "All", "startBar": 1, "endBar": total_bars}]

    def bar_start(bar: int) -> int:
        return (bar - 1) * tpb

    def note_slot(tick: int, bar: int) -> tuple[int, bool]:
        local = tick - bar_start(bar)
        nearest = round(local / slot_ticks)
        slot = max(0, min(slots - 1, nearest))
        err = abs(local - nearest * slot_ticks)
        return slot, err <= snap

    def compress(bars: list[int]) -> str:
        if not bars:
            return ""
        bars = sorted(bars)
        parts: list[str] = []
        lo = hi = bars[0]
        for b in bars[1:]:
            if b == hi + 1:
                hi = b
            else:
                parts.append(f"{lo}" if lo == hi else f"{lo}–{hi}")
                lo = hi = b
        parts.append(f"{lo}" if lo == hi else f"{lo}–{hi}")
        return ", ".join(parts)

    def fingerprint(notes: list, bar: int):
        cells: list[list] = [[] for _ in range(slots)]
        hard = 0
        for n in notes:
            slot, on = note_slot(n["tick"], bar)
            if not on:
                hard += 1
            cells[slot].append(n)
        ascii_s = ""
        pitches: list[str] = []
        for hits in cells:
            if not hits:
                ascii_s += "."
                continue
            mv = max(h["velocity"] for h in hits)
            if len(hits) > 1:
                ascii_s += "*"
            elif mv >= 110:
                ascii_s += "X"
            elif mv <= 55:
                ascii_s += "o"
            else:
                ascii_s += "x"
            pitches.append(midi_to_name(hits[0]["note"]))
        grouped = "|".join(ascii_s[i : i + 8] for i in range(0, slots, 8))
        return grouped, ascii_s, pitches, hard

    def analyze_track(track: dict, start: int, end: int):
        notes = [
            n
            for n in track.get("notes", [])
            if bar_start(start) <= n["tick"] < bar_start(end + 1)
        ]
        if not notes:
            return None
        by = {}
        for bar in range(start, end + 1):
            inb = [n for n in notes if bar_start(bar) <= n["tick"] < bar_start(bar + 1)]
            by[bar] = fingerprint(inb, bar)
        clusters: dict = {}
        hard_total = 0
        for bar, (g, raw, pit, hard) in by.items():
            hard_total += hard
            if raw not in clusters:
                clusters[raw] = {"ascii": g, "bars": [], "hard": 0, "pitches": pit}
            clusters[raw]["bars"].append(bar)
            clusters[raw]["hard"] += hard
            if len(pit) > len(clusters[raw]["pitches"]):
                clusters[raw]["pitches"] = pit
        patterns = sorted(clusters.values(), key=lambda c: -len(c["bars"]))
        two = None
        pairs: dict = {}
        for bar in range(start, end, 2):
            if bar + 1 > end:
                break
            a = by[bar][1]
            b = by[bar + 1][1]
            key = a + "/" + b
            if key not in pairs:
                pairs[key] = {"A": by[bar], "B": by[bar + 1], "starts": []}
            pairs[key]["starts"].append(bar)
        if pairs:
            best = max(pairs.values(), key=lambda x: len(x["starts"]))
            if (len(best["starts"]) >= 2):
                groove = best["A"][0] + best["B"][0]
                if any(ch in groove for ch in "xXo*#"):
                    two = {
                        "asciiA": best["A"][0],
                        "asciiB": best["B"][0],
                        "pitchesA": best["A"][2][:12],
                        "pitchesB": best["B"][2][:12],
                        "repeats": len(best["starts"]),
                        "bars": compress(
                            [s for st in best["starts"] for s in (st, st + 1)]
                        ),
                    }
        return {
            "name": track["name"],
            "channel": track["channel"],
            "noteCount": len(notes),
            "hardOff": hard_total,
            "patterns": patterns[:4],
            "two": two,
        }

    def heatmap(start: int, end: int) -> str:
        slots_acc = [0] * slots
        nbar = 0
        for bar in range(start, end + 1):
            local = [0] * slots
            anyh = False
            a, b = bar_start(bar), bar_start(bar + 1)
            for t in p["tracks"]:
                if t.get("mute"):
                    continue
                for n in t.get("notes", []):
                    if a <= n["tick"] < b:
                        slot, _ = note_slot(n["tick"], bar)
                        local[slot] += 1
                        anyh = True
            if anyh:
                nbar += 1
                for i in range(slots):
                    slots_acc[i] += local[i]
        if not nbar:
            return "........|........|........|........"
        avg = [s / nbar for s in slots_acc]
        mx = max(avg) or 1
        ascii_s = ""
        for v in avg:
            if v == 0:
                ascii_s += "."
            elif v / mx >= 0.85:
                ascii_s += "#"
            elif v / mx >= 0.5:
                ascii_s += "x"
            else:
                ascii_s += "o"
        return "|".join(ascii_s[i : i + 8] for i in range(0, slots, 8))

    lines: list[str] = []
    lines.append(f"# {p.get('name', 'Arrangement')}")
    lines.append("")
    lines.append(f"- Tempo: **{p.get('tempo')}** BPM · PPQ {ppq} · **{total_bars}** bars")
    lines.append("- Hardware: TD-3 USB → DIN → XR20 (ch2 acid, ch1 bass, ch10 drums)")
    lines.append(
        f"- ASCII grid: **1/32** ({slots} slots/bar, snap ±{int(snap)} ticks for humanization)"
    )
    lines.append(
        "- Legend: `.` empty · `x` hit · `X` accent · `o` soft · `*` stack · `#` heatmap peak"
    )
    lines.append("")
    lines.append("## Markers (from Cubase)")
    for m in markers:
        lines.append(f"- Bar {m['bar']}: {m['text']}")
    lines.append("")
    lines.append("## Sections")
    for s in sections:
        lines.append(f"- **{s['name']}** — bars {s['startBar']}–{s['endBar']}")
    lines.append("")
    lines.append("## ASCII patterns (by section, 1/32)")
    lines.append("")

    ascii_sections: list[dict] = []
    for sec in sections:
        lines.append(f"### {sec['name']} (bars {sec['startBar']}–{sec['endBar']})")
        hm = heatmap(sec["startBar"], sec["endBar"])
        lines.append("Heatmap (all tracks, avg density):")
        lines.append("```")
        lines.append(hm)
        lines.append("```")
        tracks_out: list[dict] = []
        for t in p["tracks"]:
            an = analyze_track(t, sec["startBar"], sec["endBar"])
            if not an:
                continue
            tracks_out.append(an)
            hard = f", {an['hardOff']} hard-off-grid" if an["hardOff"] else ""
            lines.append(
                f"**{an['name']}** (ch {an['channel']}, {an['noteCount']} notes{hard})"
            )
            if an["two"]:
                lines.append("2-bar loop (dominant):")
                lines.append("```")
                lines.append("A " + an["two"]["asciiA"])
                lines.append("B " + an["two"]["asciiB"])
                lines.append("```")
                if an["two"]["pitchesA"]:
                    lines.append("- A pitches: " + " ".join(an["two"]["pitchesA"]))
                if an["two"]["pitchesB"]:
                    lines.append("- B pitches: " + " ".join(an["two"]["pitchesB"]))
                lines.append(
                    f"- Covers: {an['two']['bars']} ({an['two']['repeats']}×)"
                )
            for pat in an["patterns"][:3]:
                lines.append(f"- bars {compress(pat['bars'])}:")
                lines.append("```")
                lines.append(pat["ascii"])
                lines.append("```")
                if pat["pitches"]:
                    lines.append("  pitches: " + " ".join(pat["pitches"][:16]))
                if pat["hard"]:
                    lines.append(
                        f"  ({pat['hard']} onsets beyond snap — humanized/32nd-off)"
                    )
            lines.append("")
        ascii_sections.append(
            {
                "name": sec["name"],
                "startBar": sec["startBar"],
                "endBar": sec["endBar"],
                "heatmap32": {"ascii": hm},
                "tracks": tracks_out,
            }
        )

    lines.append("## Tracks")
    for t in p["tracks"]:
        notes = t.get("notes", [])
        if notes:
            mn = min(n["note"] for n in notes)
            mx = max(n["note"] for n in notes)
            rng = f" · {midi_to_name(mn)}–{midi_to_name(mx)}"
        else:
            rng = ""
        gm = gm_program_from_name(t.get("name", ""))
        gm_tag = f" · GM {gm}" if gm is not None else ""
        lines.append(
            f"- **{t['name']}** (id `{t['id']}`, ch {t['channel']}, {t.get('role')}{gm_tag}) "
            f"— {len(notes)} notes{rng}"
        )
    lines.append("")
    lines.append(
        "_Exact ticks/velocity: `projects/current.json`. ASCII is a snapped view for reading groove._"
    )

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    ov = {
        "version": 2,
        "name": p.get("name"),
        "tempo": p.get("tempo"),
        "ppq": ppq,
        "totalBars": total_bars,
        "grid": {
            "resolution": "1/32",
            "slotsPerBar": slots,
            "slotTicks": slot_ticks,
            "snapToleranceTicks": snap,
        },
        "markers": markers,
        "sections": sections,
        "asciiBySection": ascii_sections,
        "forAssistant": (
            "Read overview.md ASCII (1/32, humanize-aware) then current.json for exact ticks."
        ),
    }
    OUT_JSON.write_text(json.dumps(ov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_MD} ({OUT_MD.stat().st_size} bytes)")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
