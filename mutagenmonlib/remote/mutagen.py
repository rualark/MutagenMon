from ..local.run import *
from ..local.file import *

global_session_config = {}


def session_config():
    return global_session_config


def mutagen_sync_list():
    st = run(
        [cfg('MUTAGEN_PATH'), 'sync', 'list'],
        shell=True,
        interactive_error=True)
    st = st.replace('Attempting to start Mutagen daemon...', '')
    st = st.replace('Started Mutagen daemon in background (terminate with "mutagen daemon stop")', '')
    st = st.replace('\n\t', '\n    ')
    st = re.sub(r"Labels: .*?\n", "", st)
    st = st.strip()
    st = st.strip('-')
    st = format_current_datetime() + "\n" + st
    return st


def stop_session(sname):
    return run(
        [cfg('MUTAGEN_PATH'), 'sync', 'terminate', sname],
        shell = True,
        interactive_error = False)


def start_session(sname):
    ca = session_config()[sname].split()
    ca[0] = cfg('MUTAGEN_PATH')
    return run(
        ca,
        shell = True,
        interactive_error = False)


def init_session_dict():
    return {x: {} for x in session_config()}


def init_session_list():
    return {x: [] for x in session_config()}


def init_session_default(dflt):
    return {x: dflt for x in session_config()}


def get_session_status():
    st = mutagen_sync_list()
    sa = st.splitlines()
    name = ''
    aname = ''
    astate = ''
    session_status = init_session_dict()
    conflicts = init_session_list()
    side = 0
    for s in sa:
        s = s.strip()
        if s.startswith('Name: '):
            name = s[6:]
            # Detect if there are duplicate sessions with same name
            if session_status[name]:
                session_status[name]['duplicate'] = "dupl"
            else:
                session_status[name]['duplicate'] = ''
            session_status[name]['conflicts'] = 0
            session_status[name]['problems'] = 0
        if s.startswith('Identifier: '):
            session_status[name]['id'] = s[12:]
        if s.startswith('Status: '):
            status = s[8:]
            session_status[name]['status'] = status
        if s.startswith('Alpha:'):
            side = 1
        if s.startswith('Beta:'):
            side = 2
        if s.startswith('URL: '):
            session_status[name]['url' + str(side)] = s[5:]
            if ':/' in s[5:]:
                session_status[name]['transport' + str(side)] = 'ssh'
                session_status[name]['server' + str(side)] = s[5:s.find(':/')]
                session_status[name]['dir' + str(side)] = s[s.find(':/')+1:]
            else:
                session_status[name]['transport' + str(side)] = 'local'
        if s.startswith('Conflicts:'):
            session_status[name]['conflicts'] = 1
        if s.startswith('Problems:'):
            session_status[name]['problems'] = 1
        if s.startswith('(α) '):
            pos = get_matching_open_parenth(s, len(s) - 1)
            aname = s[4:pos - 1]
            astate = s[pos + 1:]
        if s.startswith('(β) '):
            pos = get_matching_open_parenth(s, len(s) - 1)
            bname = s[4:pos - 1]
            bstate = s[pos + 1:]
            conflicts[name].append({
                'aname': aname,
                'bname': bname,
                'astate': astate,
                'bstate': bstate,
                'autoresolved': False
            })
    return st, session_status, conflicts


def get_sessions():
    global global_session_config
    fa = file_to_list_strip(cfg('MUTAGEN_SESSIONS_BAT_FILE'))
    for s in fa:
        if s.startswith('rem '):
            continue
        result = re.search(r'--name=(.*?) ', s)
        if result is None:
            continue
        sname = result.group(1)
        if sname:
            if sname in global_session_config:
                dlg = wx.MessageDialog(None, sname + ' session name is duplicate in ' + cfg('MUTAGEN_SESSIONS_BAT_FILE'), 'MutagenMon', wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            global_session_config[sname] = s


def restart_session(sname):
    stop_session(sname)
    start_session(sname)


def get_worst_code(session_code):
    worst_code = 100
    for sname in session_config():
        worst_code = min(worst_code, session_code[sname])
    return worst_code


def get_conflict_names(conflicts, session_code):
    cnames = set()
    for sname in session_config():
        if session_code[sname] and conflicts[sname]:
            for conflict in conflicts[sname]:
                if conflict['autoresolved']:
                    continue
                cnames.add(sname + ':' + conflict['aname'])
    return cnames

