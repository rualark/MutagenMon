# MutagenMon
Cross-platform GUI for <a href=https://github.com/mutagen-io/mutagen>mutagen.io</a>: monitor sessions status in tray, restart hanging sessions, resolve conflicts

# Features

- MutagenMon starts sessions specified in file `mutagen/mutagen-create.bat` and monitors their status
- MutagenMon will restart a session if it freezes and cannot connect for some time
- MutagenMon shows an icon in tray based on current sessions status (if multiple sessions are being monitored, worst status of all sessions is shown:

<img src=https://i.imgur.com/mPu7mZq.png align=top width=30> Watching for changes (all ok)

<img src=https://i.imgur.com/TLt1EDe.png align=top width=30> Syncing (scanning, reconciling, staging, applying changes or saving archive)

<img src=https://i.imgur.com/tTMBScq.png align=top width=30> Conflicts detected (but no problems or errors)

<img src=https://i.imgur.com/TzEpAsv.png align=top width=30> Problems detected

<img src=https://i.imgur.com/jHplJEG.png align=top width=30> Mutagen not running (restarting)

<img src=https://i.imgur.com/Xayacab.png align=top width=30> Mutagen not running (disabled)

<img src=https://i.imgur.com/5UAKYvo.png align=top width=30> Mutagen cannot connect (restarting)

<img src=https://i.imgur.com/YcvEENO.png align=top width=30> Mutagen cannot connect (disabled)

- Click on MutagenMon icon in tray to see detailed status of each individual session:

<img src=https://i.imgur.com/B9ljxT7.png>

- If there are conflicts, you can investigate them, resolve visually using winmerge (on Windows) or other software - or choose winning side at once. Time and size of both files is shown. File with latest timestamp is selected automatically for resolution:

<img src=https://i.imgur.com/d98x4xU.png>

# Operating system support

MutagenMon can work on Windows, Linux or Mac (currently tested only on Windows)

# Installation

1. Install python3
2. Install wxpython: `pip install wxpython`
3. Download and unzip <a href=https://github.com/rualark/MutagenMon/releases>MutagenMon release</a>
4. Download <a href=https://github.com/mutagen-io/mutagen>mutagen.io</a> release and put mutagen binary into `mutagen` folder of MutagenMon
5. Add your sessions to  `mutagen/mutagen-create.bat` file in MutagenMon folder 
6. Run `mutagenmon.pyw` with python3

# Limitations

- Requires that session names are unique
- Works only with local and ssh mutagen transports
- File conflict resolving for local-local and ssh-ssh sessions currently works only if you edit merged file - "A wins" and "B wins" strategies do not currently work (I can fix it if you need it)

Issue on mutagen: https://github.com/mutagen-io/mutagen/issues/173
