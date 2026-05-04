# 🎵 Web Sequencer - Retro Tracker Style

A modern web-based music sequencer inspired by classic trackers like FastTracker, built with vanilla JavaScript, Web Audio API, and Web MIDI API.

## Features

### Core Functionality
- **Piano Roll Interface**: Visual grid for placing notes (not text-based)
- **3 Monophonic Tracks**: Independent note tracks for polyphonic arrangement
- **16-Step Pattern**: Classic tracker-style 16-step patterns (expandable)
- **Multiple Waveforms**: Square, Triangle, Sawtooth wave generation
- **Tempo Control**: Adjustable BPM (30-300)
- **Real-time Playback**: Step-by-step note triggering with visual feedback

### Audio Features
- **Web Audio API**: Pure JavaScript sound synthesis (no plugins needed)
- **ADSR Envelope**: Attack, Decay, Sustain, Release for realistic sound
- **Volume Control**: Master volume and per-track volume adjustment
- **Multiple Oscillators**: Independent synths for each track

### MIDI Features
- **Web MIDI API Integration**: Send notes to external synthesizers
- **MIDI Device Selection**: Choose from available MIDI output devices
- **MIDI Export**: Export patterns to standard `.mid` files
- **MIDI Import**: Load standard MIDI files (foundation for future)

### User Interface
- **Dark Retro Theme**: FastTracker-inspired visual style with green phosphor aesthetic
- **Responsive Design**: Works on desktop and tablet
- **Keyboard Shortcuts**: Full keyboard control
- **Visual Feedback**: Playing step highlight, active note indication
- **Smooth Animations**: Retro aesthetic with modern smooth interactions

### Architecture
- **Modular Code**: Separated into logical modules (Audio, MIDI, Core, UI)
- **Clean State Management**: Centralized state with event listeners
- **Serializable State**: Save/load patterns as JSON
- **MIDI File Generation**: Full MIDI export capability

## Project Structure

```
sequencer/
├── index.html              # Main HTML page
├── styles.css             # Retro dark theme styles
├── README.md              # This file
└── js/
    ├── main.js            # Application initialization
    ├── core/
    │   ├── State.js       # Central state management
    │   └── Sequencer.js   # Playback logic and orchestration
    ├── audio/
    │   ├── AudioEngine.js # Web Audio API management
    │   └── Synth.js       # Oscillator and sound synthesis
    ├── midi/
    │   ├── MidiOutput.js  # Web MIDI API interface
    │   └── MidiExporter.js # MIDI file generation (.mid)
    └── ui/
        ├── PianoRoll.js   # Canvas-based grid visualization
        └── Controls.js    # Button, slider, and keyboard handlers
```

## Quick Start

1. **Open in Browser**: Simply open `index.html` in a modern web browser
2. **Place Notes**: Click on the grid to place notes, click again to remove
3. **Select Track**: Use Track 1, 2, 3 buttons or press 1-2-3
4. **Play**: Press SPACE or click Play button
5. **Adjust Tempo**: Use the BPM slider (30-300)
6. **Choose Waveform**: Select Square, Triangle, or Sawtooth

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Space** | Play/Stop |
| **Delete** | Clear current step |
| **1-3** | Select Track 1-3 |
| **Arrow Left/Right** | Navigate steps |
| **Arrow Up/Down** | Change note (in current step) |
| **Ctrl+C** | Clear entire track |

## Using MIDI

### Sending to External Synthesizer
1. Select your MIDI device from "MIDI Output" dropdown
2. Place notes on the grid
3. Press Play - notes will be sent to the external synth alongside internal audio

### Exporting Patterns
1. Click "Export MIDI" button
2. A `.mid` file will be downloaded with your pattern
3. Open in any DAW or MIDI player

### MIDI Configuration
- All tracks use MIDI channels 1-3 (Track 1 → Channel 1, etc.)
- Notes are mapped to MIDI notes 60-71 (C4-G5)
- Velocity is fixed at 100 (can be customized in code)

## API Reference

### Global Objects

#### `appState`
Central state management object.

```javascript
// Get/Set BPM
appState.getBPM()
appState.setBPM(120)

// Notes
appState.setNote(trackIndex, step, noteIndex)
appState.toggleNote(trackIndex, step, noteIndex)
appState.getNote(trackIndex, step)

// Tracks
appState.selectTrack(trackIndex)
appState.clearTrack(trackIndex)
appState.clearAll()

// Volumes
appState.setMasterVolume(0.5)
appState.setTrackVolume(trackIndex, 0.7)

// Waveform
appState.setWaveform('square') // 'square', 'triangle', 'sawtooth'

// Serialization
const json = appState.export()
appState.import(json)
```

#### `sequencer`
Main sequencer controlling playback.

```javascript
sequencer.play()
sequencer.stop()
sequencer.togglePlayback()
sequencer.setBPM(120)
sequencer.setWaveform('triangle')
sequencer.clearAll()
sequencer.setMidiEnabled(true)
```

