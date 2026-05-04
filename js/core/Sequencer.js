/**
 * Sequencer.js - Core sequencer logic
 * Handles playback timing and note triggering
 */
class Sequencer {
    constructor() {
        this.isPlaying = false;
        this.currentStep = 0;
        this.playbackStartTime = null;
        this.stepsPlayed = 0;
        this.animationFrameId = null;
        this.midiEnabled = false;
        this.midiTrackChannel = 0; // Which channel to use for MIDI

        // Bind methods
        this.play = this.play.bind(this);
        this.stop = this.stop.bind(this);
        this.update = this.update.bind(this);

        // Subscribe to state changes
        appState.subscribe('stateChange', () => this.onStateChange());
    }

    /**
     * Start playback
     */
    play() {
        if (this.isPlaying) return;

        audioEngine.resumeAudioContext().then(() => {
            this.isPlaying = true;
            this.playbackStartTime = this.getPlaybackTime();
            this.stepsPlayed = 0;
            appState.setPlaying(true);

            // Start update loop
            this.update();
        });
    }

    /**
     * Stop playback
     */
    stop() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        this.currentStep = 0;
        appState.setCurrentStep(0);
        appState.setPlaying(false);

        // Cancel animation frame
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }

        // Stop all audio
        audioEngine.stopAll();

        // Send MIDI All Notes Off
        if (this.midiEnabled && midiManager.isEnabled()) {
            for (let channel = 0; channel < 3; channel++) {
                midiManager.allNotesOff(channel);
            }
        }
    }

    /**
     * Get current playback time considering audio context time
     */
    getPlaybackTime() {
        return audioEngine.audioContext.currentTime;
    }

    /**
     * Main update loop - runs every frame
     */
    update() {
        if (!this.isPlaying) return;

        const currentTime = this.getPlaybackTime();
        const elapsedTime = currentTime - this.playbackStartTime;
        const stepDuration = audioEngine.stepDuration;

        // Calculate which step we're on
        const newStepsPlayed = Math.floor(elapsedTime / stepDuration);

        // Check if we've moved to a new step
        if (newStepsPlayed !== this.stepsPlayed) {
            this.stepsPlayed = newStepsPlayed;
            this.currentStep = this.stepsPlayed % 16;

            // Trigger notes for current step
            this.triggerStep(this.currentStep);

            // Update UI
            appState.setCurrentStep(this.currentStep);
        }

        // Continue update loop
        this.animationFrameId = requestAnimationFrame(this.update);
    }

    /**
     * Trigger all notes at a specific step
     */
    triggerStep(stepIndex) {
        // Play note from each track if it has a note at this step
        appState.tracks.forEach((track, trackIndex) => {
            const noteIndex = track.notes[stepIndex];
            const instrument = track.instrument || 'synth';

            if (noteIndex !== null) {
                // Play internal audio
                const noteDuration = audioEngine.stepDuration * 0.8; // 80% of step
                audioEngine.playStep(
                    trackIndex,
                    noteIndex,
                    noteDuration,
                    instrument === 'drums' ? 'square' : appState.waveform,
                    track.volume,
                    instrument
                );

                // Send MIDI if enabled
                if (this.midiEnabled && midiManager.isEnabled()) {
                    const midiChannel = instrument === 'drums' ? 9 : trackIndex;
                    midiManager.noteOn(noteIndex, 100, midiChannel);

                    // Schedule MIDI note off
                    setTimeout(() => {
                        midiManager.noteOff(noteIndex, 64, midiChannel);
                    }, noteDuration * 1000);
                }
            }
        });
    }

    /**
     * Toggle playback
     */
    togglePlayback() {
        if (this.isPlaying) {
            this.stop();
        } else {
            this.play();
        }
    }

    /**
     * Set BPM
     */
    setBPM(bpm) {
        appState.setBPM(bpm);
        audioEngine.setBPM(bpm);
    }

    /**
     * Set waveform for all tracks
     */
    setWaveform(waveform) {
        appState.setWaveform(waveform);
    }

    /**
     * Clear all patterns
     */
    clearAll() {
        this.stop();
        appState.clearAll();
    }

    /**
     * Enable/disable MIDI output
     */
    setMidiEnabled(enabled) {
        this.midiEnabled = enabled;
        if (!enabled && midiManager.isEnabled()) {
            // Send All Notes Off to MIDI outputs
            for (let channel = 0; channel < 3; channel++) {
                midiManager.allNotesOff(channel);
            }
        }
    }

    /**
     * Handle state changes
     */
    onStateChange() {
        // Update audio engine parameters
        if (this.isPlaying && appState.bpm !== audioEngine.stepDuration) {
            audioEngine.setBPM(appState.bpm);
        }
    }

    /**
     * Get current playback position (0-15)
     */
    getCurrentStep() {
        return this.currentStep;
    }

    /**
     * Check if sequencer is playing
     */
    getIsPlaying() {
        return this.isPlaying;
    }
}

// Create global sequencer instance
const sequencer = new Sequencer();
