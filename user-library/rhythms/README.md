# Rhythm Library

Pitch-free rhythmic cells for the MIDI Host Rhythm Browser.

Each pattern stores:
- `bars` and `stepsPerBar` (abstract grid; independent of MIDI PPQ);
- event `pos`, `dur`, and `vel`;
- category/family/tags/worksFor metadata.

The browser converts these cells into temporary audition notes on a selected target track.
Audition does not edit the project until **Apply to track** is pressed.

Global MIDI Host Swing remains a separate groove layer. The Rhythm Browser's Gate control scales the pattern's stored durations without changing its onset positions.
