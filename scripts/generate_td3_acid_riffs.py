#!/usr/bin/env python3
"""Generate one MIDI file with ~20 acid bass phrases for Behringer TD-3 / TB-303."""

from __future__ import annotations

import struct
from pathlib import Path

# TD-3 / 303: monophonic acid bass, channel 0, dub tempo
BPM = 120
PPQ = 480  # ticks per quarter note
CHANNEL = 0
PHRASE_BARS = 2  # every slot: 2 bars of music
GAP_BARS = 2     # then 2 bars of silence (for drum loops)
ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output" / "td3_acid_riffs_20.mid"

# MIDI note numbers (bass register, classic acid keys)
E1, F1, Fs1, G1, Gs1, A1, As1, B1 = 28, 29, 30, 31, 32, 33, 34, 35
C2, Cs2, D2, Ds2, E2, F2, Fs2, G2, Gs2, A2, As2, B2 = 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47
C3 = 48

REST = None
ACCENT = 115
NORMAL = 88
SOFT = 72
SLIDE = True  # legato overlap for 303 slide feel


def vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("VLQ must be non-negative")
    buffer = [value & 0x7F]
    value >>= 7
    while value:
        buffer.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(buffer)


def meta_event(delta: int, meta_type: int, data: bytes) -> bytes:
    return vlq(delta) + bytes([0xFF, meta_type]) + vlq(len(data)) + data


def note_on(delta: int, note: int, velocity: int) -> bytes:
    return vlq(delta) + bytes([0x90 | CHANNEL, note & 0x7F, velocity & 0x7F])


def note_off(delta: int, note: int, velocity: int = 0) -> bytes:
    return vlq(delta) + bytes([0x80 | CHANNEL, note & 0x7F, velocity & 0x7F])


def ticks(beats: float) -> int:
    return int(round(beats * PPQ))


def sixteenth(n: int) -> int:
    return ticks(n / 4)


def phrase_to_events(
    notes: list[tuple[int | None, int, int, bool]],
    *,
    bar_count: int = 1,
) -> list[tuple[int, bytes]]:
    """
    notes: list of (midi_note|REST, duration_in_16ths, velocity, slide_to_next)
    Returns list of (absolute_tick, event_bytes) without deltas yet.
    """
    events: list[tuple[int, bytes]] = []
    t = 0
    active: int | None = None

    for i, item in enumerate(notes):
        note, dur_16, vel, slide = item
        dur = sixteenth(dur_16)
        next_item = notes[i + 1] if i + 1 < len(notes) else None

        if note is REST:
            if active is not None:
                events.append((t, note_off(0, active)))
                active = None
            t += dur
            continue

        if active is not None and active != note:
            events.append((t, note_off(0, active)))
            active = None

        if active is None:
            events.append((t, note_on(0, note, vel)))
            active = note

        note_end = t + dur
        slides_to_next = (
            slide
            and next_item is not None
            and next_item[0] is not REST
            and next_item[0] != note
        )
        if not slides_to_next:
            events.append((note_end, note_off(0, note)))
            active = None
        t = note_end

    total = ticks(bar_count * 4)
    if t < total:
        if active is not None:
            events.append((t, note_off(0, active)))
    return events


def strip_vlq_prefix(raw: bytes) -> bytes:
    i = 0
    while raw[i] & 0x80:
        i += 1
    return raw[i + 1 :]


def n(note, d, vel=NORMAL, slide=False):
    return (note, d, vel, slide)


def r(d):
    return (REST, d, 0, False)


