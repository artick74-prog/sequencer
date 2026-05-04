# 🔧 Extension Guide - Web Sequencer

This document explains how to extend and customize the Web Sequencer.

## Architecture Overview

The sequencer is built with a **modular plugin-like architecture**:

```
┌──────────────────────────────────────────────────────┐
│  main.js - Initialization & API                      │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐  ┌─────────────────┐            │
│  │   UI Layer      │  │ State Management│            │
│  ├─────────────────┤  ├─────────────────┤            │
│  │ PianoRoll.js    │  │ State.js        │            │
│  │ Controls.js     │  │ (Event-driven)  │            │
│  └─────────────────┘  └─────────────────┘            │
│         ↓                      ↑↓                      │
│  ┌─────────────────┐  ┌─────────────────┐            │
│  │  Sequencer      │  │ Audio Engine    │            │
│  ├─────────────────┤  ├─────────────────┤            │
│  │ Sequencer.js    │→→→ AudioEngine.js  │            │
│  │ (Timing)        │  │ Synth.js        │            │
│  └─────────────────┘  └─────────────────┘            │
│         ↓                      ↓                       │
│  ┌──────────────────────────────────┐                │
│  │  MIDI Systems                    │                │
│  ├──────────────────────────────────┤                │
│  │ MidiOutput.js (Web MIDI API)     │                │
│  │ MidiExporter.js (MIDI file gen)  │                │
│  └──────────────────────────────────┘                │
└──────────────────────────────────────────────────────┘
```

## Common Extensions

### 1. Add More Tracks

**File**: `js/core/State.js`

```javascript
// In SequencerState constructor, change:
this.tracks = [
    // ... existing tracks ...
    { name: 'Track 4', volume: 0.5, notes: this.createEmptyPattern() },
    { name: 'Track 5', volume: 0.5, notes: this.createEmptyPattern() }
];

// Update constraints in selectTrack():
selectTrack(trackIndex) {
    if (trackIndex >= 0 && trackIndex < 5) {  // Changed from 3 to 5
        this.selectedTrack = trackIndex;
        this.notifyListeners('trackChange');
    }
}
```

**Also update** `js/audio/AudioEngine.js`:

```javascript
// Add more synths in constructor:
this.synths = [
    // ... existing 3 ...
    new SimpleSynth(this.audioContext),
    new SimpleSynth(this.audioContext)
];

// Add more track gains:
this.trackGains = [
    // ... existing 3 ...
    this.audioContext.createGain(),
    this.audioContext.createGain()
];
```

**And** `index.html`:
```html
<!-- Add buttons in track-selector -->
<button class="track-btn" data-track="3">Track 4</button>
<button class="track-btn" data-track="4">Track 5</button>
```

### 2. Expand Note Range

**File**: `js/audio/Synth.js`

```javascript
buildNoteFrequencies() {
    const notes = {
        // Add lower octaves
        -12: 130.81,  // C3
        -11: 146.83,  // D3
        -10: 164.81,  // E3
        // ... existing ...
        // Add higher octaves
        12: 1046.50,  // C6
        13: 1174.66,  // D6
        14: 1318.51,  // E6
        // ... etc
    };
    return notes;
}

getNoteName(noteIndex) {
    const noteNames = [..., 'C6', 'D6', 'E6', ...];
    return noteNames[noteIndex] ?? 'C4';
}
```

**Update** `index.html` note labels:
```html
<div class="note-label" data-note="12">C6</div>
<div class="note-label" data-note="13">D6</div>
<!-- etc -->
```

### 3. Add Audio Effects

**New file**: `js/audio/Effects.js`

