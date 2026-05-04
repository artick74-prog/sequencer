/**
 * PianoRoll.js - Canvas-based piano roll visualization and interaction
 * Renders notes grid, handles mouse input for placing notes
 */
class PianoRoll {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = this.canvas.getContext('2d');

        // Dimensions
        this.noteCount = 12; // C4 to G5
        this.stepCount = 16;
        this.cellWidth = 0;
        this.cellHeight = 0;

        // Interaction
        this.selectedStep = null;
        this.selectedNote = null;
        this.isDragging = false;
        this.dragMode = null; // 'draw' or 'erase'

        // Colors (match CSS)
        this.colors = {
            background: '#1a1a1a',
            gridLine: '#333333',
            cellBorder: '#4a4a4a',
            cellDefault: '#2a2a2a',
            cellActive: '#00ff00',
            cellBeat: '#4a6a4a',
            cellPlayhead: '#ff0000',
            cellHover: '#3a5a3a',
            track1: 'rgba(0, 136, 255, 0.3)',
            track2: 'rgba(255, 0, 255, 0.3)',
            track3: 'rgba(255, 255, 0, 0.3)'
        };

        // Selected track color
        this.trackColors = [this.colors.track1, this.colors.track2, this.colors.track3];

        // Setup canvas
        this.resizeCanvas();
        this.setupEventListeners();

        // Subscribe to state changes
        appState.subscribe('stateChange', () => this.render());
        appState.subscribe('stepChange', () => this.render());
        appState.subscribe('trackChange', () => this.render());

