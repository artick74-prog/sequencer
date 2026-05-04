# 🎵 Web Sequencer - Complete Project Guide

Welcome to Web Sequencer - a modern, retro-styled music tracker built with vanilla JavaScript!

## 📚 Documentation Index

### Getting Started
1. **[QUICKSTART.md](QUICKSTART.md)** ⭐ **START HERE**
   - 30-60 second setup and basic usage
   - Keyboard shortcuts
   - First beat creation
   - MIDI setup

2. **[README.md](README.md)** - Full Documentation
   - Complete feature list
   - Project structure
   - API reference
   - Console commands
   - Advanced usage

### Additional Guides

3. **[BROWSER.md](BROWSER.md)** - Browser Compatibility
   - Supported browsers and their features
   - HTTPS requirements
   - Permission dialogs
   - Platform-specific notes (Windows, macOS, Linux, iOS, Android)
   - Troubleshooting by browser

4. **[EXTEND.md](EXTEND.md)** - Extension Guide
   - Adding more tracks
   - Expanding note range
   - Audio effects (Reverb, Delay)
   - Pattern banks and chaining
   - Arpeggiator
   - Recording
   - Visualizers
   - Performance optimization

5. **[EXAMPLES.js](EXAMPLES.js)** - Code Examples
   - Console command examples
   - Pattern creation
   - MIDI usage
   - Saving/loading patterns

## 🚀 Quick Launch

### Option 1: Direct Open
```
1. Open index.html in your browser
2. Click on the piano roll grid to place notes
3. Press SPACE to play
```

### Option 2: With Local Server (Recommended for MIDI)
```bash
# Python
python -m http.server 8000

# Node.js
npx http-server

# PHP
php -S localhost:8000

# Then visit: http://localhost:8000
```

## 📂 Project Structure

```
sequencer/
├── index.html              Main page - OPEN THIS
├── styles.css              Retro dark theme
├── 
├── 📄 Documentation
│   ├── README.md           Full documentation
│   ├── QUICKSTART.md       Quick start guide ⭐
│   ├── BROWSER.md          Browser compatibility
│   ├── EXTEND.md           How to extend
│   └── EXAMPLES.js         Code examples
│
└── js/                     JavaScript modules
    ├── main.js             Initialization
    ├── core/
    │   ├── State.js        State management
    │   └── Sequencer.js    Playback logic
    ├── audio/
    │   ├── AudioEngine.js  Web Audio API
    │   └── Synth.js        Sound synthesis
    ├── midi/
    │   ├── MidiOutput.js   MIDI control
    │   └── MidiExporter.js MIDI file export
    └── ui/
        ├── PianoRoll.js    Canvas grid
        └── Controls.js     UI handlers
```

## 🎯 What You Can Do

### Immediate
- ✅ Play notes with mouse or keyboard
- ✅ Create multi-track patterns
- ✅ Adjust tempo, volume, waveform
- ✅ Keyboard shortcuts for quick editing
- ✅ Save patterns to browser

### With MIDI Device
- ✅ Send notes to external synthesizer
- ✅ Export patterns as standard MIDI files
- ✅ Control external hardware

### Advanced
- ✅ Programmatic pattern creation (console)
- ✅ Custom extensions (effects, more tracks, etc.)
- ✅ Integration with DAWs via MIDI export
- ✅ Offline use

## ⌨️ Essential Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **SPACE** | Play/Stop |
| **1, 2, 3** | Switch track |
| **DELETE** | Clear step |
| **→/←** | Next/previous step |
| **↑/↓** | Change note pitch |
| **Ctrl+C** | Clear track |

## 🎮 Console Commands

Open browser console (F12) and try:

```javascript
// Playback
Sequencer.play()
Sequencer.stop()
Sequencer.togglePlay()

// Configuration
Sequencer.setBPM(140)
Sequencer.setWaveform('sawtooth')

// Pattern management
App.savePattern('techno')
App.loadPattern('techno')
App.listPatterns()

// MIDI
Sequencer.exportMIDI()

// Info
Sequencer.getStats()
quickStart()  // See more examples
```

## 📋 Feature Checklist

### Audio Features
- [x] Web Audio API synthesis
- [x] Square, Triangle, Sawtooth waves
- [x] ADSR envelope
- [x] Master volume control
- [x] Per-track volume
- [x] 120 BPM - 300 BPM tempo range

### User Interface
- [x] Piano roll grid
- [x] 3 independent tracks (expandable)
- [x] 16-step pattern
- [x] 12-note range C4-G5 (expandable)
- [x] Dark retro theme
- [x] Responsive design