```javascript
class ReverbEffect {
    constructor(audioContext) {
        this.audioContext = audioContext;
        this.input = audioContext.createGain();
        this.output = audioContext.createGain();
        
        // Simple convolver reverb (needs impulse response)
        this.convolver = audioContext.createConvolver();
        this.dryGain = audioContext.createGain();
        this.wetGain = audioContext.createGain();
        
        this.input.connect(this.dryGain);
        this.input.connect(this.convolver);
        this.dryGain.connect(this.output);
        this.convolver.connect(this.wetGain);
        this.wetGain.connect(this.output);
        
        this.dryGain.gain.value = 0.7;
        this.wetGain.gain.value = 0.3;
    }
    
    setMix(dry, wet) {
        this.dryGain.gain.value = dry;
        this.wetGain.gain.value = wet;
    }
}

class DelayEffect {
    constructor(audioContext, delayTime = 0.5) {
        this.audioContext = audioContext;
        this.input = audioContext.createGain();
        this.output = audioContext.createGain();
        
        this.delay = audioContext.createDelay(5);
        this.feedback = audioContext.createGain();
        this.wetGain = audioContext.createGain();
        
        this.delay.delayTime.value = delayTime;
        this.feedback.gain.value = 0.4;
        
        this.input.connect(this.output);
        this.input.connect(this.delay);
        this.delay.connect(this.feedback);
        this.feedback.connect(this.delay);
        this.delay.connect(this.wetGain);
        this.wetGain.connect(this.output);
        
        this.wetGain.gain.value = 0.3;
    }
}
```

**Then in** `js/audio/AudioEngine.js`:
```javascript
// Add in constructor:
this.delayEffect = new DelayEffect(this.audioContext);
this.masterGain.connect(this.delayEffect.input);
this.delayEffect.output.connect(this.audioContext.destination);
```

### 4. Add Pattern Banks

**File**: `js/core/State.js`

```javascript
class PatternBank {
    constructor() {
        this.patterns = {};
        this.currentPattern = 'default';
    }
    
    save(name, state) {
        this.patterns[name] = JSON.parse(JSON.stringify(state.toJSON()));
    }
    
    load(name, state) {
        if (this.patterns[name]) {
            state.fromJSON(this.patterns[name]);
            return true;
        }
        return false;
    }
    
    list() {
        return Object.keys(this.patterns);
    }
    
    delete(name) {
        delete this.patterns[name];
    }
}
```

### 5. Add Swing/Shuffle

**File**: `js/core/Sequencer.js`

```javascript
class Sequencer {
    constructor() {
        // ... existing ...
        this.swingAmount = 0; // 0-50%
        this.swingSteps = [1, 3, 5, 7, 9, 11, 13, 15]; // Off-beat steps
    }
    
    calculateStepTime(stepIndex) {
        let time = stepIndex * this.getPlaybackTime();
        
        // Apply swing to off-beat steps
        if (this.swingSteps.includes(stepIndex)) {
            time += this.getPlaybackTime() * (this.swingAmount / 100);
        }
        
        return time;
    }
    
    setSwing(amount) {
        this.swingAmount = Math.max(0, Math.min(50, amount));
    }
}
```

### 6. Add Arpeggiator

**New file**: `js/core/Arpeggiator.js`

```javascript
class Arpeggiator {
    constructor(sequencer) {
        this.sequencer = sequencer;
        this.enabled = false;
        this.speed = 1; // 1 = quarter notes, 2 = eighth notes
        this.pattern = 'up'; // 'up', 'down', 'updown'
        this.octaves = 1;
    }
    
    generateNotes(noteIndex) {
        if (!this.enabled || noteIndex === null) return [noteIndex];
        
        const notes = [noteIndex];
        const noteNames = [0, 1, 2, 4, 5, 7, 9, 11]; // Scale degrees
        
        if (this.pattern === 'up') {
            for (let oct = 1; oct < this.octaves; oct++) {
                notes.push(noteIndex + 12 * oct);
            }
        }
        
        return notes;
    }
}
```

### 7. Add Polyphonic Recording

**New file**: `js/audio/Recorder.js`

