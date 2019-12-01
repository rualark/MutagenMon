# MutagenMon
Cross-platform GUI for mutagen.io: monitor sessions status in tray, restart hanging sessions, resolve conflicts

# Features

- MutagenMon starts sessions specified in file `mutagen/mutagen-create.bat` and monitors their status
- MutagenMon shows an icon in tray based on current sessions status (if multiple sessions are being monitored, worst status of all sessions is shown:

<img src=https://i.imgur.com/mPu7mZq.png width=30> Watching for changes

# Operating system support

MutagenMon can work on Windows, Linux or Mac (currently tested only on Windows)

# Installation

1. Install python3
2. Install wxpython: `pip install wxpython`
3. Download mutagen.io and put mutagen binary into mutagen folder of MutagenMon
4. Add your sessions to  `mutagen/mutagen-create.bat` file in MutagenMon folder 
