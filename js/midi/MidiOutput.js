/**
 * MidiOutput.js - Web MIDI API implementation
 * Handles MIDI device discovery and note output
 */
class MidiOutputManager {
    constructor() {
        this.midiAccess = null;
        this.midiOutputs = new Map();
        this.selectedOutput = null;
        this.isSupported = navigator.requestMIDIAccess !== undefined;
        this.noteOnMessages = new Map(); // Track which MIDI notes are active

        if (this.isSupported) {
            this.initialize();
        } else {
            console.warn('Web MIDI API not supported in this browser');
        }
    }

    /**
     * Initialize MIDI access
     */
    async initialize() {
        try {
            this.midiAccess = await navigator.requestMIDIAccess();
            this.enumerateOutputs();
            this.setupMidiInputListeners();
        } catch (error) {
            console.error('MIDI Access failed:', error);
        }
    }

    /**
     * Enumerate all MIDI outputs
     */
    enumerateOutputs() {
        this.midiOutputs.clear();

        if (!this.midiAccess) return;

        const outputs = this.midiAccess.outputs.values();
        for (let output of outputs) {
            this.midiOutputs.set(output.id, {
                id: output.id,
                name: output.name,
                manufacturer: output.manufacturer,
                state: output.state,
                connection: output.connection,
                port: output
            });
        }

        console.log('MIDI Outputs found:', this.midiOutputs.size);
    }

    /**
     * Setup listeners for MIDI device changes
     */
    setupMidiInputListeners() {
        if (!this.midiAccess) return;

        this.midiAccess.addEventListener('statechange', (event) => {
            console.log('MIDI device state changed:', event.port.name);
            this.enumerateOutputs();
        });
    }

    /**
     * Get list of available MIDI outputs
     */
    getOutputs() {
        return Array.from(this.midiOutputs.values());
    }

    /**
     * Select a MIDI output device
     */
    selectOutput(deviceId) {
        const output = this.midiOutputs.get(deviceId);
        if (output) {
            this.selectedOutput = output;
            console.log('Selected MIDI output:', output.name);
            return true;
        }
        return false;
    }

    /**
     * Get currently selected output
     */
    getSelectedOutput() {
        return this.selectedOutput;
    }

    /**
     * Send MIDI Note On message
     * noteIndex: 0-11 (C4 to G5) → MIDI note 60-71
     * velocity: 1-127
     * channel: 0-15 (0 = channel 1)
     */
    noteOn(noteIndex, velocity = 100, channel = 0) {
        if (!this.selectedOutput || noteIndex === null || noteIndex === undefined) {
            return false;
        }

        try {
            // Convert note index to MIDI note number (C4 = 60)
            const midiNote = 60 + noteIndex;

            // Create MIDI Note On message
            const noteOnMessage = [
                0x90 + channel,  // Note On, channel
                midiNote,        // Note
                velocity         // Velocity
            ];

            // Store active note
            const key = `${channel}_${noteIndex}`;
            this.noteOnMessages.set(key, midiNote);

            // Send message
            this.selectedOutput.port.send(noteOnMessage);
            return true;
        } catch (error) {
            console.error('MIDI Note On failed:', error);
            return false;
        }
    }

    /**
     * Send MIDI Note Off message
     */
    noteOff(noteIndex, velocity = 64, channel = 0) {
        if (!this.selectedOutput || noteIndex === null || noteIndex === undefined) {
            return false;
        }

        try {
            // Convert note index to MIDI note number
            const midiNote = 60 + noteIndex;

            // Create MIDI Note Off message
            const noteOffMessage = [
                0x80 + channel,  // Note Off, channel
                midiNote,        // Note
                velocity         // Velocity
            ];

            // Remove from active notes
            const key = `${channel}_${noteIndex}`;
            this.noteOnMessages.delete(key);

            // Send message
            this.selectedOutput.port.send(noteOffMessage);
            return true;
        } catch (error) {
            console.error('MIDI Note Off failed:', error);
            return false;
        }
    }

    /**
     * Send MIDI Control Change
     */
    controlChange(controller, value, channel = 0) {
        if (!this.selectedOutput) return false;

        try {
            const ccMessage = [
                0xB0 + channel,  // Control Change, channel
                controller,      // CC number
                value           // Value (0-127)
            ];
            this.selectedOutput.port.send(ccMessage);
            return true;
        } catch (error) {
            console.error('MIDI CC failed:', error);
            return false;
        }
    }

    /**
     * Send MIDI Program Change
     */
    programChange(program, channel = 0) {
        if (!this.selectedOutput) return false;

        try {
            const pcMessage = [
                0xC0 + channel,  // Program Change, channel
                program          // Program number 0-127
            ];
            this.selectedOutput.port.send(pcMessage);
            return true;
        } catch (error) {
            console.error('MIDI PC failed:', error);
            return false;
        }
    }

    /**
     * Stop all active MIDI notes
     */
    allNotesOff(channel = 0) {
        const keysToRemove = Array.from(this.noteOnMessages.keys())
            .filter(key => key.startsWith(`${channel}_`));

        keysToRemove.forEach(key => {
            const noteIndex = parseInt(key.split('_')[1]);
            this.noteOff(noteIndex, 64, channel);
        });
    }

    /**
     * Check if MIDI is available and enabled
     */
    isEnabled() {
        return this.isSupported && this.selectedOutput !== null;
    }

    /**
     * Get number of active MIDI notes
     */
    getActiveNoteCount() {
        return this.noteOnMessages.size;
    }
}

// Create global MIDI manager instance
const midiManager = new MidiOutputManager();
