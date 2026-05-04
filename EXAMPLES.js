/**
 * EXAMPLES.js - Usage examples for Web Sequencer
 * Open browser console (F12) and try these commands
 */

// ============================================================================
// BASIC PLAYBACK CONTROLS
// ============================================================================

/**
 * Play a simple pattern
 */
function examplePlaySimplePattern() {
    // Clear everything
    appState.clearAll();
    
    // Add some notes to track 1
    appState.setNote(0, 0, 4);   // Step 0: G4
    appState.setNote(0, 4, 2);   // Step 4: E4
    appState.setNote(0, 8, 0);   // Step 8: C4
    appState.setNote(0, 12, 2);  // Step 12: E4
    
    // Add bass line to track 2
    appState.selectTrack(1);
    appState.setNote(1, 0, 0);   // Step 0: C4
    appState.setNote(1, 4, 0);   // Step 4: C4
    
    // Set tempo and play
    appState.setBPM(100);
    sequencer.play();
    
    console.log('Simple pattern playing at 100 BPM');
}

/**
 * Play a techno beat
 */
function exampleTechnoPattern() {
    appState.clearAll();
    appState.setBPM(130);
    appState.setWaveform('square');
    
    // Kick pattern on track 1 (C4)
    appState.selectTrack(0);
    for (let i = 0; i < 16; i += 4) {
        appState.setNote(0, i, 0);
    }
    appState.setNote(0, 2, 0);
    appState.setNote(0, 10, 0);
    
    // Hi-hat pattern on track 2 (G4)
    appState.selectTrack(1);
    for (let i = 0; i < 16; i += 2) {
        appState.setNote(1, i, 4);
    }
    
    sequencer.play();
    console.log('Techno pattern playing');
}

/**
 * Create a melodic pattern
 */
function exampleMelodicPattern() {
    appState.clearAll();
    appState.setBPM(120);
    appState.setWaveform('triangle');
    
    // Melody: C-E-G-C-E-G-A-G
    appState.selectTrack(0);
    const melody = [0, 2, 4, 0, 2, 4, 5, 4];
    melody.forEach((note, i) => {
        appState.setNote(0, i, note);
    });
    
    // Pad on track 2
    appState.selectTrack(1);
    appState.setNote(1, 0, 0);
    appState.setNote(1, 8, 0);
    
    sequencer.play();
    console.log('Melodic pattern with pad');
}

// ============================================================================
// VOLUME AND EFFECTS
// ============================================================================

/**
 * Set different volumes
 */
function exampleVolumes() {
    appState.setMasterVolume(0.5);      // Master at 50%
    appState.setTrackVolume(0, 0.8);    // Track 1 at 80%
    appState.setTrackVolume(1, 0.6);    // Track 2 at 60%
    appState.setTrackVolume(2, 0.4);    // Track 3 at 40%
    
    console.log('Volumes adjusted');
}

/**
 * Test different waveforms
 */
function exampleWaveforms() {
    const waveforms = ['square', 'triangle', 'sawtooth'];
    
    appState.clearAll();
    appState.selectTrack(0);
    appState.setNote(0, 0, 4);
    
    console.log('Testing waveforms. Current:', appState.waveform);
    console.log('Available: square, triangle, sawtooth');
    
    // Play each waveform for 2 seconds
    let index = 0;
    const interval = setInterval(() => {
        if (index < waveforms.length) {
            appState.setWaveform(waveforms[index]);
            console.log('Playing:', waveforms[index]);
            index++;
        } else {
            clearInterval(interval);
            console.log('Waveform test complete');
        }
    }, 2000);
}

// ============================================================================
// PATTERN MANAGEMENT
// ============================================================================

/**
 * Save current pattern to browser storage
 */
function exampleSavePattern() {
    const patternName = 'my_pattern_' + Date.now();
    App.savePattern(patternName);
    console.log('Pattern saved as:', patternName);
}

/**
 * Load saved pattern
 */
function exampleLoadPattern() {
    const patterns = App.listPatterns();
    if (patterns.length > 0) {
        App.loadPattern(patterns[0]);
        console.log('Loaded pattern:', patterns[0]);
    } else {
        console.log('No saved patterns found');
    }
}

/**
 * Export current pattern as JSON
 */
function exampleExportJSON() {
    App.exportJSON();
    console.log('Pattern exported as sequencer_pattern.json');
}

/**
 * List all saved patterns
 */
function exampleListPatterns() {
    const patterns = App.listPatterns();
    console.log('Saved patterns:', patterns);
    patterns.forEach((p, i) => console.log(`  ${i + 1}. ${p}`));
}

/**
 * Get current application statistics
 */
function exampleGetStats() {
    const stats = App.getStats();
    console.table(stats);
}

// ============================================================================
// MIDI FUNCTIONALITY
// ============================================================================

/**
 * List available MIDI devices
 */
function exampleListMidiDevices() {
    const devices = midiManager.getOutputs();
    
    if (devices.length === 0) {
        console.log('No MIDI devices found');
    } else {
        console.log('Available MIDI outputs:');
        devices.forEach((device, i) => {
            console.log(`  ${i + 1}. ${device.name} (${device.manufacturer})`);
        });
    }
}

/**
 * Select first available MIDI device
 */
