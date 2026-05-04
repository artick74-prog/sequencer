/**
 * AudioEngine.js - Main audio engine managing synths and playback
 * Coordinates audio output across multiple tracks
 */
class AudioEngine {
    constructor() {
        // Initialize Web Audio API
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext();

        // Create three independent synths for three tracks
        this.synths = [
            new SimpleSynth(this.audioContext),
            new SimpleSynth(this.audioContext),
            new SimpleSynth(this.audioContext)
        ];

        // Master gain node
        this.masterGain = this.audioContext.createGain();
        this.masterGain.connect(this.audioContext.destination);
        this.masterGain.gain.value = 0.3;

        // Track-specific gain nodes
        this.trackGains = [
            this.audioContext.createGain(),
            this.audioContext.createGain(),
            this.audioContext.createGain()
        ];

        // Connect track gains to master
        this.trackGains.forEach(gain => {
            gain.connect(this.masterGain);
        });

        // Initial volumes
        this.trackGains.forEach(gain => {
            gain.gain.value = 0.5;
        });

        // Playback state
        this.stepDuration = this.calculateStepDuration(120);
        this.isRequestingAudio = false;
    }

    /**
     * Calculate step duration in seconds based on BPM
     * Assuming 4/4 time and each step is a 16th note
     */
    calculateStepDuration(bpm) {
        // bpm is beats per minute
        // 16 steps per beat = 16 steps per 4 beats
        // So 4 beats = 240ms at 120 BPM (typical)
        // One step = 240/16 = 15ms per step (wrong)
        // Actually: 60 / BPM = seconds per beat
        // For 16th notes: 4 * 60 / (BPM * 4) = 60 / (BPM * 4)
        const secondsPerBeat = 60 / bpm;
        const stepDuration = secondsPerBeat / 4; // 16 steps per beat = 4 16th notes per beat
        return stepDuration;
    }

    /**
     * Resume audio context if suspended (required for Web Audio API)
     */
    async resumeAudioContext() {
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
    }

    /**
     * Update timeline and playback
     * Called by sequencer to trigger notes at specific steps
     */
    playStep(trackIndex, noteIndex, duration, waveform = 'square', volume = 0.5, instrument = 'synth') {
        if (noteIndex === null || noteIndex === undefined) return;

        const trackGain = this.trackGains[trackIndex];
        const finalVolume = volume * appState.tracks[trackIndex].volume * appState.masterVolume;

        if (instrument === 'drums') {
            this.playDrum(trackGain, noteIndex, duration, finalVolume);
            return;
        }

        const synth = this.synths[trackIndex];
        const oscillator = this.audioContext.createOscillator();
        const gain = this.audioContext.createGain();

        oscillator.type = waveform;
        oscillator.frequency.value = synth.getFrequency(noteIndex);
        gain.gain.value = finalVolume;

        const now = this.audioContext.currentTime;
        const attackTime = 0.01;
        const decayTime = 0.1;
        const sustainLevel = 0.7;
        const releaseTime = 0.1;

        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(finalVolume, now + attackTime);
        gain.gain.linearRampToValueAtTime(finalVolume * sustainLevel, now + attackTime + decayTime);

        const cutoffTime = now + duration - releaseTime;
        gain.gain.setValueAtTime(finalVolume * sustainLevel, cutoffTime);
        gain.gain.linearRampToValueAtTime(0, cutoffTime + releaseTime);

        oscillator.connect(gain);
        gain.connect(trackGain);

        const stopTime = now + duration;
        oscillator.start(now);
        oscillator.stop(stopTime);
    }

    playDrum(trackGain, noteIndex, duration, volume) {
        const now = this.audioContext.currentTime;
        const drumType = noteIndex;

        const createNoiseSource = () => {
            const bufferSource = this.audioContext.createBufferSource();
            bufferSource.buffer = this.noiseBuffer || (this.noiseBuffer = this.createNoiseBuffer());
            bufferSource.loop = false;
            return bufferSource;
        };

        const createEnvelopedGain = (attack = 0.001, release = duration * 0.6) => {
            const gain = this.audioContext.createGain();
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(volume, now + attack);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + release);
            return gain;
        };