### Playback & Control
- [x] Real-time step sequencing
- [x] Visual playback indicator
- [x] Keyboard shortcuts
- [x] Play/Stop/Clear controls

### MIDI Features
- [x] Web MIDI API integration
- [x] MIDI device selection
- [x] MIDI file export (.mid)
- [x] Multiple track channels

### Data Management
- [x] Save patterns to browser
- [x] Export as JSON
- [x] State serialization
- [x] Event-driven architecture

## 🔧 Customization

All major aspects are customizable:

```javascript
// Change BPM range
// Edit: tempoSlider min/max in index.html

// More tracks
// Edit: State.js constructor + audio setup

// Expand note range
// Edit: Synth.js noteFrequencies

// Different colors
// Edit: :root in styles.css

// Add effects
// Create files in js/audio/ (see EXTEND.md)
```

## 🐛 Troubleshooting

### No Sound
1. Check volume sliders (Master & Track)
2. Check system volume
3. Try different waveform
4. Click the page first (audio context resume requirement)
5. Check browser console for errors (F12)

### MIDI Not Working
1. Device powered on and connected
2. Select device from dropdown
3. Using HTTPS or localhost (not file://)
4. Browser supports Web MIDI (Chrome, Firefox, Edge - not Safari)

### Pattern Not Saving
1. Browser allows localStorage
2. Enough disk space
3. Try private/incognito window
4. Check browser storage quota

See [BROWSER.md](BROWSER.md) for more platform-specific issues.

## 📱 Browser Support

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome | ✅ Full | Recommended |
| Firefox | ✅ Full | Excellent |
| Edge | ✅ Full | Chrome-based |
| Safari | ⚠️ Partial | No MIDI, audio works |
| Opera | ✅ Full | Chrome-based |
| Mobile | ⚠️ Limited | Touch support varies |

See [BROWSER.md](BROWSER.md) for detailed compatibility information.

## 🎓 Learning Resources

### Understanding the Code
1. Start with `index.html` - see the overall structure
2. Read `js/core/State.js` - understand state management
3. Look at `js/ui/PianoRoll.js` - see how UI works
4. Check `js/audio/AudioEngine.js` - audio processing

### Building Extensions
1. Read [EXTEND.md](EXTEND.md) for examples
2. Follow code structure and comments
3. Test in browser console
4. Share your creations!

### Music Theory Basics
- Notes: C, D, E, F, G, A, B (repeat each octave)
- Octaves: Click higher rows for higher notes
- Rhythm: Each column = time step
- Harmony: Different tracks = different notes at same time

## 🤝 Contributing

Found a bug? Have an improvement?

1. Test the issue thoroughly
2. Document steps to reproduce
3. Check existing code for patterns
4. Submit improvements following existing style

## 📄 License

This project is free and open-source. Use, modify, and distribute freely.

Inspired by classic trackers:
- FastTracker 2
- ProTracker  
- ScreamTracker
- OctaMED

Built with:
- Vanilla JavaScript (ES6+)
- Web Audio API
- Web MIDI API
- HTML5 Canvas

## 🎉 Getting Help

1. **Console Examples**: Type `quickStart()` in browser console
2. **Documentation**: See [README.md](README.md) for full API
3. **Browser Issues**: See [BROWSER.md](BROWSER.md) for platform-specific help
4. **Extension Help**: See [EXTEND.md](EXTEND.md) for code examples
5. **Code Comments**: All modules heavily commented

## 🎵 Next Steps

**New Users**:
1. Open index.html
2. Read [QUICKSTART.md](QUICKSTART.md) (5 minutes)
3. Create your first pattern
4. Save and export it

**Intermediate Users**:
1. Learn console commands
2. Create complex patterns
3. Connect MIDI device
4. Export to DAW

**Advanced Users**:
1. Read [EXTEND.md](EXTEND.md)
2. Add custom features
3. Build effects
4. Create pattern banks

---

## Summary

| Question | Answer |
|----------|--------|
| **How do I start?** | Open index.html, read QUICKSTART.md |
| **How do I make sound?** | Click grid, press SPACE |
| **How do I use MIDI?** | Select device, patterns auto-route |
| **How do I save?** | Click export or use console save |
| **How do I add features?** | Read EXTEND.md |
| **Which browser?** | Chrome, Firefox (Safari for audio only) |
| **Is it free?** | Yes, completely open |

---

**Ready to make music?** Open **index.html** right now! 🎶

For specific questions, check the documentation folder or browser console.

**Happy sequencing!** 🎵
