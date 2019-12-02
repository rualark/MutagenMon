# Set to 0 to disable logging to log/debug.log
# Set to 100 to enable maximum logging to log/debug.log
DEBUG_LEVEL = 100

# If MutagenMon should start enabled
# (enabled means that it restarts mutagen sessions if they have errors or are not running)
START_ENABLED = True

# Paths to binary files
MERGE_PATH = r'C:\Program Files (x86)\WinMerge\WinMergeU'
SCP_PATH = r'C:\Program Files\Git\usr\bin\scp'
SSH_PATH = r'C:\Program Files\Git\usr\bin\ssh'
MUTAGEN_PATH = r'mutagen\mutagen'

TRAY_TOOLTIP = 'MutagenMon'

# Path for log files
LOG_PATH = 'log'

# Path to mutagen sessions config
MUTAGEN_SESSIONS_BAT_FILE = 'mutagen/mutagen-create.bat'

# Number of pollings with "not connected" errors to allow before restarting mutagen session
SESSION_MAX_ERRORS = 7

# Number of pollings with no session found to allow before restarting mutagen session
SESSION_MAX_NOSESSION = 2

# Number of pollings with duplicate session found to allow before restarting mutagen sessions
SESSION_MAX_DUPLICATE = 2

# Number of milliseconds to wait between polling 'mutagen sync list'
MUTAGEN_POLL_PERIOD = 1000