# 20 distinct acid phrases (source motifs; length normalized in build)
PHRASES: list[tuple[list, int, str]] = [
    (
        [
            n(E1, 1, ACCENT), n(E1, 1), n(G1, 1, NORMAL, SLIDE), n(E1, 1),
            n(E1, 1, ACCENT), n(E1, 1), n(B1, 1, NORMAL, SLIDE), n(E1, 1),
            n(E1, 1, ACCENT), n(E1, 1), n(G1, 1, NORMAL, SLIDE), n(E1, 1),
            n(E1, 1, ACCENT), n(E1, 1), n(B1, 1, NORMAL, SLIDE), n(E1, 1),
        ],
        1,
        "Rolling E pump",
    ),
    (
        [
            n(E1, 2, ACCENT), r(2), n(E2, 2, ACCENT), r(2),
            n(E1, 2, ACCENT), r(2), n(E2, 1, ACCENT), n(E1, 1, NORMAL, SLIDE),
        ],
        1,
        "Octave stab",
    ),
    (
        [
            n(A1, 1, ACCENT), r(1), n(A1, 1), n(C2, 1, NORMAL, SLIDE), r(1),
            n(A1, 1, ACCENT), n(G1, 1), n(A1, 1), n(E1, 1, NORMAL, SLIDE),
            n(A1, 1), r(1), n(C2, 2), n(A1, 2),
        ],
        2,
        "Syncopated A minor",
    ),
    (
        [
            n(E1, 1, ACCENT), n(F1, 1, NORMAL, SLIDE), n(Fs1, 1, NORMAL, SLIDE),
            n(G1, 1, ACCENT), n(Gs1, 1, NORMAL, SLIDE), n(A1, 1, NORMAL, SLIDE),
            n(As1, 1), n(B1, 1, ACCENT), r(8),
        ],
        1,
        "Chromatic climb",
    ),
    (
        [
            n(G1, 2, ACCENT), n(G1, 1), n(B1, 1, NORMAL, SLIDE),
            n(G1, 2, ACCENT), n(Fs1, 1), n(E1, 1, NORMAL, SLIDE),
            n(G1, 2, ACCENT), n(A1, 1), n(G1, 1),
            n(E1, 2, ACCENT), r(2),
        ],
        1,
        "G triplet squelch",
    ),
    (
        [
            n(D2, 2, ACCENT), n(D2, 2), n(A1, 2, NORMAL, SLIDE), n(A1, 2),
            n(D2, 2, ACCENT), r(2), n(Fs1, 2), n(G1, 2, NORMAL, SLIDE),
            n(A1, 2, ACCENT), n(G1, 2), n(Fs1, 2), n(E1, 2),
        ],
        2,
        "Call and response D",
    ),
    (
        [
            r(4), n(E1, 1, ACCENT), n(E1, 1), n(G1, 1, NORMAL, SLIDE), r(1),
            n(E1, 1, ACCENT), r(2), n(B1, 1), n(E1, 1, NORMAL, SLIDE),
            r(4), n(E1, 2, ACCENT), r(2),
        ],
        1,
        "Empty pocket E",
    ),
    (
        [
            n(Fs1, 1, ACCENT), n(Fs1, 1), n(A1, 1, NORMAL, SLIDE), n(Fs1, 1),
            n(Fs1, 1, ACCENT), n(Cs2, 1), n(B1, 1, NORMAL, SLIDE), n(A1, 1),
            n(Fs1, 2, ACCENT), n(Fs1, 2), n(E1, 2), n(Fs1, 2),
        ],
        1,
        "F# machine funk",
    ),
    (
        [
            n(C2, 1, ACCENT), n(B1, 1, NORMAL, SLIDE), n(A1, 1, NORMAL, SLIDE),
            n(G1, 1), n(Fs1, 1, NORMAL, SLIDE), n(E1, 1, ACCENT),
            r(2), n(E1, 1), n(G1, 1, NORMAL, SLIDE), n(B1, 1),
            n(A1, 1), n(G1, 1), n(E1, 2, ACCENT), r(2),
        ],
        2,
        "Descending acid",
    ),
    (
        [
            r(1), n(G1, 1, ACCENT), r(1), n(G1, 1),
            r(1), n(B1, 1, ACCENT), n(G1, 1, NORMAL, SLIDE), r(1),
            r(1), n(G1, 1, ACCENT), r(1), n(D2, 1),
            r(1), n(B1, 1, ACCENT), n(G1, 1), r(1),
        ],
        1,
        "Offbeat hammer G",
    ),
    (
        [
            n(A1, 3, ACCENT), n(A1, 1), n(C2, 3, NORMAL, SLIDE), n(A1, 1),
            n(E1, 3, ACCENT), n(E1, 1), n(A1, 3, NORMAL, SLIDE), n(G1, 1),
        ],
        1,
        "Long gate wobble",
    ),
    (
        [
            n(E1, 1, ACCENT), n(E1, 1), n(E1, 1), n(G1, 1, NORMAL, SLIDE),
            n(E1, 1, ACCENT), r(1), n(E1, 1), n(B1, 1),
            n(E1, 1, ACCENT), n(E1, 1), n(D2, 1), n(B1, 1, NORMAL, SLIDE),
            n(G1, 1), n(E1, 2, ACCENT), r(2),
        ],
        2,
        "Phuture-ish E",
    ),
    (
        [
            n(B1, 2, ACCENT), n(B1, 1), n(D2, 1, NORMAL, SLIDE),
            n(B1, 2, ACCENT), n(A1, 1), n(Fs1, 1, NORMAL, SLIDE),
            n(B1, 2, ACCENT), n(B1, 2), n(Fs1, 2), n(B1, 2),
        ],
        1,
        "B rumble",
    ),
    (
        [
            n(C2, 1, ACCENT), n(C2, 1), n(G1, 1), n(C2, 1),
            n(B1, 1, ACCENT), n(B1, 1), n(G1, 1), n(B1, 1),
            n(A1, 1, ACCENT), n(A1, 1), n(E1, 1), n(A1, 1),
            n(G1, 1, ACCENT), n(G1, 1), n(E1, 1), n(G1, 1),
        ],
        1,
        "Staccato chase",
    ),
    (
        [
            n(E1, 4, ACCENT), r(4), n(G1, 2, NORMAL, SLIDE), r(2),
            n(B1, 2, ACCENT), r(2), n(A1, 2, NORMAL, SLIDE), r(2),
            n(G1, 4, ACCENT), r(4),
        ],
        2,
        "Sparse tension",
    ),
    (
        [
            n(E1, 1, ACCENT), n(Fs1, 1, NORMAL, SLIDE), n(G1, 1, NORMAL, SLIDE),
            n(A1, 1), n(B1, 1, NORMAL, SLIDE), n(C2, 1, NORMAL, SLIDE),
            n(B1, 1), n(A1, 1, NORMAL, SLIDE), n(G1, 1),
            n(Fs1, 1), n(E1, 1, ACCENT), r(1), n(E1, 1), r(3),
        ],
        1,
        "Double-time fill",
    ),
    (
        [
            n(G1, 2, ACCENT), n(Bb := As1, 2, NORMAL, SLIDE),
            n(G1, 2, ACCENT), n(Bb, 2, NORMAL, SLIDE),
            n(G1, 1, ACCENT), n(Bb, 1), n(D2, 2), n(Bb, 2),
            n(G1, 2, ACCENT), r(2),
        ],
        1,
        "Minor third bounce",
    ),
    (
        [
            n(E1, 1, ACCENT), n(E2, 1, ACCENT), n(E1, 1), n(G1, 1, NORMAL, SLIDE),
            n(E1, 1, ACCENT), n(E2, 1), n(B1, 1, NORMAL, SLIDE), n(G1, 1),
            n(E1, 2, ACCENT), n(B1, 2), n(E1, 2), n(E2, 2, ACCENT),
        ],
        1,
        "Hoover octave hop",
    ),
    (
        [
            n(D1 := 26, 1, ACCENT), n(D1, 1), n(F1, 1, NORMAL, SLIDE), n(D1, 1),
            n(D1, 1, ACCENT), n(A1, 1), n(D2, 1, NORMAL, SLIDE), r(1),
            n(D1, 1, ACCENT), n(C2, 1), n(B1, 1, NORMAL, SLIDE), n(A1, 1),
            n(G1, 1), n(Fs1, 1, NORMAL, SLIDE), n(D1, 2, ACCENT), r(2),
        ],
        2,
        "Dark D pedal",
    ),
    (
        [
            n(A1, 1, ACCENT), n(A1, 1), n(C2, 1, NORMAL, SLIDE), n(A1, 1),
            n(G1, 1, ACCENT), n(Fs1, 1, NORMAL, SLIDE), n(E1, 1, NORMAL, SLIDE),
            n(D1, 1), n(E1, 1, ACCENT), n(Fs1, 1, NORMAL, SLIDE),
            n(G1, 1, NORMAL, SLIDE), n(A1, 1, ACCENT), n(B1, 1),
            n(C2, 2, ACCENT), r(2),
        ],
        2,
        "Closing squelch run",
    ),
]


