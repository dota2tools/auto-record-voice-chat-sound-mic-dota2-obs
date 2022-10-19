# auto-record-voice-chat-sound-mic-dota2-obs
ARVCSMDO is an extension for OBS Studio to automatically record Dota 2 audio (voice chat, sounds, music etc.)  
Recordings are saved for each match id with sync information file included.  

# Installation 
* Download [source code](https://github.com/upgradeQ/auto-record-voice-chat-sound-mic-dota2-obs/archive/main.zip), unpack/unzip.
* For windows install [Python3.6](https://www.python.org/downloads/release/python-368/) 64 or 32 bit depending on your OBS, you can use any 3.6+ version of Python in 28+ version of OBS Studio 
* Add `auto_record_dota2.py` to OBS Studio via Tools > Scripts > "+" button
* Add `gamestate_integration_py.cfg` to local dota 2 folder e.g `C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration`
* When first started you may will be prompted to add firewall exception to local network on `127.0.0.1:3322`

# Usage
1. You need to setup OBS Studio properly or better create a new profile with scene collection for this:
 * In Global Audio Devices set to `Disabled` everything - this is to prevent dual capturing
 * In new scene add  Application Audio Capture or equivalent; your mic etc

2. Best encoding advice [coming soon](https://obsproject.com/forum/threads/what-are-encoding-settings-for-audio-only-still-image-recording.160619/), but for now my tests results (not optimized for audio only):
 - `NVIDIA NVENC HEVC`
 - Single track
 - Container - mkv
 - cqp 13 , preset quality, profile main, psycho visual tuning on ,max-b frames 2, fps 30, canvas 2560x1440 , output 1280x720, bicubic
 - audio bitrate 320, sample rate 48kHz, stereo 
 - video render - direct3d 11, nv12, rec 709 limited
 - file results 46 min : 108 mb, 49 min : 116 mb 
 - I did demuxing to 108 mb file to audio mp3 with 320k bitrate and it was 104 mb 

3. Select path where you want to save recordings then press Start, when the game found and after all players are loaded it will start recording.
When game ends and you are left from lobby it will stop. When it is active you should **not** watch other games(live or replay) or play in demo mode.

4. Under unknown circumstances `auto_record_dota2.py` may hang after you close OBS Studio - so make sure to check and kill OBS Studio process in Task Manager.

5. If you have trouble running on Windows with admin mode on, try normal mode. You might also want to downgrade python version to 3.6 or 3.7

# Roadmap 
- Add encoding info
- Implement replay audio player with gamestate integration 
- Add more checks in recording logic
- Fix thread hanging 
- Add ability to restart recording with timestamp and new part on player disconnect

# Contribute 
 [Forks](https://help.github.com/articles/fork-a-repo) are a great way to contribute to a repository.
After forking a repository, you can send the original author a [pull request](https://help.github.com/articles/using-pull-requests)