function exampleSelectMidiDevice() {
    const devices = midiManager.getOutputs();
    if (devices.length > 0) {
        midiManager.selectOutput(devices[0].id);
        sequencer.setMidiEnabled(true);
        console.log('MIDI enabled:', devices[0].name);
    } else {
        console.log('No MIDI devices available');
    }
}

/**
 * Export pattern as MIDI file
 */
function exampleExportMidi() {
    midiExporter.exportAndDownload();
    console.log('MIDI file downloaded');
}

// ============================================================================
// ADVANCED PATTERNS
// ============================================================================

/**
 * Create a polyrhythmic pattern
 */
function examplePolyrhythm() {
    appState.clearAll();
    appState.setBPM(120);
    
    // Track 1: 4/4 beat (every 4 steps)
    appState.selectTrack(0);
    for (let i = 0; i < 16; i += 4) {
        appState.setNote(0, i, 0);
    }
    
    // Track 2: 3/4 beat (every ~5.33 steps, rounded)
    appState.selectTrack(1);
    for (let i = 0; i < 16; i += 5) {
        if (i < 16) appState.setNote(1, i, 2);
    }
    
    // Track 3: 2/4 beat (every 2 steps)
    appState.selectTrack(2);
    for (let i = 0; i < 16; i += 2) {
        appState.setNote(2, i, 4);
    }
    
    sequencer.play();
    console.log('Polyrhythmic pattern started');
}

/**
 * Create a random generative pattern
 */
function exampleRandomPattern() {
    appState.clearAll();
    appState.setBPM(140);
    
    // Generate random melodies for each track
    for (let track = 0; track < 3; track++) {
        appState.selectTrack(track);
        
        // Random pattern: place notes with 40% probability
        for (let step = 0; step < 16; step++) {
            if (Math.random() < 0.4) {
                const noteIndex = Math.floor(Math.random() * 12);
                appState.setNote(track, step, noteIndex);
            }
        }
    }
    
    sequencer.play();
    console.log('Random generative pattern created');
}

/**
 * Create a pentatonic scale pattern
 */
function examplePentatonic() {
    appState.clearAll();
    appState.setBPM(110);
    appState.setWaveform('triangle');
    
    // Pentatonic scale: C, D, E, G, A (indices 0, 1, 2, 4, 5)
    const pentatonic = [0, 1, 2, 4, 5, 4, 2, 1];
    
    appState.selectTrack(0);
    pentatonic.forEach((note, i) => {
        appState.setNote(0, i, note);
    });
    
    // Simple bass line
    appState.selectTrack(1);
    appState.setNote(1, 0, 0);
    appState.setNote(1, 8, 4);
    
    sequencer.play();
    console.log('Pentatonic scale pattern');
}

// ============================================================================
// DEBUGGING AND INTROSPECTION
// ============================================================================

/**
 * Print current state
 */
function examplePrintState() {
    const state = appState;
    console.log('Current State:');
    console.log('  BPM:', state.bpm);
    console.log('  Playing:', state.isPlaying);
    console.log('  Current Step:', state.currentStep);
    console.log('  Selected Track:', state.selectedTrack);
    console.log('  Waveform:', state.waveform);
    console.log('  Master Volume:', state.masterVolume);
    
    state.tracks.forEach((track, i) => {
        const noteCount = track.notes.filter(n => n !== null).length;
        console.log(`  Track ${i + 1}: ${noteCount} notes, volume: ${track.volume}`);
    });
}

/**
 * Test audio latency
 */
function exampleTestLatency() {
    appState.clearAll();
    appState.selectTrack(0);
    appState.setNote(0, 0, 4);
    
    const startTime = performance.now();
    sequencer.play();
    
    setTimeout(() => {
        const latency = performance.now() - startTime;
        console.log(`Playback start latency: ${latency.toFixed(2)}ms`);
    }, 100);
}

// ============================================================================
// QUICK START EXAMPLES
// ============================================================================

/**
 * Run this to start with a demo pattern
 */
function quickStart() {
    console.log('🎵 Welcome to Web Sequencer!');
    console.log('');
    console.log('Quick commands:');
    console.log('  examplePlaySimplePattern()  - Play a simple pattern');
    console.log('  exampleTechnoPattern()      - Play a techno beat');
    console.log('  exampleMelodicPattern()     - Play a melody');
    console.log('  exampleWaveforms()          - Test different waveforms');
    console.log('  examplePolyrhythm()         - Polyrhythmic pattern');
    console.log('  exampleRandomPattern()      - Generative pattern');
    console.log('  examplePentatonic()         - Pentatonic scale');
    console.log('');
    console.log('MIDI:');
    console.log('  exampleListMidiDevices()    - See connected MIDI devices');
    console.log('  exampleSelectMidiDevice()   - Enable MIDI output');
    console.log('  exampleExportMidi()         - Download pattern as .mid');
    console.log('');
    console.log('Pattern management:');
    console.log('  exampleSavePattern()        - Save current pattern');
    console.log('  exampleLoadPattern()        - Load last saved pattern');
    console.log('  exampleListPatterns()       - Show all saved patterns');
    console.log('  exampleExportJSON()         - Download pattern as JSON');
    console.log('');
    console.log('Playing: Space bar');
    console.log('');
    
    // Start with simple pattern
    examplePlaySimplePattern();
}

// Show quick start on initialization
console.log('Type: quickStart() to see examples');