        // Initial render
        this.render();
    }

    /**
     * Resize canvas to fit container
     */
    resizeCanvas() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;

        // Calculate cell dimensions
        this.cellWidth = this.canvas.width / this.stepCount;
        this.cellHeight = this.canvas.height / this.noteCount;
    }

    /**
     * Setup event listeners for mouse interactions
     */
    setupEventListeners() {
        window.addEventListener('resize', () => {
            this.resizeCanvas();
            this.render();
        });

        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseLeave(e));
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
    }

    /**
     * Get cell at mouse position
     */
    getCellFromMouse(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const step = Math.floor(x / this.cellWidth);
        const note = Math.floor(y / this.cellHeight);

        if (step >= 0 && step < this.stepCount && note >= 0 && note < this.noteCount) {
            return { step, note };
        }

        return null;
    }

    /**
     * Handle mouse down
     */
    onMouseDown(e) {
        const cell = this.getCellFromMouse(e);
        if (!cell) return;

        this.isDragging = true;
        const selectedTrack = appState.selectedTrack;
        const currentNote = appState.getNote(selectedTrack, cell.step);

        // Determine drag mode
        if (e.button === 0) { // Left click - draw
            this.dragMode = currentNote === cell.note ? 'erase' : 'draw';
        } else if (e.button === 2) { // Right click - erase
            this.dragMode = 'erase';
        }

        this.toggleNote(cell.step, cell.note);
    }

    /**
     * Handle mouse move
     */
    onMouseMove(e) {
        const cell = this.getCellFromMouse(e);

        if (cell) {
            this.selectedStep = cell.step;
            this.selectedNote = cell.note;

            // Draw if dragging
            if (this.isDragging && this.dragMode) {
                const selectedTrack = appState.selectedTrack;
                const currentNote = appState.getNote(selectedTrack, cell.step);

                if (this.dragMode === 'draw' && currentNote !== cell.note) {
                    appState.setNote(selectedTrack, cell.step, cell.note);
                } else if (this.dragMode === 'erase' && currentNote === cell.note) {
                    appState.setNote(selectedTrack, cell.step, null);
                }
            }
        } else {
            this.selectedStep = null;
            this.selectedNote = null;
        }

        this.render();
    }

    /**
     * Handle mouse up
     */
    onMouseUp(e) {
        this.isDragging = false;
        this.dragMode = null;
    }

    /**
     * Handle mouse leave
     */
    onMouseLeave(e) {
        this.selectedStep = null;
        this.selectedNote = null;
        this.isDragging = false;
        this.dragMode = null;
        this.render();
    }

    /**
     * Toggle note at step and note
     */
    toggleNote(step, note) {
        const selectedTrack = appState.selectedTrack;
        appState.toggleNote(selectedTrack, step, note);
    }

    /**
     * Render the piano roll
     */
    render() {
        // Clear canvas
        this.ctx.fillStyle = this.colors.background;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid
        this.drawGrid();

        // Draw notes for selected track
        this.drawNotes();

        // Draw current playback step indicator
        if (appState.isPlaying) {
            this.drawPlayhead();
        }

        // Draw hover highlight
        if (this.selectedStep !== null && this.selectedNote !== null) {
            this.drawHover();
        }
    }

    /**
     * Draw grid lines
     */
    drawGrid() {
        this.ctx.strokeStyle = this.colors.gridLine;
        this.ctx.lineWidth = 1;

        // Vertical lines (steps) - emphasize beat divisions
        for (let step = 0; step <= this.stepCount; step++) {
            const x = step * this.cellWidth;
            this.ctx.strokeStyle = (step % 4 === 0) ? this.colors.cellBorder : this.colors.gridLine;
            this.ctx.lineWidth = (step % 4 === 0) ? 2 : 1;
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }

        // Horizontal lines (notes)
        for (let note = 0; note <= this.noteCount; note++) {
            const y = note * this.cellHeight;
            this.ctx.strokeStyle = this.colors.gridLine;
            this.ctx.lineWidth = 1;
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    /**
     * Draw notes for selected track
     */
    drawNotes() {
        const selectedTrack = appState.selectedTrack;
        const track = appState.tracks[selectedTrack];

        track.notes.forEach((noteIndex, step) => {
            if (noteIndex !== null) {
                const x = step * this.cellWidth;
                const y = noteIndex * this.cellHeight;

                // Draw note cell
                this.ctx.fillStyle = this.colors.cellActive;
                this.ctx.fillRect(x + 1, y + 1, this.cellWidth - 2, this.cellHeight - 2);

                // Add border with glow effect
                this.ctx.strokeStyle = '#00ff00';
                this.ctx.lineWidth = 2;
                this.ctx.strokeRect(x + 1, y + 1, this.cellWidth - 2, this.cellHeight - 2);

                // Glow effect
                this.ctx.shadowColor = '#00ff00';
                this.ctx.shadowBlur = 10;
                this.ctx.strokeRect(x + 1, y + 1, this.cellWidth - 2, this.cellHeight - 2);
                this.ctx.shadowBlur = 0;
            }
        });
    }

    /**
     * Draw playback position indicator
     */
    drawPlayhead() {
        const step = appState.currentStep;
        const x = step * this.cellWidth;

        // Draw vertical line
        this.ctx.strokeStyle = this.colors.cellPlayhead;
        this.ctx.lineWidth = 3;
        this.ctx.globalAlpha = 0.8;
        this.ctx.beginPath();
        this.ctx.moveTo(x, 0);
        this.ctx.lineTo(x, this.canvas.height);
        this.ctx.stroke();
        this.ctx.globalAlpha = 1.0;

        // Draw highlight on all notes in current step
        appState.tracks[appState.selectedTrack].notes.forEach((noteIndex, stepIndex) => {
            if (stepIndex === step && noteIndex !== null) {
                const cellX = step * this.cellWidth;
                const cellY = noteIndex * this.cellHeight;
                this.ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
                this.ctx.fillRect(cellX + 1, cellY + 1, this.cellWidth - 2, this.cellHeight - 2);
            }
        });
    }

    /**
     * Draw hover highlight
     */
    drawHover() {
        const x = this.selectedStep * this.cellWidth;
        const y = this.selectedNote * this.cellHeight;

        this.ctx.fillStyle = this.colors.cellHover;
        this.ctx.fillRect(x + 1, y + 1, this.cellWidth - 2, this.cellHeight - 2);
    }

    /**
     * Get note name at position for tooltip
     */
    getNoteNameAtPosition(step, note) {
        return new SimpleSynth(null).getNoteName(note);
    }
}

// Create global piano roll instance
let pianoRoll = null;

// Initialize when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
    const pianoRollCanvas = document.getElementById('pianoRoll');
    if (pianoRollCanvas) {
        pianoRoll = new PianoRoll(pianoRollCanvas);
    }
});
