# Rhythm Library

Pitch-free rhythmic cells for the MIDI Host Rhythm Browser.

## Schema

Each pattern stores:
- `bars` and `stepsPerBar` (abstract grid; independent of MIDI PPQ);
- event `pos`, `dur`, and `vel`;
- `bank`, `instrument`, `category`, `family`, `variant`, `tags`, and `worksFor` metadata.

Guitar events may also carry future-facing performance metadata:
- `attack`: `CHORD`, `CHOKE`, `MUTE`, or `SUSTAIN`;
- `stroke`: `DOWN` or `UP`.

The current MIDI Host intentionally ignores `attack` and `stroke` for note generation, so these fields do not change pitch or articulation yet. They are preserved in the library for future guitar voicing/articulation support.

## Banks

The expanded library contains **278 patterns**:
- **Core** — 20 universal rhythmic cells;
- **Guitar** — 144 patterns across Rock, Chug/Metal, Punk/Indie, Funk, Ska/Reggae, Disco/Pop, Blues/Boogie, Latin/Bossa, and Stabs/Syncopation;
- **Bass** — 42 patterns;
- **Acid** — 36 TB-303-oriented rhythmic shapes;
- **Keys** — 36 comping/stab patterns.

Many instrument-bank families include musically related variants such as Base, Tight/Short, Push, Sparse, Busy, Offbeat Shift/Rotate, Backbeat Accent, and 2-bar Turnaround. These are deterministic variations of curated seed rhythms rather than random note generation.

## MIDI Host behavior

The browser converts these cells into temporary audition notes on a selected target track.
Audition does not edit the project until **Apply to track** is pressed.

The **Bank** filter defaults to **Auto for target**:
- TD-3 / acid tracks → Acid;
- XR20 bass / GM Bass → Bass;
- GM Guitar → Guitar;
- GM Piano/Chromatic Percussion/Organ families → Keys;
- unknown pitched tracks → all banks.

The user can always switch Bank to **All banks** or a specific bank manually.

Global MIDI Host Swing remains a separate groove layer. The Rhythm Browser's Gate control scales the pattern's stored durations without changing its onset positions.

## Personal revisions in MIDI Host

Each library card can be edited without changing the built-in source pattern.

- The **✎** button opens a compact onset-grid editor.
- **LIVE preview is always on inside the editor**: opening the editor starts/continues audition, and every add/remove/drag change is heard immediately without waiting for Save. The project backing loop keeps running; only the temporary rhythm overlay is swapped.
- Click a step to add/remove an attack; drag a hit to another step to move it while preserving duration, velocity and articulation metadata.
- **Save as new revision** appends a non-destructive personal revision to that card.
- Cards with revisions expose **‹ / ›** navigation. `O · N` means Original with N saved revisions available; `V3/10` means revision 3 of 10.
- Revision arrows immediately audition the selected Original/revision on the current target track.
- The card's **▣** button saves the currently selected revision as a separate custom rhythm card.
- Personal revisions and custom cards are stored in browser localStorage, so they survive normal page reloads and one-click application updates without modifying `user-library/rhythms/index.json`.

Built-in patterns remain immutable; personal experiments never overwrite the factory rhythm.



## Onset groups and note lengths

The Rhythm Browser now separates **attack placement** from **performance length**.

Patterns in the same bank/family with the same bar/grid and identical onset positions are collapsed into one browser card. Their different stored duration/velocity performances remain available through the card's **Variant ‹ / ›** control, so e.g. `Rock 8ths · Base` and `Rock 8ths · Tight` no longer need separate visible cards.

The underlying library is still lossless: the source patterns remain separate entries in `index.json`; grouping is a browser presentation layer only. Manual V1/V2/... revisions still belong to the currently selected underlying variant.

The editor shows note length visually and supports exact 4/4 musical-duration presets:
- `1/32`
- `1/16`
- `1/8`
- `1/4`
- dotted `1/4`
- `1/2`
- dotted `1/2`
- `1/1`

Stored `dur` is still expressed in abstract pattern-grid steps. For a 16-step 4/4 pattern, these map to `0.5 / 1 / 2 / 4 / 6 / 8 / 12 / 16` steps. On a 12-step triplet grid the editor converts the same musical values proportionally.

The MIDI Host's global **Gate** remains a playback multiplier after the stored duration. Therefore Gate = 100% means the editor's named duration is literal; Gate 50% halves it, Gate 150% extends it.


### Automatic no-overlap trimming

The Rhythm Editor is monophonic in time: edited note lengths are never allowed to run through a later attack.

When a hit is added or moved inside the span of an earlier note, the earlier note is automatically shortened so its end lands exactly on the new attack. Choosing a duration preset that would extend through the next attack is also capped at that next attack. The final note in a pattern is capped at the pattern boundary.

Example on a 16-step 4/4 grid: a stored quarter note is 4 steps. If a new attack is inserted 2 steps later, the quarter is automatically reduced to 2 steps (an eighth note). Removing the later attack does not automatically lengthen the earlier note again; the editor preserves the shortened value unless the user chooses a longer duration.
