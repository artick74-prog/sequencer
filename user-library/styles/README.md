# User Style Library

This is the user's reusable arranger-style library, separate from the external MIDI reference library.

## Lifecycle

- `draft` — a useful groove/arrangement seed that may still change.
- `mature` — a stable reusable style.
- Mature styles can later grow arranger sections such as Main A/B/C/D, Fill, Break, Intro and Ending.

## Schema idea

Each style keeps:

- tempo, meter, tags and a default harmony;
- self-contained realized MIDI-note data for quick audition/reload;
- a harmonic pattern model for tonal parts (bar-relative timing + interval from the current/next chord root);
- provenance for source drum loops and source projects.

This lets a bass rhythm survive a harmony change instead of being tied forever to the notes of the original song.

## Current drafts

- **Acid Rock 1** — rock drums + Tresillo Rock bass.
- **Acid Rock 2** — same drum family + Kick Lock Long bass.

Open them from **Style Library → My Styles**.
