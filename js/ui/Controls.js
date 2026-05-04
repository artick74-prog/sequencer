/**
 * Controls.js - UI control handlers
 * Manages buttons, sliders, dropdowns and keyboard shortcuts
 */
class UIControls {
    constructor() {
        this.elements = {};
        this.cacheElements();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.updateMidiDevicesList();
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            // Buttons
            playBtn: document.getElementById('playBtn'),
            stopBtn: document.getElementById('stopBtn'),
            clearBtn: document.getElementById('clearBtn'),
            midiExportBtn: document.getElementById('midiExportBtn'),

            // Sliders
            tempoSlider: document.getElementById('tempoSlider'),
            volumeSlider: document.getElementById('volumeSlider'),
            trackVolume: document.getElementById('trackVolume'),

            // Selects
            waveformSelect: document.getElementById('waveformSelect'),
            instrumentButtons: document.querySelectorAll('.instrument-btn'),
            midiOutput: document.getElementById('midiOutput'),

            // Info displays
            currentBPM: document.getElementById('currentBPM'),
            currentStep: document.getElementById('currentStep'),
            tempoValue: document.getElementById('tempoValue'),
            volumeValue: document.getElementById('volumeValue'),

            // Track selection
            trackBtns: document.querySelectorAll('.track-btn'),
            selectedInstrument: document.getElementById('selectedInstrument'),

            // Note labels
            noteLabels: document.querySelectorAll('.note-label')
        };
    }

    /**
     * Setup event listeners for all controls
     */
    setupEventListeners() {
        // Play/Stop
        this.elements.playBtn?.addEventListener('click', () => {
            sequencer.togglePlayback();
            this.updatePlayStopButtons();
        });

        this.elements.stopBtn?.addEventListener('click', () => {
            sequencer.stop();
            this.updatePlayStopButtons();
        });

        // Clear
        this.elements.clearBtn?.addEventListener('click', () => {
            if (confirm('Clear all patterns? This cannot be undone.')) {
                sequencer.clearAll();
            }
        });

        // Tempo
        this.elements.tempoSlider?.addEventListener('input', (e) => {
            const bpm = parseInt(e.target.value);
            sequencer.setBPM(bpm);
            this.elements.tempoValue.textContent = bpm;
            this.elements.currentBPM.textContent = `${bpm} BPM`;
        });

        // Volume
        this.elements.volumeSlider?.addEventListener('input', (e) => {
            const volume = parseFloat(e.target.value);
            appState.setMasterVolume(volume);
            audioEngine.setMasterVolume(volume);
            this.elements.volumeValue.textContent = Math.round(volume * 100) + '%';
        });

        // Waveform
        this.elements.waveformSelect?.addEventListener('change', (e) => {
            sequencer.setWaveform(e.target.value);
        });

        // Instrument selection buttons
        this.elements.instrumentButtons?.forEach(button => {
            button.addEventListener('click', (e) => {
                const instrument = e.target.dataset.instrument;
                const trackIndex = appState.selectedTrack;
                appState.setInstrument(trackIndex, instrument);
                this.updateInstrumentButtons(instrument);
                this.toggleInstrumentUI(trackIndex);
                this.updateInstrumentLabels();
            });
        });

        // Track Volume
        this.elements.trackVolume?.addEventListener('input', (e) => {
            const volume = parseFloat(e.target.value);
            const trackIndex = appState.selectedTrack;
            appState.setTrackVolume(trackIndex, volume);
            audioEngine.setTrackVolume(trackIndex, volume);
        });

        // Track Selection
        this.elements.trackBtns?.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const trackIndex = parseInt(e.target.dataset.track);
                appState.selectTrack(trackIndex);
                this.updateTrackSelection();
                this.updateTrackVolume();
            });
        });

        // MIDI Output Selection
        this.elements.midiOutput?.addEventListener('change', (e) => {
            const selectedId = e.target.value;
            if (selectedId) {
                midiManager.selectOutput(selectedId);
                appState.setMidiOutput(selectedId);
                sequencer.setMidiEnabled(true);
            } else {
                appState.setMidiOutput(null);
                sequencer.setMidiEnabled(false);
            }
        });

        // MIDI Export
        this.elements.midiExportBtn?.addEventListener('click', () => {
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            midiExporter.exportAndDownload(appState, `sequencer_${timestamp}.mid`);
            console.log('MIDI exported');
        });

        // Subscribe to state changes
        appState.subscribe('stateChange', () => this.updateDisplays());
        appState.subscribe('stepChange', () => this.updateStepDisplay());
        appState.subscribe('trackChange', () => {
            this.updateTrackSelection();
            this.updateTrackVolume();
            this.updateInstrumentLabels();
            this.toggleInstrumentUI(appState.selectedTrack);
        });
        appState.subscribe('playStateChange', () => this.updatePlayStopButtons());

        // Initialize UI from state
        this.updateTrackSelection();
        this.updateTrackVolume();
        this.updateInstrumentLabels();
        this.toggleInstrumentUI(appState.selectedTrack);
        if (this.elements.selectedInstrument) {
            const instrument = appState.tracks[appState.selectedTrack].instrument || 'synth';
            this.elements.selectedInstrument.textContent = instrument === 'drums' ? 'Drums' : 'Synth';
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Space: Play/Stop
            if (e.code === 'Space') {
                e.preventDefault();
                sequencer.togglePlayback();
                this.updatePlayStopButtons();
            }

            // Delete: Clear current step in selected track
            if (e.code === 'Delete' || e.code === 'Backspace') {
                e.preventDefault();
                const currentStep = appState.currentStep;
                const trackIndex = appState.selectedTrack;
                appState.setNote(trackIndex, currentStep, null);
            }

            // Numbers 1-3: Select track
            if (e.code.startsWith('Digit') && !e.ctrlKey && !e.metaKey) {
                const number = parseInt(e.code.replace('Digit', ''));
                if (number >= 1 && number <= 3) {
                    appState.selectTrack(number - 1);
                    this.updateTrackSelection();
                }
            }

            // Arrow keys: Navigate steps
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                const newStep = (appState.currentStep - 1 + 16) % 16;
                appState.setCurrentStep(newStep);
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                const newStep = (appState.currentStep + 1) % 16;
                appState.setCurrentStep(newStep);
            }

            // Arrow up/down: Change note (if not playing - for safety)
            if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && !appState.isPlaying) {
                e.preventDefault();
                const currentStep = appState.currentStep;
                const trackIndex = appState.selectedTrack;
                const currentNote = appState.getNote(trackIndex, currentStep);

                if (currentNote !== null) {
                    const newNote = e.key === 'ArrowUp'
                        ? Math.min(11, currentNote + 1)
                        : Math.max(0, currentNote - 1);
                    appState.setNote(trackIndex, currentStep, newNote);
                }
            }

            // C: Clear selected track
            if (e.code === 'KeyC' && e.ctrlKey) {
                e.preventDefault();
                const trackIndex = appState.selectedTrack;
                appState.clearTrack(trackIndex);
            }
        });
    }

    /**
     * Update MIDI devices list
     */
    updateMidiDevicesList() {
        // Request MIDI access if not already done
        if (!midiManager.midiAccess && midiManager.isSupported) {
            midiManager.initialize().then(() => {
                this.populateMidiOutputs();
            });
        } else {
            this.populateMidiOutputs();
        }
    }

    /**
     * Populate MIDI output dropdown
     */
    populateMidiOutputs() {
        if (!midiManager.isSupported) {
            this.elements.midiOutput.innerHTML = '<option value="">MIDI Not Supported</option>';
            return;
        }

        const outputs = midiManager.getOutputs();

        if (outputs.length === 0) {
            this.elements.midiOutput.innerHTML = '<option value="">No MIDI Outputs</option>';
        } else {
            let html = '<option value="">None</option>';
            outputs.forEach(output => {
                html += `<option value="${output.id}">${output.name}</option>`;
            });
            this.elements.midiOutput.innerHTML = html;
        }
    }

    /**
     * Update all displays after state change
     */
    updateDisplays() {
        this.updateStepDisplay();
        this.updateTrackSelection();
    }

    /**
     * Update step/BPM display
     */
    updateStepDisplay() {
        const step = appState.currentStep + 1;
        this.elements.currentStep.textContent = `Step: ${step}/16`;
        this.elements.currentBPM.textContent = `${appState.bpm} BPM`;
    }

    /**
     * Update track selection visualization
     */
    updateTrackSelection() {
        this.elements.trackBtns.forEach((btn, index) => {
            if (index === appState.selectedTrack) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        const trackIndex = appState.selectedTrack;
        const trackInstrument = appState.tracks[trackIndex].instrument || 'synth';
        this.updateInstrumentButtons(trackInstrument);
        if (this.elements.selectedInstrument) {
            this.elements.selectedInstrument.textContent = trackInstrument === 'drums' ? 'Drums' : 'Synth';
        }
        this.toggleInstrumentUI(trackIndex);
        this.updateInstrumentLabels();
    }

    /**
     * Update track volume slider
     */
    updateTrackVolume() {
        const trackIndex = appState.selectedTrack;
        const volume = appState.tracks[trackIndex].volume;
        this.elements.trackVolume.value = volume;
    }

    updateInstrumentButtons(activeInstrument) {
        this.elements.instrumentButtons.forEach(btn => {
            if (btn.dataset.instrument === activeInstrument) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    /**
     * Enable/disable waveform control depending on instrument type
     */
    toggleInstrumentUI(trackIndex) {
        const instrument = appState.tracks[trackIndex].instrument || 'synth';
        if (instrument === 'drums') {
            this.elements.waveformSelect.disabled = true;
            this.elements.waveformSelect.parentElement.style.opacity = '0.6';
        } else {
            this.elements.waveformSelect.disabled = false;
            this.elements.waveformSelect.parentElement.style.opacity = '1';
        }
    }

    /**
     * Update note labels for selected instrument
     */
    updateInstrumentLabels() {
        const trackIndex = appState.selectedTrack;
        const instrument = appState.tracks[trackIndex].instrument || 'synth';

        const synthLabels = ['C4','D4','E4','F4','G4','A4','B4','C5','D5','E5','F5','G5'];
        const drumLabels = ['Kick','Snare','Hi-Hat','Clap','Tom','Rim','Perc','Shaker','Low Tom','Mid Tom','Open Hat','Crash'];

        this.elements.noteLabels.forEach((label, index) => {
            label.textContent = instrument === 'drums' ? drumLabels[index] : synthLabels[index];
        });
    }

    /**
     * Update play/stop button states
     */
    updatePlayStopButtons() {
        if (appState.isPlaying) {
            this.elements.playBtn.classList.add('active');
            this.elements.stopBtn.classList.remove('active');
        } else {
            this.elements.playBtn.classList.remove('active');
            this.elements.stopBtn.classList.add('active');
        }
    }

    /**
     * Refresh MIDI outputs (call when devices change)
     */
    refreshMidiOutputs() {
        this.populateMidiOutputs();
    }
}

// Initialize controls when DOM is ready
let uiControls = null;

window.addEventListener('DOMContentLoaded', () => {
    uiControls = new UIControls();

    // Try to get MIDI access after user interaction
    document.addEventListener('click', async () => {
        if (midiManager.isSupported && !midiManager.midiAccess) {
            try {
                await midiManager.initialize();
                uiControls.populateMidiOutputs();
            } catch (e) {
                console.log('MIDI access denied or not available');
            }
        }
    }, { once: true });
});
