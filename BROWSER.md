# 🌐 Browser Compatibility & Permissions

## Browser Support Summary

| Feature | Chrome | Firefox | Safari | Edge | Opera |
|---------|--------|---------|--------|------|-------|
| **Web Audio API** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Web MIDI API** | ✅ Full | ✅ Full | ❌ No | ✅ Full | ✅ Full |
| **Canvas** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **localStorage** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **RequestAnimationFrame** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **File API** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |

### Feature Details

#### Web Audio API
- **Purpose**: Generate sound using oscillators
- **Status**: Widely supported since 2013
- **Min Version**: Chrome 14+, Firefox 25+, Safari 6+
- **Notes**: No special permissions required

#### Web MIDI API
- **Purpose**: Send MIDI notes to external devices
- **Chrome/Edge**: ✅ Fully supported
  - Desktop (Windows, macOS, Linux)
  - Requires HTTPS or localhost
  - User permission on first use
  
- **Firefox**: ✅ Fully supported
  - Desktop only
  - Requires HTTPS or localhost
  - About the same feature level as Chrome
  
- **Safari**: ❌ Not supported
  - No MIDI API available
  - Audio synthesis works fine
  - Consider alternative: virtual MIDI routing via system tools
  
- **Mobile**: ⚠️ Limited
  - iOS Safari: No MIDI, limited audio context
  - Android Chrome: MIDI support varies

---

## Permission Requirements

### Web Audio API (ALWAYS NEEDED)

**First User Interaction Requirement**:
Web Audio API requires that the user interact with the page before audio can play (to prevent autoplay spam).

```javascript
// This is why we do:
document.addEventListener('click', async () => {
    await audioEngine.audioContext.resume();
});
```

**What the user sees**: Nothing! It just works after they click.

### Web MIDI API (OPTIONAL - ONLY IF USING MIDI)

**First Use**:
1. User selects a MIDI device from dropdown
2. Browser shows permission dialog:
   ```
   "Web Sequencer" wants to access your MIDI devices
   [Allow] [Block]
   ```

3. After user clicks Allow:
   - MIDI output becomes active
   - Notes can be sent to synthesizer

**No Permission Required for**:
- Audio synthesis (Web Audio API)
- MIDI Export (saves as .mid file locally)

**Optional Permissions** (in advanced scenarios):
- File System Access (for loading patterns with File Picker)
- Clipboard API (for copy/paste patterns)

---

## HTTPS Requirements

### When HTTPS is REQUIRED
1. **Web MIDI API**: Requires HTTPS (with rare exceptions)
   - localhost:* is allowed for development
   - file:// protocol does NOT work with MIDI
   
2. **Service Workers**: Not used here, but required for PWA

### When HTTPS is NOT Required
1. **Web Audio API**: Works on any protocol
2. **Canvas**: Works on any protocol
3. **localStorage**: Works on any protocol
4. **File/Blob URLs**: Work on any protocol

### Testing Locally Without HTTPS

**Option 1: Python HTTP Server** (Recommended)
```bash
# Navigate to sequencer folder
cd /path/to/sequencer

# Python 3
python -m http.server 8000

# Then visit: http://localhost:8000
```

**Option 2: Node.js http-server**
```bash
npx http-server
# or
npm install -g http-server
http-server
```

**Option 3: PHP**
```bash
php -S localhost:8000
```

**Option 4: Browser's file:// protocol** (Limited)
```
file:///path/to/sequencer/index.html
# Works for Audio API
# DOES NOT WORK for Web MIDI
```

---

## Platform-Specific Notes

### Windows

**Chrome/Edge**: ✅ Full support
- MIDI works with Windows MIDI devices
- Test with: VirtualMIDI, loopMIDI

**Firefox**: ✅ Full support
- Similar to Chrome
- WinMM MIDI API integration

**Recommended Setup**:
- Use Chrome or Edge
- Use loopMIDI for virtual routing
- HTTPS not required on localhost

### macOS

**Chrome/Edge**: ✅ Full support
- MIDI works with Core MIDI
- Works with GarageBand, Logic Pro

**Safari**: ❌ No MIDI support
- Audio synthesis still works
- Consider Chrome Alternative

**Firefox**: ✅ Full support
- Core MIDI integration

**Recommended Setup**:
- Use Chrome, Firefox, or Safari (Safari for music only)
- System handles MIDI routing natively

### Linux

**Chrome/Edge**: ✅ Full support
- MIDI works with ALSA/Jack
- May require additional setup

**Firefox**: ✅ Full support
- Similar MIDI support

**Safari**: ❌ Not available

**Recommended Setup**:
- Use Chrome or Firefox
- ALSA MIDI or Jack Audio routing
- May need `sudo` for MIDI ports

### iOS (iPhone/iPad)

**Safari**: ⚠️ Partial
- Web Audio API works
- Web MIDI NOT available
- Audio context has restrictions
- Layout optimized for touch