#### `audioEngine`
Web Audio API management.

```javascript
audioEngine.playStep(trackIndex, noteIndex, duration, 'square', 0.5)
audioEngine.setMasterVolume(0.8)
audioEngine.setTrackVolume(trackIndex, 0.6)
audioEngine.stopAll()
```

#### `midiManager`
MIDI device control.

```javascript
midiManager.getOutputs()              // Get list of MIDI devices
midiManager.selectOutput(deviceId)    // Select device
midiManager.noteOn(noteIndex, 100, 0) // Send MIDI note on
midiManager.noteOff(noteIndex, 64, 0) // Send MIDI note off
midiManager.isEnabled()               // Check if MIDI active
```

#### `midiExporter`
MIDI file export.

```javascript
midiExporter.exportAndDownload()           // Download .mid file
const blob = midiExporter.export(appState) // Get Blob
```

### Console Commands

All commands available via `Sequencer.*` object:

```javascript
// Playback
Sequencer.play()
Sequencer.stop()
Sequencer.togglePlay()

// Configuration
Sequencer.setBPM(140)
Sequencer.setWaveform('sawtooth')

// Patterns
Sequencer.savePattern('myPattern')
Sequencer.loadPattern('myPattern')
Sequencer.listPatterns()
Sequencer.exportJSON()
Sequencer.exportMIDI()

// Info
Sequencer.getStats()
Sequencer.getState()
```

## Advanced Usage

### Saving and Loading Patterns

Patterns are automatically saved to browser's LocalStorage:

```javascript
// Save pattern
App.savePattern('techno_beat')

// Load pattern
App.loadPattern('techno_beat')

// List all saved patterns
App.listPatterns()

// Export as JSON file
App.exportJSON()
```

### Creating Custom Patterns

Programmatically create patterns:

```javascript
// Get state reference
const state = appState

// Set a notes
state.setNote(0, 0, 4)  // Track 0, Step 0, Note G4
state.setNote(0, 4, 4)  // Track 0, Step 4, Note G4
state.setNote(0, 8, 2)  // Track 0, Step 8, Note E4

// Configure playback
state.setBPM(130)
state.setWaveform('square')

// Play
sequencer.play()
```

### Extending the Sequencer

The modular architecture makes extension easy. Examples:

1. **Add More Tracks**: Modify `State.js` to create more tracks
2. **Custom Waveforms**: Extend `Synth.js` with new oscillator types
3. **Effects**: Add effects by inserting Web Audio Nodes
4. **Pattern Editor**: Extend `PianoRoll.js` for different grid views
5. **Recording**: Add input recorder using Constraints API

## Browser Support

| Browser | Support |
|---------|---------|
| Chrome/Edge | ✅ Full support |
| Firefox | ✅ Full support |
| Safari | ✅ (except MIDI) |
| Safari iOS | ⚠️ Limited (no MIDI) |

**Note**: Web MIDI API requires HTTPS in most browsers. Development can use localhost.

## Technical Details

### Audio Processing
- **Sample Rate**: Browser's native (usually 48kHz)
- **Buffer Size**: Browser's default (usually 4096 samples)
- **Latency**: Minimal, depends on browser implementation
- **Polyphony**: Limited by Web Audio API voice pool (default 8)

### MIDI Implementation
- **Protocol**: Standard MIDI 1.0
- **File Format**: Type 1 (multi-track)
- **Resolution**: 480 ticks per quarter note
- **Timing**: Quantized to 16-step pattern

### State Management
- **Format**: JSON-serializable JavaScript objects
- **Change Notification**: Event-based observer pattern
- **Storage**: Optional LocalStorage integration

## Performance

- **Memory**: ~10-20 MB (varies with browser)
- **CPU**: Minimal impact (no continuous rendering)
- **Audio Thread**: Offloaded to Web Audio API
- **Rendering**: Only updates on state changes

## Limitations and Future Work

### Current Limitations
- Fixed 12-note range (C4-G5) - easily expandable
- 3 tracks maximum - can be increased
- 16-step fixed length - can be parameterized
- No effects (reverb, delay, etc.)
- No pattern chaining/sequencing
- MIDI import is not yet implemented

### Future Enhancements
- [ ] Four-channel polyphonic recording
- [ ] Audio effects (reverb, delay, filter, EQ)
- [ ] Multiple pattern banks (A, B, C, D)
- [ ] Pattern chaining/song mode
- [ ] Swing/shuffle timing
- [ ] Arpeggiator
- [ ] Drum samples playback
- [ ] MIDI import functionality
- [ ] Touch/gesture control for mobile
- [ ] Offline WebWorker for audio processing
- [ ] Audio input recording
- [ ] Real-time waveform visualization

## License

This project is free and open-source. Use it for personal, educational, and commercial purposes.

## Credits

Inspired by classic trackers:
- FastTracker 2
- ScreamTracker
- ProTracker
- OctaMED

Created with vanilla JavaScript, Web Audio API, and Web MIDI API.

---

**Enjoy making music! 🎶**