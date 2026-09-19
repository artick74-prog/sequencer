#!/usr/bin/env python3
"""Content-aware MIDI role classifier for Style Library. Stdlib only."""

from __future__ import annotations

import statistics
import struct
from collections import Counter, defaultdict

GM_FAMILY_NAMES = (
    "piano",
    "chromatic-percussion",
    "organ",
    "guitar",
    "bass",
    "strings",
    "ensemble",
    "brass",
    "reed",
    "pipe",
    "synth-lead",
    "synth-pad",
    "synth-effects",
    "ethnic",
    "percussive",
    "sound-effects",
)


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def _vlq(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated VLQ")
        byte = data[offset]
        offset += 1
        value = (value << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            return value, offset


def parse_midi(data: bytes) -> dict:
    if len(data) < 14 or data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI File")

    ppq = _u16(data, 12)
    if ppq & 0x8000:
        raise ValueError("SMPTE time division is unsupported")

    pos = 8 + _u32(data, 4)
    tracks = _u16(data, 10)
    notes: list[tuple[int, int, int, int, int]] = []
    programs_by_channel: defaultdict[int, set[int]] = defaultdict(set)

    for _ in range(tracks):
        if pos + 8 > len(data) or data[pos:pos + 4] != b"MTrk":
            raise ValueError("missing MTrk")
        track_end = pos + 8 + _u32(data, pos + 4)
        if track_end > len(data):
            raise ValueError("truncated MTrk")

        i = pos + 8
        tick = 0
        running_status: int | None = None
        active: defaultdict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)

        while i < track_end:
            delta, i = _vlq(data, i)
            tick += delta
            if i >= track_end:
                break

            status = data[i]
            if status < 0x80:
                if running_status is None:
                    raise ValueError("bad running status")
                status = running_status
            else:
                i += 1
                if status < 0xF0:
                    running_status = status

            if status == 0xFF:
                if i >= track_end:
                    raise ValueError("truncated meta event")
                i += 1
                length, i = _vlq(data, i)
                i += length
                running_status = None
                continue

            if status in (0xF0, 0xF7):
                length, i = _vlq(data, i)
                i += length
                running_status = None
                continue

            kind = status & 0xF0
            channel = status & 0x0F

            if kind in (0x80, 0x90):
                if i + 2 > track_end:
                    raise ValueError("truncated note event")
                pitch, velocity = data[i], data[i + 1]
                i += 2
                key = (channel, pitch)
                if kind == 0x90 and velocity:
                    active[key].append((tick, velocity))
                elif active[key]:
                    start, start_velocity = active[key].pop(0)
                    notes.append((start, max(1, tick - start), pitch, start_velocity, channel))
            elif kind == 0xC0:
                if i >= track_end:
                    raise ValueError("truncated program change")
                programs_by_channel[channel].add(data[i])
                i += 1
            elif kind in (0xA0, 0xB0, 0xE0):
                i += 2
            elif kind == 0xD0:
                i += 1
            else:
                raise ValueError(f"unsupported MIDI status {status:02x}")

        pos = track_end

    return {
        "ppq": ppq,
        "notes": notes,
        "programsByChannel": {
            channel: sorted(programs)
            for channel, programs in programs_by_channel.items()
        },
    }


def name_kind(source: str, member: str) -> tuple[str | None, float, str]:
    text = f" {source} {member} ".lower().replace("_", " ").replace("-", " ")
    checks = (
        ("bass", ("bassline", "bass line", " bass ", "/bass", "\\bass", "sub bass"), 0.99),
        ("drums", ("drum", "kick", "snare", "clap", "hihat", "hi hat", "hat ", "perc"), 0.99),
        ("acid", ("acid", "303"), 0.99),
        ("chords", ("chord", "pad ", "stabs", "stab "), 0.97),
        ("melody", ("melody", "lead", "synth", "arp", "riff"), 0.94),
    )
    for kind, tokens, confidence in checks:
        if any(token in text for token in tokens):
            return kind, confidence, "name/path"
    return None, 0.0, ""


def _polyphony_features(notes: list[tuple[int, int, int, int, int]]) -> tuple[float, int]:
    if not notes:
        return 0.0, 0

    onset_counts = Counter(start for start, _, _, _, _ in notes)
    chord_onsets = sum(1 for count in onset_counts.values() if count >= 2)
    chord_ratio = chord_onsets / max(1, len(onset_counts))

    events: list[tuple[int, int]] = []
    for start, duration, *_ in notes:
        events.append((start, 1))
        events.append((start + max(1, duration), -1))
    events.sort(key=lambda event: (event[0], event[1]))

    active = 0
    max_polyphony = 0
    for _, delta in events:
        active += delta
        max_polyphony = max(max_polyphony, active)

    return chord_ratio, max_polyphony


def _family(program: int) -> str:
    return GM_FAMILY_NAMES[max(0, min(15, int(program) // 8))]


def _channel_role(
    notes: list[tuple[int, int, int, int, int]],
    programs: list[int],
) -> tuple[str, float, str]:
    pitches = [note[2] for note in notes]
    median_pitch = float(statistics.median(pitches))
    pitch_span = max(pitches) - min(pitches)
    chord_ratio, max_polyphony = _polyphony_features(notes)
    families = {_family(program) for program in programs}

    if "bass" in families:
        return "bass", 0.97, f"GM bass family; median pitch {median_pitch:.1f}"

    chord_families = {
        "piano", "organ", "guitar", "strings", "ensemble", "synth-pad"
    }
    melody_families = {
        "brass", "reed", "pipe", "synth-lead", "ethnic"
    }

    if (families & chord_families) and (
        chord_ratio >= 0.18 or max_polyphony >= 3
    ):
        return (
            "chords",
            min(0.96, 0.80 + chord_ratio * 0.25),
            f"{','.join(sorted(families))}; polyphonic onsets {chord_ratio:.0%}",
        )

    if families & melody_families and max_polyphony <= 2:
        return (
            "melody",
            0.92,
            f"{','.join(sorted(families))}; mostly monophonic",
        )

    if chord_ratio >= 0.42 or (max_polyphony >= 3 and chord_ratio >= 0.22):
        confidence = min(0.95, 0.70 + chord_ratio * 0.45 + min(max_polyphony, 6) * 0.02)
        return (
            "chords",
            confidence,
            f"polyphonic onsets {chord_ratio:.0%}, max polyphony {max_polyphony}",
        )

    if median_pitch <= 50 and max_polyphony <= 2 and chord_ratio < 0.18:
        confidence = 0.82
        if median_pitch <= 45:
            confidence += 0.08
        if pitch_span <= 24:
            confidence += 0.04
        return (
            "bass",
            min(0.96, confidence),
            f"low monophonic line, median pitch {median_pitch:.1f}",
        )

    if max_polyphony <= 2 and chord_ratio < 0.20:
        confidence = 0.78 + (0.08 if median_pitch >= 55 else 0.0)
        return (
            "melody",
            min(0.92, confidence),
            f"mostly monophonic pitched line, median pitch {median_pitch:.1f}",
        )

    return (
        "unclassified",
        0.45,
        (
            f"ambiguous channel: median {median_pitch:.1f}, "
            f"polyphonic onsets {chord_ratio:.0%}, max polyphony {max_polyphony}"
        ),
    )


def classify_midi(data: bytes, source: str = "", member: str = "") -> dict:
    """Classify MIDI into drums/bass/chords/melody/acid/arrangement/unclassified."""
    hinted_kind, hinted_confidence, hinted_method = name_kind(source, member)

    try:
        parsed = parse_midi(data)
    except Exception as exc:
        if hinted_kind is not None:
            return {
                "kind": hinted_kind,
                "confidence": hinted_confidence,
                "method": hinted_method,
                "reason": f"explicit {hinted_kind} token in name/path",
                "roles": [hinted_kind],
                "programs": [],
            }
        return {
            "kind": "unclassified",
            "confidence": 0.0,
            "method": "content",
            "reason": f"parse error: {type(exc).__name__}",
            "roles": [],
            "programs": [],
        }

    notes = parsed["notes"]
    programs_by_channel = parsed["programsByChannel"]
    all_programs = sorted({
        program
        for programs in programs_by_channel.values()
        for program in programs
    })

    if not notes:
        return {
            "kind": hinted_kind or "unclassified",
            "confidence": hinted_confidence if hinted_kind else 0.0,
            "method": hinted_method or "content",
            "reason": (
                f"explicit {hinted_kind} token in name/path"
                if hinted_kind
                else "no complete note events"
            ),
            "roles": [hinted_kind] if hinted_kind else [],
            "programs": all_programs,
        }

    total = len(notes)
    drum_notes = [note for note in notes if note[4] == 9]
    melodic_notes = [note for note in notes if note[4] != 9]
    drum_ratio = len(drum_notes) / total

    notes_by_channel: defaultdict[int, list[tuple[int, int, int, int, int]]] = defaultdict(list)
    for note in melodic_notes:
        notes_by_channel[note[4]].append(note)

    role_rows = []
    for channel, channel_notes in sorted(notes_by_channel.items()):
        programs = programs_by_channel.get(channel, [])
        role, confidence, reason = _channel_role(channel_notes, programs)
        role_rows.append((channel, role, confidence, reason))

    roles = sorted({row[1] for row in role_rows if row[1] != "unclassified"})
    if drum_ratio >= 0.20:
        roles = sorted(set(roles) | {"drums"})

    if hinted_kind is not None and hinted_kind != "acid":
        roles = sorted(set(roles) | {hinted_kind})

    if hinted_kind == "acid":
        return {
            "kind": "acid",
            "confidence": hinted_confidence,
            "method": hinted_method,
            "reason": "explicit acid/303 token in name/path",
            "roles": sorted(set(roles) | {"acid"}),
            "programs": all_programs,
        }

    if drum_ratio >= 0.80 and not melodic_notes:
        return {
            "kind": "drums",
            "confidence": 0.99,
            "method": "content",
            "reason": "all notes are on GM drum channel 10",
            "roles": ["drums"],
            "programs": all_programs,
        }

    if drum_ratio >= 0.80 and len(roles) <= 1:
        return {
            "kind": "drums",
            "confidence": round(min(0.99, 0.90 + drum_ratio * 0.09), 3),
            "method": "content",
            "reason": f"{drum_ratio:.0%} of notes are on GM drum channel 10",
            "roles": ["drums"],
            "programs": all_programs,
        }

    pitched_roles = [role for role in roles if role != "drums"]
    if len(set(pitched_roles)) >= 2 or (
        len(notes_by_channel) >= 2 and len(roles) >= 2
    ):
        details = ", ".join(
            f"ch{channel + 1}:{role}"
            for channel, role, _, _ in role_rows
            if role != "unclassified"
        )
        return {
            "kind": "arrangement",
            "confidence": 0.90,
            "method": "content+program",
            "reason": f"multiple musical roles ({details})",
            "roles": roles,
            "programs": all_programs,
        }

    if hinted_kind is not None:
        return {
            "kind": hinted_kind,
            "confidence": hinted_confidence,
            "method": hinted_method,
            "reason": f"explicit {hinted_kind} token in name/path",
            "roles": roles or [hinted_kind],
            "programs": all_programs,
        }

    if len(pitched_roles) == 1:
        role = pitched_roles[0]
        confidences = [row[2] for row in role_rows if row[1] == role]
        reasons = [row[3] for row in role_rows if row[1] == role]
        return {
            "kind": role,
            "confidence": round(statistics.fmean(confidences), 3) if confidences else 0.8,
            "method": "content+program",
            "reason": "; ".join(reasons[:3]),
            "roles": roles,
            "programs": all_programs,
        }

    if roles == ["drums"]:
        return {
            "kind": "drums",
            "confidence": 0.9,
            "method": "content",
            "reason": f"drum channel present ({drum_ratio:.0%} of notes)",
            "roles": roles,
            "programs": all_programs,
        }

    return {
        "kind": "unclassified",
        "confidence": 0.45,
        "method": "content+program",
        "reason": (
            f"ambiguous material across {len(notes_by_channel)} melodic channel(s); "
            f"GM programs {all_programs or 'not encoded'}"
        ),
        "roles": roles,
        "programs": all_programs,
    }
