# MutagenMon
Cross-platform GUI for <a href=https://github.com/mutagen-io/mutagen>mutagen.io</a> file synchronizer: monitor sessions status in tray, restart hanging sessions, resolve conflicts

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/802c129fde624c2390086e9246f29b79)](https://www.codacy.com/manual/rualark/MutagenMon?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=rualark/MutagenMon&amp;utm_campaign=Badge_Grade)

# Features

- MutagenMon starts sessions specified in file `mutagen/mutagen-create.bat` and monitors their status
- MutagenMon will restart a session if it freezes and cannot connect for some time
- MutagenMon shows an icon in tray based on current sessions status (if multiple sessions are being monitored, worst status of all sessions is shown:

<img src=https://i.imgur.com/mPu7mZq.png align=top width=30> Watching for changes (all ok)

<img src=https://i.imgur.com/Kg671Sm.png align=top width=30> Files updated (this icon is shown for one second when some files are updated in mutagen session)

<img src=https://i.imgur.com/TLt1EDe.png align=top width=30> Syncing (reconciling, staging, applying changes or saving archive)

<img src=https://i.imgur.com/uOzXxHM.png align=top width=30> Scanning files

<img src=https://i.imgur.com/tTMBScq.png align=top width=30> Conflicts detected (but no problems or errors)

<img src=https://i.imgur.com/MW5448A.png align=top width=30> Problems detected

<img src=https://i.imgur.com/376oKOM.png align=top width=30> Waiting for mutagen daemon to respond

<img src=https://i.imgur.com/wR2LqjK.png align=top width=30> Mutagen stopping

<img src=https://i.imgur.com/jHplJEG.png align=top width=30> Mutagen not running (restarting)

<img src=https://i.imgur.com/Xayacab.png align=top width=30> Mutagen not running (disabled)

<img src=https://i.imgur.com/5UAKYvo.png align=top width=30> Mutagen cannot connect (restarting)

<img src=https://i.imgur.com/YcvEENO.png align=top width=30> Mutagen cannot connect (disabled)

- Click on MutagenMon icon in tray to see detailed status of each individual session:

<img src=https://i.imgur.com/B9ljxT7.png>

- If there are conflicts, you can investigate them, resolve visually using winmerge (on Windows) or other software - or choose winning side at once. Time and size of both files is shown. File with latest timestamp is selected automatically for resolution:

<img src=https://i.imgur.com/d98x4xU.png>

- MutagenMon can automatically resolve conflicts if you specify paths, where Alpha or Beta versions should always win. You will get desktop notification if conflict is resolved automatically.

# Operating system support

MutagenMon can work on Windows, Linux or Mac (currently tested only on Windows)

# Installation on Windows

1. Download and unzip <a href=https://github.com/rualark/MutagenMon/releases>MutagenMon release</a>
2. Download <a href=https://github.com/mutagen-io/mutagen>mutagen.io</a> release and put mutagen binary into `mutagen` folder of MutagenMon
3. If you want to use visual diff and merge, download and install winmerge or alternative program, which can take two different files as two parameters.
4. Add your sessions to  `mutagen/mutagen-create.bat` file in MutagenMon folder 
5. Edit configuration file at `mutagen/config/mutagenmon_config.json`
6. Run mutagenmon

# Installation from sources

1. Install python3
2. Install wxpython: `pip install wxpython`
3. Download and unzip <a href=https://github.com/rualark/MutagenMon/releases>MutagenMon release</a>
4. Download <a href=https://github.com/mutagen-io/mutagen>mutagen.io</a> release and put mutagen binary into `mutagen` folder of MutagenMon
5. If you want to use visual diff and merge, download and install winmerge or alternative program, which can take two different files as two parameters.
6. Add your sessions to  `mutagen/mutagen-create.bat` file in MutagenMon folder 
7. Edit configuration file at `mutagen/config/mutagenmon_config.json`
8. Run mutagenmon

# Limitations

- Requires that session names are unique
- Works only with local and ssh mutagen transports

Issue on mutagen: https://github.com/mutagen-io/mutagen/issues/173

[![Open Source Helpers](https://www.codetriage.com/rualark/mutagenmon/badges/users.svg)](https://www.codetriage.com/rualark/mutagenmon)
[![BCH compliance](https://bettercodehub.com/edge/badge/rualark/MutagenMon?branch=master)](https://bettercodehub.com/)

[![DeepSource](https://static.deepsource.io/deepsource-badge-light.svg)](https://deepsource.io/gh/rualark/MutagenMon/?ref=repository-badge)