def normalize_to_two_bars(notes: list) -> list:
    """Loop the actual musical material until it fills exactly two bars."""
    target_steps = PHRASE_BARS * 16
    if not notes:
        raise ValueError("A phrase cannot be empty")

    normalized = []
    steps = 0
    source_index = 0
    while steps < target_steps:
        note, dur, vel, slide = notes[source_index % len(notes)]
        remaining = target_steps - steps
        use_dur = min(dur, remaining)

        is_cycle_end = (source_index + 1) % len(notes) == 0
        normalized.append((note, use_dur, vel, slide and not is_cycle_end and use_dur == dur))
        steps += use_dur
        source_index += 1

    return normalized


def build_midi(phrases_data: list[tuple[list, int, str]]) -> bytes:
    all_events: list[tuple[int, int, bytes]] = []
    slot_beats = (PHRASE_BARS + GAP_BARS) * 4
    cursor = 0

    for idx, (notes, _bars, name) in enumerate(phrases_data, 1):
        norm_notes = normalize_to_two_bars(notes)
        pe = phrase_to_events(norm_notes, bar_count=PHRASE_BARS)
        base = cursor

        start_marker = f"{idx:02d} START {name}".encode("latin-1", errors="replace")
        end_marker = f"{idx:02d} END".encode("latin-1", errors="replace")
        all_events.append((base, 0, meta_event(0, 0x06, start_marker)))
        for tick, ev in pe:
            all_events.append((base + tick, 1, ev))
        phrase_end = base + ticks(PHRASE_BARS * 4)
        all_events.append((phrase_end, 0, meta_event(0, 0x06, end_marker)))

        cursor = base + ticks(slot_beats)

    all_events.sort(key=lambda x: (x[0], x[1]))

    track = bytearray()
    track += meta_event(0, 0x03, "TD-3 Acid Riffs x20 [2+2 @120]".encode("latin-1"))
    us_per_quarter = int(60_000_000 / BPM)
    track += meta_event(0, 0x51, struct.pack(">I", us_per_quarter)[1:])
    track += meta_event(0, 0x58, bytes([4, 2, 24, 8]))
    track += meta_event(0, 0x59, bytes([0, 0]))

    prev_tick = 0
    for tick, _prio, raw_ev in all_events:
        delta = tick - prev_tick
        track += vlq(delta) + strip_vlq_prefix(raw_ev)
        prev_tick = tick

    track += meta_event(0, 0x2F, b"")

    header = b"MThd" + struct.pack(">I", 6) + struct.pack(">HHH", 0, 1, PPQ)
    return header + b"MTrk" + struct.pack(">I", len(track)) + track


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = build_midi(PHRASES)
    OUTPUT.write_bytes(data)
    total_bars = len(PHRASES) * (PHRASE_BARS + GAP_BARS)
    print(f"Wrote {OUTPUT}")
    print(
        f"Phrases: {len(PHRASES)}, BPM: {BPM}, "
        f"layout: {PHRASE_BARS} bars play + {GAP_BARS} bars rest, "
        f"total: {total_bars} bars"
    )
    for i, (_notes, bars, name) in enumerate(PHRASES, 1):
        src = f"{bars} bar motif" if bars == 1 else f"{bars} bar motif"
        print(f"  {i:2d}. {name} ({src})")


if __name__ == "__main__":
    main()
