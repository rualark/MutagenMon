# MutagenMon
Cross-platform GUI for mutagen.io: monitor sessions status in tray, restart hanging sessions, resolve conflicts

# Features

- MutagenMon starts sessions specified in file `mutagen/mutagen-create.bat` and monitors their status
- MutagenMon will restart a session if it freezes and cannot connect for some time
- MutagenMon shows an icon in tray based on current sessions status (if multiple sessions are being monitored, worst status of all sessions is shown:

<img src=https://i.imgur.com/mPu7mZq.png align=top width=30> Watching for changes (all ok)

<img src=https://i.imgur.com/TLt1EDe.png align=top width=30> Syncing (scanning, reconciling, staging, applying changes or saving archive)

<img src=https://i.imgur.com/tTMBScq.png align=top width=30> Conflicts detected (but no problems or errors)

<img src=https://i.imgur.com/TzEpAsv.png align=top width=30> Problems detected

<img src=https://i.imgur.com/Xayacab.png align=top width=30> Mutagen not running

<img src=https://i.imgur.com/YcvEENO.png align=top width=30> Mutagen cannot connect

- Click on MutagenMon icon in tray to see detailed status of each individual session:

<img src=https://i.imgur.com/B9ljxT7.png>

- If there are conflicts, you can investigate them, resolve visually using winmerge (on Windows) or other software - or choose winning side at once:

<img src=https://i.imgur.com/d98x4xU.png>

# Operating system support

MutagenMon can work on Windows, Linux or Mac (currently tested only on Windows)

# Installation

1. Install python3
2. Install wxpython: `pip install wxpython`
3. Download mutagen.io and put mutagen binary into `mutagen` folder of MutagenMon
4. Add your sessions to  `mutagen/mutagen-create.bat` file in MutagenMon folder 

# Limitations

- Works only with local and ssh mutagen transports
- File conflict resolving for local-local and ssh-ssh sessions currently works only if you edit merged file - "A wins" and "B wins" strategies do not currently work (I can fix it if you need it)
