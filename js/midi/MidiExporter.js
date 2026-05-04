/**
 * MidiExporter.js - Export sequencer patterns to standard MIDI files (.mid)
 * Implements simplified MIDI file format generation
 */
class MidiExporter {
    constructor() {
        // MIDI file format constants
        this.HEADER_CHUNK_TYPE = 'MThd';
        this.HEADER_LENGTH = 6;
        this.TRACK_CHUNK_TYPE = 'MTrk';
        this.TICKS_PER_QUARTER = 480;
        this.TEMPO_MICROSECONDS = 500000; // 120 BPM = 500000 microseconds per quarter note
    }

    /**
     * Export sequencer state to MIDI file
     * Returns Blob object that can be downloaded
     */
    export(state = appState) {
        const buffer = this.createMidiBuffer(state);
        return new Blob([buffer], { type: 'audio/midi' });
    }

    /**
     * Create MIDI file buffer from state
     */
    createMidiBuffer(state) {
        const parts = [];

        // Add header
        parts.push(this.createHeaderChunk());

        // Add track for each non-empty track
        state.tracks.forEach((track, trackIndex) => {
            if (track.notes.some(note => note !== null)) {
                parts.push(this.createTrackChunk(track, state.bpm));
            }
        });

        // Concatenate all parts
        return this.concatenateBuffers(parts);
    }

    /**
     * Create MIDI header chunk
     */
    createHeaderChunk() {
        const data = new ArrayBuffer(14);
        const view = new Uint8Array(data);

        // Chunk type: "MThd"
        view[0] = 0x4D; // M
        view[1] = 0x54; // T
        view[2] = 0x68; // h
        view[3] = 0x64; // d

        // Chunk length (always 6 for header)
        view[4] = 0x00;
        view[5] = 0x00;
        view[6] = 0x00;
        view[7] = 0x06;

        // Format type: 0 (single track) or 1 (multiple tracks)
        view[8] = 0x00;
        view[9] = 0x01; // Format type 1

        // Number of tracks (will be updated if needed)
        view[10] = 0x00;
        view[11] = 0x01; // 1 track initially

        // Division (ticks per quarter note)
        view[12] = (this.TICKS_PER_QUARTER >> 8) & 0xFF;
        view[13] = this.TICKS_PER_QUARTER & 0xFF;

        return data;
    }

    /**
     * Create MIDI track chunk
     */
    createTrackChunk(track, bpm) {
        const events = [];

        // Add tempo meta event
        events.push(this.createTempoMetaEvent(bpm));

        // Add notes from pattern
        const stepDuration = this.TICKS_PER_QUARTER; // 480 ticks per step in 16-step pattern
        let currentTick = 0;

        track.notes.forEach((noteIndex, step) => {
            if (noteIndex !== null) {
                const midiNote = 60 + noteIndex; // C4 = 60

                // Note On
                events.push({
                    tick: currentTick,
                    data: this.createNoteOnEvent(midiNote, 100)
                });

                // Note Off (quarter note duration = step duration)
                const noteDuration = stepDuration * 0.75; // Make notes 75% of step length
                events.push({
                    tick: currentTick + noteDuration,
                    data: this.createNoteOffEvent(midiNote)
                });
            }

            currentTick += stepDuration;
        });

        // Add end of track meta event
        const finalTick = currentTick;
        events.push({
            tick: finalTick,
            data: this.createEndOfTrackEvent()
        });

        // Sort by tick
        events.sort((a, b) => a.tick - b.tick);

        // Convert to variable length quantities and delta times
        const trackData = this.eventsToTrackData(events);

        // Create track chunk
        const chunkHeader = new ArrayBuffer(8);
        const headerView = new Uint8Array(chunkHeader);

        // Chunk type: "MTrk"
        headerView[0] = 0x4D; // M
        headerView[1] = 0x54; // T
        headerView[2] = 0x72; // r
        headerView[3] = 0x6B; // k

        // Chunk length
        const length = trackData.byteLength;
        headerView[4] = (length >> 24) & 0xFF;
        headerView[5] = (length >> 16) & 0xFF;
        headerView[6] = (length >> 8) & 0xFF;
        headerView[7] = length & 0xFF;

        // Combine header and track data
        const result = new ArrayBuffer(chunkHeader.byteLength + trackData.byteLength);
        const resultView = new Uint8Array(result);
        resultView.set(new Uint8Array(chunkHeader), 0);
        resultView.set(new Uint8Array(trackData), chunkHeader.byteLength);

        return result;
    }

    /**
     * Create tempo meta event
     */
    createTempoMetaEvent(bpm) {
        // Convert BPM to microseconds per quarter note
        const microseconds = Math.round(60000000 / bpm);

        const data = new Uint8Array(7);
        data[0] = 0xFF; // Meta event
        data[1] = 0x51; // Tempo
        data[2] = 0x03; // Length
        data[3] = (microseconds >> 16) & 0xFF;
        data[4] = (microseconds >> 8) & 0xFF;
        data[5] = microseconds & 0xFF;

        return { data: data.buffer, tick: 0 };
    }

    /**
     * Create Note On event
     */
    createNoteOnEvent(note, velocity) {
        const data = new Uint8Array(3);
        data[0] = 0x90; // Note On, channel 0
        data[1] = note & 0x7F;
        data[2] = velocity & 0x7F;

        return data.buffer;
    }

    /**
     * Create Note Off event
     */
    createNoteOffEvent(note) {
        const data = new Uint8Array(3);
        data[0] = 0x80; // Note Off, channel 0
        data[1] = note & 0x7F;
        data[2] = 64; // Default velocity

        return data.buffer;
    }

    /**
     * Create End of Track meta event
     */
    createEndOfTrackEvent() {
        const data = new Uint8Array(3);
        data[0] = 0xFF; // Meta event
        data[1] = 0x2F; // End of Track
        data[2] = 0x00; // Length

        return data.buffer;
    }

    /**
     * Convert events (with absolute ticks) to track data with delta times
     */
    eventsToTrackData(events) {
        const data = [];
        let previousTick = 0;

        events.forEach(event => {
            // Calculate delta time
            const deltaTime = event.tick - previousTick;
            const deltaBytes = this.encodeVariableLength(deltaTime);

            // Add delta time
            data.push(...deltaBytes);

            // Add event data
            data.push(...new Uint8Array(event.data));

            previousTick = event.tick;
        });

        return new Uint8Array(data).buffer;
    }

    /**
     * Encode value as MIDI variable length quantity
     */
    encodeVariableLength(value) {
        const result = [];
        let buffer = value & 0x7F;

        while ((value >>= 7) > 0) {
            result.unshift(buffer | 0x80);
            buffer = value & 0x7F;
        }

        result.push(buffer);
        return result;
    }

    /**
     * Concatenate multiple ArrayBuffers
     */
    concatenateBuffers(buffers) {
        const totalLength = buffers.reduce((sum, buf) => sum + buf.byteLength, 0);
        const result = new Uint8Array(totalLength);

        let offset = 0;
        buffers.forEach(buf => {
            result.set(new Uint8Array(buf), offset);
            offset += buf.byteLength;
        });

        return result.buffer;
    }

    /**
     * Download MIDI file
     */
    download(blob, filename = 'pattern.mid') {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Export and download
     */
    exportAndDownload(state = appState, filename = 'sequencer_pattern.mid') {
        const blob = this.export(state);
        this.download(blob, filename);
    }
}

// Create global MIDI exporter instance
const midiExporter = new MidiExporter();