        const makeNoise = (filterType, frequency, q = 1, localVolume = 1) => {
            const noise = createNoiseSource();
            const filter = this.audioContext.createBiquadFilter();
            filter.type = filterType;
            filter.frequency.value = frequency;
            filter.Q.value = q;
            const gainNode = createEnvelopedGain(0.001, duration * 0.8);
            gainNode.gain.setValueAtTime(0.0001, now);
            gainNode.gain.exponentialRampToValueAtTime(volume * localVolume, now + 0.008);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, now + duration);
            noise.connect(filter);
            filter.connect(gainNode);
            gainNode.connect(trackGain);
            noise.start(now);
            noise.stop(now + duration);
        };

        const makeKick = () => {
            const osc = this.audioContext.createOscillator();
            const gainNode = createEnvelopedGain(0.001, duration * 0.75);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(160, now);
            osc.frequency.exponentialRampToValueAtTime(40, now + duration * 0.8);
            osc.connect(gainNode);
            gainNode.connect(trackGain);
            osc.start(now);
            osc.stop(now + duration);
        };

        switch (drumType) {
            case 0:
                makeKick();
                break;
            case 1:
                makeNoise('bandpass', 1800, 1.5, 0.9);
                break;
            case 2:
                makeNoise('highpass', 8000, 1, 0.6);
                break;
            case 3:
                makeNoise('bandpass', 1200, 2, 0.8);
                break;
            case 4:
                makeNoise('bandpass', 900, 1.2, 0.7);
                break;
            case 5:
                makeNoise('bandpass', 1200, 5, 0.5);
                break;
            case 6:
                makeNoise('highpass', 4000, 0.8, 0.55);
                break;
            case 7:
                makeNoise('highpass', 7000, 0.8, 0.5);
                break;
            case 8:
                makeKick();
                break;
            case 9:
                makeNoise('bandpass', 600, 1.2, 0.6);
                break;
            case 10:
                makeNoise('highpass', 9000, 1.1, 0.65);
                break;
            case 11:
                makeNoise('highpass', 5000, 0.9, 1);
                break;
            default:
                makeNoise('bandpass', 1500, 1, 0.6);
        }
    }

    createNoiseBuffer() {
        const sampleRate = this.audioContext.sampleRate;
        const buffer = this.audioContext.createBuffer(1, sampleRate * 1, sampleRate);
        const output = buffer.getChannelData(0);
        for (let i = 0; i < output.length; i++) {
            output[i] = (Math.random() * 2 - 1) * 0.4;
        }
        return buffer;
    }

    /**
     * Set BPM and recalculate step duration
     */
    setBPM(bpm) {
        this.stepDuration = this.calculateStepDuration(bpm);
    }

    /**
     * Set master volume (0-1)
     */
    setMasterVolume(volume) {
        this.masterVolume = volume;
        this.masterGain.gain.value = Math.max(0, Math.min(1, volume));
    }

    /**
     * Set track volume (0-1)
     */
    setTrackVolume(trackIndex, volume) {
        if (trackIndex >= 0 && trackIndex < 3) {
            this.trackGains[trackIndex].gain.value = Math.max(0, Math.min(1, volume));
        }
    }

    /**
     * Stop all audio immediately
     */
    stopAll() {
        this.synths.forEach(synth => synth.stopAll());
    }

    /**
     * Get real-time audio analysis data (for visualization)
     */
    getAudioData() {
        // This could be enhanced to return frequency data, RMS level, etc.
        // For now, return playing notes count
        return {
            playingNotesCount: this.synths.reduce((sum, synth) => sum + synth.getPlayingNotes().length, 0)
        };
    }
}

// Create global audio engine instance
const audioEngine = new AudioEngine();
