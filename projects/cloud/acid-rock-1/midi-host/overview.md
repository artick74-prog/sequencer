# Acid Rock 1

- Tempo: **120** BPM · PPQ 480 · **32** bars
- Hardware: TD-3 USB → DIN → XR20 (ch2 acid, ch1 bass, ch10 drums)
- ASCII grid: **1/32** (32 slots/bar, snap ±30 ticks for humanization)
- Legend: `.` empty · `x` hit · `X` accent · `o` soft · `*` stack · `#` heatmap peak

## Markers (from Cubase)
- Bar 1: Start

## Sections
- **Start** — bars 1–32

## ASCII patterns (by section, 1/32)

### Start (bars 1–32)
Heatmap (all tracks, avg density):
```
x.o.xoo.|#oo.ooo.|xoo.#oo.|xoo.xoxo
```
**Acid** (ch 2, 224 notes)
2-bar loop (dominant):
```
A X.X.X.X.|x.X...X.|x.X.X.X.|..x.x.x.
B X.X.X.X.|x.X...X.|x.X.X.X.|..x.x.x.
```
- A pitches: C3 C3 C2 C2 C3 C1 C3 C3 C2 C1 C3 C3
- B pitches: C3 C3 C2 C2 C3 C1 C3 C3 C2 C1 C3 C3
- Covers: 1–16 (8×)
- bars 1–16:
```
X.X.X.X.|x.X...X.|x.X.X.X.|..x.x.x.
```
  pitches: C3 C3 C2 C2 C3 C1 C3 C3 C2 C1 C3 C3 A#3 C3
- bars 17–32:
```
........|........|........|........
```

**Drums** (ch 10, 207 notes)
- bars 17–32:
```
........|........|........|........
```
- bars 3–4:
```
*...x...|*...x...|X...*...|*....x.o
```
  pitches: C2 F#2 D2 F#2 F#2 C2 D2 F#2 C2
- bars 1:
```
*....x..|.*...x..|.X...*..|.*...x..
```
  pitches: C2 F#2 D2 F#2 F#2 C2 D2 F#2
- bars 2:
```
*...x...|Xx...x..|x...*...|*...x..o
```
  pitches: C2 F#2 D2 F#2 F#2 F#2 C2 D2 F#2 C2

## Tracks
- **Bass** (id `bass`, ch 1, xr20-bass) — 0 notes
- **Acid** (id `acid`, ch 2, td3) — 224 notes · C1–A#3
- **29 Overdriven Guitar** (id `guitar`, ch 3, gm · GM 29) — 0 notes
- **4 Electric Piano 1** (id `keys`, ch 4, gm · GM 4) — 0 notes
- **Drums** (id `drums`, ch 10, xr20-drums) — 207 notes · C2–F#2

## Activity (notes per 8 bars)
- Bars 1-8: total 215 — Acid:112, Drums:103
- Bars 9-16: total 216 — Acid:112, Drums:104
- Bars 17-24: total 0 — (empty)
- Bars 25-32: total 0 — (empty)

_Exact ticks/velocity: `projects/current.json`. ASCII is a snapped view for reading groove._