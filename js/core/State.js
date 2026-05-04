/**
 * State.js - Central state management for the sequencer
 * Handles all application state in a serializable format
 */
class SequencerState {
    constructor() {
        // Initialize state with default values
        this.bpm = 120;
        this.isPlaying = false;
        this.currentStep = 0;
        this.selectedTrack = 0;
        this.waveform = 'square';
        this.masterVolume = 0.3;
        this.midiOutputId = null;
        this.midiEnabled = false;

        // Pattern data: 3 tracks, 16 steps, 12 notes each
        this.tracks = [
            { name: 'Track 1', volume: 0.5, notes: this.createEmptyPattern() },
            { name: 'Track 2', volume: 0.5, notes: this.createEmptyPattern() },
            { name: 'Track 3', volume: 0.5, notes: this.createEmptyPattern() }
        ];

        // Listeners for state changes
        this.listeners = {
            stateChange: [],
            stepChange: [],
            trackChange: [],
            playStateChange: []
        };

        // Store for undo/redo (optional)
        this.history = [];
        this.historyIndex = -1;
    }

    /**
     * Create an empty pattern (16 steps x 12 notes)
     * Returns array where each step contains a note index or null
     */
    createEmptyPattern() {
        return new Array(16).fill(null);
    }

    /**
     * Get the currently selected track
     */
    getSelectedTrack() {
        return this.tracks[this.selectedTrack];
    }

    /**
     * Set note at specific step and note position
     */
    setNote(trackIndex, step, noteIndex) {
        const track = this.tracks[trackIndex];
        if (step >= 0 && step < 16) {
            track.notes[step] = noteIndex !== null ? noteIndex : null;
            this.notifyListeners('stateChange');
        }
    }

    /**
     * Toggle note (add if empty, remove if present)
     */
    toggleNote(trackIndex, step, noteIndex) {
        const track = this.tracks[trackIndex];
        if (step >= 0 && step < 16) {
            const current = track.notes[step];
            track.notes[step] = current === noteIndex ? null : noteIndex;
            this.notifyListeners('stateChange');
        }
    }

    /**
     * Get note at specific step
     */
    getNote(trackIndex, step) {
        if (trackIndex >= 0 && trackIndex < 3 && step >= 0 && step < 16) {
            return this.tracks[trackIndex].notes[step];
        }
        return null;
    }

    /**
     * Clear all notes in a track
     */
    clearTrack(trackIndex) {
        this.tracks[trackIndex].notes = this.createEmptyPattern();
        this.notifyListeners('stateChange');
    }

    /**
     * Clear all tracks
     */
    clearAll() {
        this.tracks.forEach(track => {
            track.notes = this.createEmptyPattern();
        });
        this.currentStep = 0;
        this.notifyListeners('stateChange');
    }

    /**
     * Set BPM
     */
    setBPM(bpm) {
        this.bpm = Math.max(30, Math.min(300, bpm));
        this.notifyListeners('stateChange');
    }

    /**
     * Set playing state
     */
    setPlaying(isPlaying) {
        this.isPlaying = isPlaying;
        this.notifyListeners('playStateChange');
    }

    /**
     * Update current step
     */
    setCurrentStep(step) {
        this.currentStep = step % 16;
        this.notifyListeners('stepChange');
    }

    /**
     * Select track
     */
    selectTrack(trackIndex) {
        if (trackIndex >= 0 && trackIndex < 3) {
            this.selectedTrack = trackIndex;
            this.notifyListeners('trackChange');
        }
    }

    /**
     * Set waveform type
     */
    setWaveform(waveform) {
        if (['square', 'triangle', 'sawtooth'].includes(waveform)) {
            this.waveform = waveform;
            this.notifyListeners('stateChange');
        }
    }

    /**
     * Set master volume
     */
    setMasterVolume(volume) {
        this.masterVolume = Math.max(0, Math.min(1, volume));
        this.notifyListeners('stateChange');
    }

    /**
     * Set track volume
     */
    setTrackVolume(trackIndex, volume) {
        if (trackIndex >= 0 && trackIndex < 3) {
            this.tracks[trackIndex].volume = Math.max(0, Math.min(1, volume));
            this.notifyListeners('stateChange');
        }
    }

    /**
     * Set MIDI output
     */
    setMidiOutput(deviceId) {
        this.midiOutputId = deviceId;
        this.midiEnabled = deviceId !== null;
        this.notifyListeners('stateChange');
    }

    /**
     * Subscribe to state changes
     */
    subscribe(eventType, callback) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].push(callback);
        }
    }

    /**
     * Unsubscribe from state changes
     */
    unsubscribe(eventType, callback) {
        if (this.listeners[eventType]) {
            this.listeners[eventType] = this.listeners[eventType].filter(cb => cb !== callback);
        }
    }

    /**
     * Notify all listeners of a state change
     */
    notifyListeners(eventType) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].forEach(callback => callback());
        }
    }

    /**
     * Serialize state to JSON
     */
    toJSON() {
        return {
            bpm: this.bpm,
            selectedTrack: this.selectedTrack,
            waveform: this.waveform,
            masterVolume: this.masterVolume,
            midiOutputId: this.midiOutputId,
            tracks: this.tracks.map(track => ({
                name: track.name,
                volume: track.volume,
                notes: [...track.notes]
            }))
        };
    }

    /**
     * Load state from JSON
     */
    fromJSON(data) {
        if (data.bpm) this.bpm = data.bpm;
        if (data.selectedTrack !== undefined) this.selectedTrack = data.selectedTrack;
        if (data.waveform) this.waveform = data.waveform;
        if (data.masterVolume !== undefined) this.masterVolume = data.masterVolume;
        if (data.midiOutputId) this.midiOutputId = data.midiOutputId;

        if (data.tracks && Array.isArray(data.tracks)) {
            data.tracks.forEach((trackData, index) => {
                if (index < this.tracks.length) {
                    if (trackData.name) this.tracks[index].name = trackData.name;
                    if (trackData.volume !== undefined) this.tracks[index].volume = trackData.volume;
                    if (trackData.notes && Array.isArray(trackData.notes)) {
                        this.tracks[index].notes = [...trackData.notes];
                    }
                }
            });
        }

        this.notifyListeners('stateChange');
    }

    /**
     * Export state as JSON string
     */
    export() {
        return JSON.stringify(this.toJSON(), null, 2);
    }

    /**
     * Import state from JSON string
     */
    import(jsonString) {
        try {
            const data = JSON.parse(jsonString);
            this.fromJSON(data);
            return true;
        } catch (error) {
            console.error('Failed to import state:', error);
            return false;
        }
    }
}

// Create global instance
const appState = new SequencerState();