```javascript
class AudioRecorder {
    constructor(audioContext) {
        this.audioContext = audioContext;
        this.mediaRecorder = null;
        this.chunks = [];
    }
    
    start(sourceNode) {
        const dest = this.audioContext.createMediaStreamAudioDestination();
        sourceNode.connect(dest);
        
        this.mediaRecorder = new MediaRecorder(dest.stream);
        this.chunks = [];
        
        this.mediaRecorder.ondataavailable = (e) => {
            this.chunks.push(e.data);
        };
        
        this.mediaRecorder.start();
    }
    
    stop() {
        return new Promise((resolve) => {
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.chunks, { type: 'audio/wav' });
                resolve(blob);
            };
            this.mediaRecorder.stop();
        });
    }
    
    download(filename = 'recording.wav') {
        this.stop().then(blob => {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.click();
        });
    }
}
```

### 8. Add Pattern Chaining

**File**: `js/core/Sequencer.js`

```javascript
class Sequencer {
    constructor() {
        // ... existing ...
        this.patternChain = [];
        this.currentPatternIndex = 0;
    }
    
    createChain(patternNames) {
        this.patternChain = patternNames;
        this.currentPatternIndex = 0;
    }
    
    nextPattern() {
        this.currentPatternIndex = (this.currentPatternIndex + 1) % this.patternChain.length;
        this.loadPattern(this.patternChain[this.currentPatternIndex]);
    }
}
```

### 9. Add Visual Waveform Display

**File**: `js/ui/Visualizer.js`

```javascript
class AudioVisualizer {
    constructor(canvas, audioContext) {
        this.canvas = canvas;
        this.ctx = this.canvas.getContext('2d');
        this.analyser = audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        
        this.bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(this.bufferLength);
        
        this.animate();
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        this.analyser.getByteFrequencyData(this.dataArray);
        
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        const barWidth = this.canvas.width / this.bufferLength;
        let x = 0;
        
        for (let i = 0; i < this.bufferLength; i++) {
            const barHeight = (this.dataArray[i] / 255) * this.canvas.height;
            
            this.ctx.fillStyle = '#00ff00';
            this.ctx.fillRect(x, this.canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth;
        }
    }
}
```

## Testing Extensions

After adding features:

1. **Test in console**:
```javascript
// Check if extension loaded
console.log(typeof ReverbEffect) // Should show 'function'

// Test functionality
const effect = new ReverbEffect(audioEngine.audioContext);
```

2. **Check for errors**:
   - Open DevTools (F12)
   - Check Console tab for errors
   - Look for red X marks in file list

3. **Test with patterns**:
   - Load EXAMPLES.js
   - Run `examplePlaySimplePattern()`
   - Verify your extension works

## Performance Tips

When extending with heavy features:

1. **Use Web Workers** for audio processing
2. **Debounce UI updates** to 60 FPS max
3. **Lazy-load effects** only when needed
4. **Use typed arrays** for audio buffers
5. **Limit polyphony** to 8-16 voices max

## Documentation Template

When adding new modules, include:

```javascript
/**
 * ModuleName.js - Brief description
 * Longer description of what this module does,
 * how it integrates, and any Web Audio API specifics.
 * 
 * Dependencies: List modules it depends on
 * Used by: List modules that use this
 */

class ModuleName {
    /**
     * Constructor
     * @param {param1} Description
     */
    constructor(param1) {
        // Implementation
    }
    
    /**
     * Public method description
     * @param {param} Description
     * @returns {type} Return description
     */
    publicMethod(param) {
        // Implementation
    }
}
```

## Debugging Tips

```javascript
// Enable detailed logging
localStorage.setItem('debug', 'true');

// Check state changes
appState.subscribe('stateChange', () => {
    console.log('State changed:', appState.toJSON());
});

// Monitor audio activity
const stats = audioEngine.getAudioData();
console.log('Active notes:', stats.playingNotesCount);

// Profile performance
console.time('rendering');
pianoRoll.render();
console.timeEnd('rendering');
```

---

## Next Steps

1. Choose an extension from above
2. Follow the code examples
3. Test in browser console
4. Share your creations!

**Happy extending!** 🎵
