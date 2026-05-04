/**
 * main.js - Application initialization and setup
 * Entry point for the web sequencer
 */

// Global namespace for application
const App = {
    version: '1.0.0',
    name: 'Web Sequencer',

    /**
     * Initialize application
     */
    init() {
        console.log(`Initializing ${this.name} v${this.version}`);

        // Initialize modules (order matters)
        this.initAudio();
        this.initState();
        this.initSequencer();
        this.initUI();

        console.log('Application initialized successfully');
        console.log('Usage: SPACE to play/stop, DELETE to clear step, 1-3 to select track');
        console.log('Arrow keys to navigate, CTRL+C to clear track');
    },

    /**
     * Initialize audio engine
     */
    initAudio() {
        // Audio engine is created globally in AudioEngine.js
        console.log('✓ Audio Engine initialized');
        console.log('  - 3 oscillator channels ready');
        console.log('  - Master volume:', audioEngine.masterGain.gain.value);
    },

    /**
     * Initialize application state
     */
    initState() {
        // State is created globally in State.js
        console.log('✓ State Management initialized');
        console.log('  - 3 tracks with 16 steps each');
        console.log('  - Default BPM:', appState.bpm);
        console.log('  - Default waveform:', appState.waveform);
    },

    /**
     * Initialize sequencer
     */
    initSequencer() {
        // Sequencer is created globally in Sequencer.js
        console.log('✓ Sequencer initialized');
        console.log('  - Step duration:', audioEngine.stepDuration, 'seconds');
        console.log('  - Playback ready');
    },

    /**
     * Initialize UI and controls
     */
    initUI() {
        // UI will be initialized by Controls.js when DOM is ready
        // PianoRoll is also initialized when DOM is ready
        console.log('✓ UI initialized');
        console.log('  - Piano Roll ready');
        console.log('  - Controls prepared');

        // Display welcome message
        this.showWelcomeMessage();
    },

    /**
     * Show welcome message to console
     */
    showWelcomeMessage() {
        const style = 'color: #00ff00; font-weight: bold; text-shadow: 0 0 10px #00ff00;';
        console.log('%c🎵 Web Sequencer Ready!', style);
        console.log('%cTips:', style);
        console.log('  • Click on the grid to place notes');
        console.log('  • Press SPACE to play/stop');
        console.log('  • Use 1-2-3 keys to switch tracks');
        console.log('  • Select MIDI output to send notes to external synthesizer');
        console.log('  • Export patterns to standard MIDI files');
    },

    /**
     * Save pattern to local storage
     */
    savePattern(name = 'default') {
        try {
            const jsonData = appState.export();
            localStorage.setItem(`sequencer_pattern_${name}`, jsonData);
            console.log(`Pattern "${name}" saved`);
            return true;
        } catch (error) {
            console.error('Failed to save pattern:', error);
            return false;
        }
    },

    /**
     * Load pattern from local storage
     */
    loadPattern(name = 'default') {
        try {
            const jsonData = localStorage.getItem(`sequencer_pattern_${name}`);
            if (jsonData) {
                appState.import(jsonData);
                console.log(`Pattern "${name}" loaded`);
                return true;
            } else {
                console.log(`Pattern "${name}" not found`);
                return false;
            }
        } catch (error) {
            console.error('Failed to load pattern:', error);
            return false;
        }
    },

    /**
     * List saved patterns
     */
    listPatterns() {
        const patterns = [];
        for (let key in localStorage) {
            if (key.startsWith('sequencer_pattern_')) {
                patterns.push(key.replace('sequencer_pattern_', ''));
            }
        }
        console.log('Saved patterns:', patterns.length ? patterns : 'None');
        return patterns;
    },

    /**
     * Export current pattern as JSON
     */
    exportJSON() {
        const data = appState.export();
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'sequencer_pattern.json';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    },

    /**
     * Import pattern from JSON file
     */
    importJSON(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const jsonData = e.target.result;
                if (appState.import(jsonData)) {
                    console.log('Pattern imported successfully');
                    if (uiControls) {
                        uiControls.updateDisplays();
                    }
                }
            } catch (error) {
                console.error('Failed to import pattern:', error);
            }
        };
        reader.readAsText(file);
    },

    /**
     * Get application statistics
     */
    getStats() {
        const noteCount = appState.tracks.reduce((sum, track) => {
            return sum + track.notes.filter(n => n !== null).length;
        }, 0);

        return {
            version: this.version,
            bpm: appState.bpm,
            tracks: appState.tracks.length,
            stepsPerTrack: 16,
            totalNotes: noteCount,
            isPlaying: appState.isPlaying,
            currentStep: appState.currentStep + 1
        };
    }
};

/**
 * Expose debugging functions to console
 */
window.Sequencer = {
    play: () => sequencer.play(),
    stop: () => sequencer.stop(),
    togglePlay: () => sequencer.togglePlayback(),
    setBPM: (bpm) => sequencer.setBPM(bpm),
    setWaveform: (waveform) => sequencer.setWaveform(waveform),
    clearAll: () => sequencer.clearAll(),
    exportMIDI: () => midiExporter.exportAndDownload(),
    exportJSON: () => App.exportJSON(),
    savePattern: (name) => App.savePattern(name),
    loadPattern: (name) => App.loadPattern(name),
    listPatterns: () => App.listPatterns(),
    getStats: () => App.getStats(),
    getState: () => appState,
    getAudioEngine: () => audioEngine,
    getSequencer: () => sequencer,
    getMidiManager: () => midiManager
};

// Initialize application when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        App.init();
    });
} else {
    App.init();
}

// Also expose for testing
window.App = App;
