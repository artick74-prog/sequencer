# 🚀 Quick Start Guide - Web Sequencer

## Installation & Launch

### Option 1: Direct (No Server Needed)
1. Extract/clone the repository
2. Open `index.html` directly in your browser
3. You should see the sequencer interface

### Option 2: With Local Server (Recommended for MIDI)
```bash
# Using Python 3
python -m http.server 8000

# Using Node.js http-server
npx http-server

# Using PHP
php -S localhost:8000
```

Then visit: `http://localhost:8000`

---

## Basic Usage (30 seconds)

### 1. **Place Notes**
   - Click on the grid cells to add notes
   - Different rows = different note pitches (C4 to G5)
   - Columns = 16-step pattern
   - Click again to remove

### 2. **Select Track**
   - Use Track 1, 2, 3 buttons at the bottom
   - Or press keyboard keys: **1**, **2**, **3**

### 3. **Play**
   - Press **SPACE** or click **▶ Play**
   - You'll hear notes play sequentially

### 4. **Adjust Tempo**
   - Drag BPM slider: 30-300 beats per minute
   - Or type in the value

### 5. **Choose Waveform**
   - Square: Classic, bright sound
   - Triangle: Softer, rounder
   - Sawtooth: Harsh, buzzy

---

## Keyboard Shortcuts (Cheat Sheet)

| Key | What It Does |
|-----|------|
| **SPACE** | Play/Stop |
| **1, 2, 3** | Switch tracks |
| **DELETE** | Clear note at current step |
| **← / →** | Move to previous/next step |
| **↑ / ↓** | Change note pitch (while not playing) |
| **CTRL+C** | Clear entire current track |

---

## Making Your First Beat (60 seconds)

### Kick Pattern
1. Select Track 1
2. Click on steps 0, 4, 8, 12 in the first (bottom) row → hear the bass
3. Click step 2 and 10 in the first row too

### Hi-Hat Pattern
1. Select Track 2
2. Click on every even step (0, 2, 4, 6...) in the middle row
3. This creates a steady hi-hat rhythm

### Melody
1. Select Track 3
2. Click on different rows to create a melody
3. Example: row 2, row 4, row 0, row 2 (reading left to right)

4. Press **SPACE** to hear your beat!

---

## Using MIDI (Connect External Synth)

### Setup
1. Connect your MIDI synthesizer (keyboard, module, etc.)
2. In the sequencer, select your device from "MIDI Output" dropdown
3. Place some notes on the grid
4. Press SPACE - notes go to your synth + internal speaker

### Export to DAW
1. Create your pattern
2. Click **📥 Export MIDI** button
3. Choose where to save the `.mid` file
4. Open in: Ableton Live, Logic Pro, FL Studio, any DAW

---

## Console Commands (Advanced)

Open browser DevTools: **F12** or **Right-Click → Inspect**

Go to **Console** tab and try:

```javascript
// Playback
Sequencer.play()
Sequencer.stop()
Sequencer.togglePlay()

// Set tempo
Sequencer.setBPM(140)

// Change sound
Sequencer.setWaveform('sawtooth')

// Save your pattern
App.savePattern('my_beat')

// Load it back
App.loadPattern('my_beat')

// See all saved patterns
App.listPatterns()

// Export as MIDI
Sequencer.exportMIDI()

// See current state
Sequencer.getStats()
```

---

## Tips & Tricks

### 🎵 Making Better Patterns
- Use **repeated 4-step patterns**: steps 0,4,8,12 sound like a beat
- Tracks play **at the same time**, so create harmony (different notes)
- **Lower notes** = bass (left side of keyboard)
- **Higher notes** = melody (right side of keyboard)

### 📊 Understanding the Grid
```
            16-step pattern
            ↓←←←←←←←→
            [0][1][2][3][4][5][6][7] ... [15]
Note  G5  |_|_|_|_|_|_|_|_|         |
Pitch F5  |_|_|_|_|_|_|_|_|         |
  ↑   E5  |_|_|_|_|_|_|_|_|         |
  |   D5  |_|_|_|_|_|_|_|_|         |
  |   C5  |_|_|_|_|_|_|_|_|         |
  |   B4  |_|_|_|_|_|_|_|_|         |
  └─...
       C4  |●|_|_|●|_|_|●|_|        |  ← Play this note at steps 0,3,6
       
● = note playing
_ = silence
```

### 🔊 Volume Tips
- **Too quiet?** Increase Master Volume slider
- **Track too loud?** Use Track Volume slider at bottom
- **Distorted?** Lower Master Volume below 50%

### ⏱️ Tempo Tips
- **120 BPM**: Standard, good for practice
- **140 BPM**: Fast, for house/techno
- **90 BPM**: Slow, for downtempo/ambient
- Small changes (±10 BPM) = big feel difference

---

## Troubleshooting

### No Sound
- [ ] Check Master Volume slider (should be > 0%)
- [ ] Check Track Volume at bottom
- [ ] Try clicking Play/Stop button again
- [ ] Try a different waveform
- [ ] Check browser volume

### MIDI Not Working
- [ ] Make sure device is powered on and connected
- [ ] Select it from MIDI Output dropdown
- [ ] Not all browsers support MIDI (Chrome ✅, Firefox ✅, Safari ⚠️)
- [ ] Requires HTTPS or localhost (not http://)

### Pattern Doesn't Sound Right
- [ ] Check you're on the right track (button shows blue highlight)
- [ ] Notes might be too high/low (try middle rows)
- [ ] Try different waveforms
- [ ] Increase tempo to hear pattern better

---

## Next Steps

1. **Create 3-4 patterns** and experiment
2. **Save your favorites** using console commands
3. **Export to MIDI** and load in your DAW
4. **Connect a MIDI synth** and play with it
5. **Read the full README.md** for advanced features

---

## File Organization

```
sequencer/
├── index.html          ← Open this!
├── QUICKSTART.md       ← You are here
├── README.md           ← Full documentation
├── EXAMPLES.js         ← Code examples
└── js/
    ├── main.js
    ├── core/           ← Sequencer engine
    ├── audio/          ← Sound synthesis
    ├── midi/           ← MIDI output & export
    └── ui/             ← Piano roll & controls
```

---

## Community & Resources

- **Inspiration**: Classic trackers - FastTracker 2, ProTracker, ScreamTracker
- **Learn MIDI**: https://www.midi.org/
- **Web Audio API**: https://developer.mozilla.org/en-US/docs/Web_Audio_API
- **Your DAW**: Any DAW can load the exported `.mid` files

---

## Have Fun! 🎶

The sequencer is fully functional. Start clicking on the grid and making music!

Questions? Open the console (**F12**) and explore:
- Type `App` to see available functions
- Type `Sequencer` to see playback controls
- Type `quickStart()` to see usage examples

**Happy sequencing!** 🎵
