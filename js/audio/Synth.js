/**
 * Synth.js - Web Audio API synthesizer implementation
 * Handles oscillator creation and audio synthesis
 */
class SimpleSynth {
    static getNoteNameStatic(noteIndex) {
        const notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const octave = Math.floor(noteIndex / 12) + 4;
        const note = notes[noteIndex % 12];
        return note + octave;
    }

    constructor(audioContext) {
        this.audioContext = audioContext;
        this.oscillators = new Map();
        this.gains = new Map();
        this.notes = new Map();

        // Note to frequency mapping
        this.noteFrequencies = this.buildNoteFrequencies();
    }

    /**
     * Build a mapping of note indices to frequencies
     * 12 notes from C4 (261.63 Hz) to B4
     */
    buildNoteFrequencies() {
        const notes = {
            0: 261.63,   // C4
            1: 293.66,   // D4
            2: 329.63,   // E4
            3: 349.23,   // F4
            4: 392.00,   // G4
            5: 440.00,   // A4
            6: 493.88,   // B4
            7: 523.25,   // C5
            8: 587.33,   // D5
            9: 659.25,   // E5
            10: 698.46,  // F5
            11: 783.99   // G5
        };
        return notes;
    }

    /**
     * Get frequency in Hz for a note index
     */
    getFrequency(noteIndex) {
        return this.noteFrequencies[noteIndex] || 440;
    }

    /**
     * Get note name from index
     */
    getNoteName(noteIndex) {
        const noteNames = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5', 'D5', 'E5', 'F5', 'G5'];
        return noteNames[noteIndex] || 'C4';
    }

    /**
     * Play a note on a specific voice/channel
     * voiceId: unique identifier for the voice (e.g., "track0", "track1", "track2")
     * noteIndex: 0-11 (C4 to G5)
     * duration: time in seconds (optional, for amplitude envelope)
     * waveform: 'square', 'triangle', 'sawtooth', 'sine'
     * volume: gain amount (0-1)
     */
    playNote(voiceId, noteIndex, duration = 1, waveform = 'square', volume = 0.5) {
        // Stop any previous note on this voice
        this.stopNote(voiceId);

        const frequency = this.getFrequency(noteIndex);

        // Create oscillator
        const oscillator = this.audioContext.createOscillator();
        oscillator.type = waveform;
        oscillator.frequency.value = frequency;

        // Create gain node for this voice
        const gain = this.audioContext.createGain();
        gain.gain.value = volume;

        // Create ADSR-like envelope
        const now = this.audioContext.currentTime;
        const attackTime = 0.01;
        const decayTime = 0.1;
        const sustainLevel = 0.7;

        // Attack
        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(volume, now + attackTime);

        // Decay to sustain
        gain.gain.linearRampToValueAtTime(volume * sustainLevel, now + attackTime + decayTime);

        // Connect nodes
        oscillator.connect(gain);
        gain.connect(this.audioContext.destination);

        // Start oscillator
        oscillator.start(now);

        // Schedule release
        const releaseTime = 0.2;
        const stopTime = now + duration - releaseTime;
        gain.gain.setValueAtTime(volume * sustainLevel, stopTime);
        gain.gain.linearRampToValueAtTime(0, stopTime + releaseTime);
        oscillator.stop(stopTime + releaseTime);

        // Store references
        this.oscillators.set(voiceId, oscillator);
        this.gains.set(voiceId, gain);
        this.notes.set(voiceId, {
            noteIndex,
            frequency,
            startTime: now,
            stopTime: stopTime + releaseTime
        });
    }

    /**
     * Stop a note on a specific voice
     */
    stopNote(voiceId) {
        const oscillator = this.oscillators.get(voiceId);
        const gain = this.gains.get(voiceId);

        if (oscillator && gain) {
            try {
                const now = this.audioContext.currentTime;
                const releaseTime = 0.1;
                gain.gain.setValueAtTime(gain.gain.value, now);
                gain.gain.linearRampToValueAtTime(0, now + releaseTime);
                oscillator.stop(now + releaseTime);
            } catch (e) {
                // Oscillator may have already stopped
            }

            this.oscillators.delete(voiceId);
            this.gains.delete(voiceId);
            this.notes.delete(voiceId);
        }
    }

    /**
     * Stop all playing notes
     */
    stopAll() {
        const voiceIds = Array.from(this.oscillators.keys());
        voiceIds.forEach(voiceId => this.stopNote(voiceId));
    }

    /**
     * Get list of currently playing notes
     */
    getPlayingNotes() {
        return Array.from(this.notes.values());
    }

    /**
     * Check if a voice is currently playing
     */
    isPlaying(voiceId) {
        return this.oscillators.has(voiceId);
    }
}

/**
 * PolyphonySynth - Enhanced synth for polyphonic-like behavior
 * Allows multiple notes per track (within limits)
 */
class PolyphonySynth extends SimpleSynth {
    constructor(audioContext, maxVoices = 8) {
        super(audioContext);
        this.maxVoices = maxVoices;
        this.voicePool = [];
        this.voiceIndex = 0;

        // Pre-allocate voice pool
        for (let i = 0; i < maxVoices; i++) {
            this.voicePool.push(`voice_${i}`);
        }
    }

    /**
     * Allocate next available voice
     */
    getNextVoice() {
        const voiceId = this.voicePool[this.voiceIndex % this.maxVoices];
        this.voiceIndex++;
        return voiceId;
    }

    /**
     * Play note and allocate from voice pool
     */
    playNotePooled(noteIndex, duration = 1, waveform = 'square', volume = 0.5) {
        const voiceId = this.getNextVoice();
        this.playNote(voiceId, noteIndex, duration, waveform, volume);
        return voiceId;
    }
}
