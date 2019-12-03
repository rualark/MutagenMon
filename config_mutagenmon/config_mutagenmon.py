# Set to 0 to disable logging to log/debug.log
# Set to 100 to enable maximum logging to log/debug.log
DEBUG_LEVEL = 0

# Do not show messageboxes with exceptions, instead print them to console
DEBUG_EXCEPTIONS_TO_CONSOLE = False

# Notify when mutagen is being restarted due to stuck connection
NOTIFY_RESTART_CONNECTION = True

# Notify when conflicts are detected
NOTIFY_CONFLICTS = True

# Notify when conflicts are detected
NOTIFY_AUTORESOLVE = True

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

# Add records matching filenames:
# filepath - specify regular expression to match whole path with directory and filename
# resolve - specify 'A wins' or 'B wins' to choose conflict resolution behavior
AUTORESOLVE = [
    {
        'filepath': r'/\.idea/',
        'resolve': 'A wins'
    },
    {
        'filepath': r'nohup\.out$',
        'resolve': 'B wins'
    },
    {
        'filepath': r'mut.st/con.*?2',
        'resolve': 'A wins'
    },
    {
        'filepath': r'mut.st/con.*?3',
        'resolve': 'B wins'
    }
]

# How long to remember autoresolved conflicts not to try to autoresolve them again (in seconds)
AUTORESOLVE_HISTORY_AGE = 30
