#!/usr/bin/env python3
"""Content-based MIDI role classifier for Style Library. Stdlib only."""

from __future__ import annotations

import statistics
import struct
from collections import Counter, defaultdict


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


def parse_midi_notes(data: bytes) -> tuple[int, list[tuple[int, int, int, int, int]]]:
    """Return (PPQ, notes) where notes are (tick, duration, pitch, velocity, channel)."""
    if len(data) < 14 or data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI File")

    ppq = _u16(data, 12)
    if ppq & 0x8000:
        raise ValueError("SMPTE time division is unsupported")

    pos = 8 + _u32(data, 4)
    tracks = _u16(data, 10)
    notes: list[tuple[int, int, int, int, int]] = []

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
                i += 1  # meta type
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
            elif kind in (0xA0, 0xB0, 0xE0):
                i += 2
            elif kind in (0xC0, 0xD0):
                i += 1
            else:
                raise ValueError(f"unsupported MIDI status {status:02x}")

        pos = track_end

    return ppq, notes


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


def classify_midi(data: bytes, source: str = "", member: str = "") -> dict:
    """Classify one MIDI as drums/bass/chords/melody/acid/unclassified."""
    hinted_kind, hinted_confidence, hinted_method = name_kind(source, member)
    if hinted_kind is not None:
        return {
            "kind": hinted_kind,
            "confidence": hinted_confidence,
            "method": hinted_method,
            "reason": f"explicit {hinted_kind} token in name/path",
        }

    try:
        ppq, notes = parse_midi_notes(data)
    except Exception as exc:
        return {
            "kind": "unclassified",
            "confidence": 0.0,
            "method": "content",
            "reason": f"parse error: {type(exc).__name__}",
        }

    if not notes:
        return {
            "kind": "unclassified",
            "confidence": 0.0,
            "method": "content",
            "reason": "no complete note events",
        }

    total = len(notes)
    drum_notes = [note for note in notes if note[4] == 9]
    melodic_notes = [note for note in notes if note[4] != 9]
    drum_ratio = len(drum_notes) / total

    channel_counts = Counter(note[4] for note in melodic_notes)
    dominant_channel_ratio = (
        channel_counts.most_common(1)[0][1] / len(melodic_notes)
        if melodic_notes
        else 0.0
    )

    if drum_ratio >= 0.80:
        return {
            "kind": "drums",
            "confidence": round(min(0.99, 0.90 + drum_ratio * 0.09), 3),
            "method": "content",
            "reason": f"{drum_ratio:.0%} of notes are on GM drum channel 10",
        }

    if not melodic_notes:
        return {
            "kind": "drums",
            "confidence": 0.99,
            "method": "content",
            "reason": "all notes are on GM drum channel 10",
        }

    # Mixed multichannel arrangements are deliberately left unresolved unless
    # one melodic channel clearly dominates. This avoids inventing a role for
    # whole-song MIDI files.
    if len(channel_counts) > 1 and dominant_channel_ratio < 0.72:
        return {
            "kind": "unclassified",
            "confidence": round(dominant_channel_ratio, 3),
            "method": "content",
            "reason": f"mixed arrangement across {len(channel_counts)} melodic channels",
        }

    pitches = [note[2] for note in melodic_notes]
    median_pitch = float(statistics.median(pitches))
    pitch_span = max(pitches) - min(pitches)
    chord_ratio, max_polyphony = _polyphony_features(melodic_notes)

    if chord_ratio >= 0.42 or (max_polyphony >= 3 and chord_ratio >= 0.22):
        confidence = min(0.97, 0.70 + chord_ratio * 0.45 + min(max_polyphony, 6) * 0.02)
        return {
            "kind": "chords",
            "confidence": round(confidence, 3),
            "method": "content",
            "reason": (
                f"polyphonic onsets {chord_ratio:.0%}, max polyphony {max_polyphony}, "
                f"median pitch {median_pitch:.1f}"
            ),
        }

    if median_pitch <= 50 and max_polyphony <= 2 and chord_ratio < 0.18:
        confidence = 0.82
        if median_pitch <= 45:
            confidence += 0.08
        if pitch_span <= 24:
            confidence += 0.04
        return {
            "kind": "bass",
            "confidence": round(min(0.96, confidence), 3),
            "method": "content",
            "reason": (
                f"low mostly-monophonic line, median pitch {median_pitch:.1f}, "
                f"max polyphony {max_polyphony}"
            ),
        }

    if max_polyphony <= 2 and chord_ratio < 0.20:
        confidence = 0.78
        if median_pitch >= 55:
            confidence += 0.08
        if dominant_channel_ratio >= 0.90:
            confidence += 0.04
        return {
            "kind": "melody",
            "confidence": round(min(0.94, confidence), 3),
            "method": "content",
            "reason": (
                f"mostly-monophonic pitched line, median pitch {median_pitch:.1f}, "
                f"max polyphony {max_polyphony}"
            ),
        }

    return {
        "kind": "unclassified",
        "confidence": 0.45,
        "method": "content",
        "reason": (
            f"ambiguous pitched material: median {median_pitch:.1f}, "
            f"polyphonic onsets {chord_ratio:.0%}, max polyphony {max_polyphony}"
        ),
    }