**Chrome/Firefox**: ⚠️ Limited
- Uses Safari WebKit engine
- Same restrictions as Safari

**Recommendation**: Use desktop for full features

### Android

**Chrome**: ✅ Good support
- Web Audio API: Yes
- Web MIDI API: Varies (depends on device/version)
- Requires HTTPS or localhost

**Firefox**: ✅ Good support
- Similar to Chrome

**Recommendation**: Use Chrome for best support

---

## Permissions Popup Examples

### Web MIDI Permission (First Time Using MIDI)

```
┌─────────────────────────────────────────┐
│ localhost wants to access your MIDI     │
│ devices                                 │
│                                         │
│ Allow devices to receive MIDI messages  │
│                                         │
│            [Block]  [Allow]             │
└─────────────────────────────────────────┘
```

### What This Means
- ✅ Microphone/Camera: NOT required (we don't use them)
- ✅ Location: NOT required (we don't use it)
- ✅ MIDI: Only if you want to use external synth
- ✅ Clipboard: Optional, not implemented

---

## Troubleshooting by Browser

### Chrome/Edge: No Sound
**Checklist**:
- [ ] Volume slider > 0%
- [ ] System volume not muted
- [ ] Click page first (audio context resume)
- [ ] Try different waveform
- [ ] Check browser console for errors (F12)

**Fix**:
```javascript
// In console
audioEngine.audioContext.state // Should show 'running'
```

### Firefox: No Sound
**Same as Chrome** - usually system volume or muted browser tab

### Safari: No Sound
**May be related to**:
- Stricter audio context policies
- Try: Click Play button, wait 100ms, then interact with grid
- Update to latest Safari

### MIDI Not Showing Devices
**Check**:
1. Device powered on and connected
2. Browser updated to latest version
3. Using HTTPS or localhost
4. No popup browser blocking permission request
5. Check browser console: 
   ```javascript
   midiManager.isSupported  // Should be true
   midiManager.getOutputs() // Should list devices
   ```

### MIDI Devices Show But No Sound
**Possible causes**:
1. External synthesizer muted or volume off
2. Wrong MIDI channel (try channels 1-3)
3. Device not receiving MIDI (check its input settings)
4. Try testing with DAW first to confirm device works

---

## Security & Privacy

### What We Access
- ✅ **Web Audio API**: Oscillator generation (no I/O)
- ✅ **Web MIDI API**: MIDI output only (device configuration)
- ✅ **Canvas**: Drawing (visual only)
- ✅ **localStorage**: Save patterns (local storage)
- ✅ **Blob/File API**: Export/import files

### What We DON'T Access
- ❌ Microphone
- ❌ Camera/Webcam
- ❌ Location data
- ❌ Network (except initial page load)
- ❌ Files outside explicit user selection
- ❌ Clipboard without permission
- ❌ Contacts or personal data

### Data Stored Locally
- **Browser**: Pattern saves in localStorage (device-specific)
- **Server**: Nothing uploaded (it's a static page)
- **Transmitted**: Nothing except initial HTML/CSS/JS load

---

## Best Practices

### For Users
1. **Always use HTTPS** on public internet (even localhost for dev)
2. **Allow MIDI** permission for external synth use
3. **Check system volume** if no sound
4. **Update browser** regularly for new features

### For Developers
1. **Test on multiple browsers**: Chrome, Firefox, Safari
2. **Graceful degradation**: Features work even on older browsers
3. **Permissions dialog**: Explain why (if needed)
4. **Error handling**: Catch and log API failures

### For Deployment
1. **Host on HTTPS**: Required for MIDI on production
2. **Test MIDI**: Verify on different devices before public
3. **Document limitations**: Which browsers support what
4. **Fallbacks**: Audio synthesis works everywhere

---

## Additional Resources

### Official Specifications
- [Web Audio API](https://www.w3.org/TR/webaudio/)
- [Web MIDI API](https://www.w3.org/TR/webmidi/)
- [Canvas API](https://www.w3.org/TR/2dcontext/)

### Browser Compatibility
- [caniuse.com - Web Audio](https://caniuse.com/audio-api)
- [caniuse.com - Web MIDI](https://caniuse.com/midi)

### Testing Tools
- [MIDI Monitor](https://www.snoize.com/MIDIMonitor/) (macOS)
- [MIDI-OX](http://www.midiox.com/) (Windows)
- [qjackctrl](https://qjackctl.sourceforge.io/) (Linux)

---

## Summary

| Use Case | Requirement |
|----------|------------|
| Local development | `http://localhost` ✅ |
| Production HTTPS | `https://yoursite.com` ✅ |
| Local file testing | `file://` for audio only ✅ |
| MIDI on file:// | ❌ Not supported |
| Audio without clicking | ❌ Must click first |
| Archive/offline use | ✅ Works fine |

---

**Need help?** Check the browser console (F12 → Console) for specific error messages!
