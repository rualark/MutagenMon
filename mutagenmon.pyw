#!/usr/bin/env python
# coding=utf-8
# This script uses python3

import wx.adv
import wx
import os
import time
import sys
import subprocess
import datetime
import re
from collections import defaultdict
import threading
import traceback
import queue
from config_mutagenmon.config_mutagenmon import *

#####################
#      CONFIG       #
#####################

status_connecting = (
    'Connecting to',
    'Waiting to connect',
    'Unknown')
status_working = (
    'Scanning files',
    'Waiting 5 seconds for rescan',
    'Reconciling changes',
    'Staging files on',
    'Applying changes',
    'Saving archive')
status_ready = (
    'Watching for changes')

session_config = {}

#####################
#      HELPERS      #
#####################


def my_excepthook(exctype, value, tb):
    est = str(exctype) + '\n' + str(value) + '\n' + str(tb)
    append_log(LOG_PATH + '/error.log', est)
    errorBox('MutagenMon exception', est)

sys.excepthook = my_excepthook


def dir_and_name(dir, name):
    # dir.replace("\\", '/')
    if dir[:-1] == '/':
        return dir + name
    else:
        return dir + '/' + name


def write_file(fname, st):
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(st + '\n')


def append_file(fname, st):
    with open(fname, 'a+', encoding='utf-8') as f:
        f.write(st + '\n')


def format_current_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def format_datetime_from_timestamp(i):
    return datetime.datetime.fromtimestamp(i).strftime("%Y-%m-%d %H:%M:%S")


def append_log(fname, st):
    append_file(fname, '[' + format_current_datetime() + '] ' + str(st))


def resolve_log(sname, session_status, fname, method, auto):
    st = ''
    if auto:
        st += ' (AUTO)'
    st += '\n'
    st += sname + '\n'
    st += session_status[sname]['url1'] + '\n'
    st += session_status[sname]['url2'] + '\n'
    st += fname + '\n'
    st += method + '\n'
    append_log('log/resolve.log', st)


def format_dict(d):
    st = ""
    for key, val in d.items():
        if st:
            st += ", "
        st += "%s: '%s'" % (key, val)
    return st


def format_status(d):
    st = ""
    for key, val in d.items():
        if st:
            st += ". "
        st += key + ": "
        first = 1
        for key2, val2 in val.items():
            if not first:
                st += ', '
            else:
                first = 0
            st += key2 + "=" + str(val2)
    return st


def file_to_list_strip(filename):
    with open(filename) as f:
        fa = f.readlines()
    return [x.strip() for x in fa]


def get_matching_open_parenth(st, i):
    stack = []
    for x in reversed(range(i)):
        if st[x] == '(':
            if not stack:
                return x
            else:
                stack.pop()
        if st[x] == ')':
            stack.append(1)


def test_matching_open_parenth():
    st = "asdf ( df) (d(e)erf) ( adf)"
    print(st, get_matching_open_parenth(st, len(st) - 1))
    st = "asdf ( df) (d(e)erf) ( adf (qwer ))"
    print(st, get_matching_open_parenth(st, len(st) - 1))
    st = "asdf ( df) (d(e)erf) ( adf (qwer )asd)"
    print(st, get_matching_open_parenth(st, len(st) - 1))


def remote_escape(st):
    return st.replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)').replace('&', '\\&')


def escape_if_remote(st):
    if ':/' in st:
        return remote_escape(st)
    else:
        return st


def run(ca, shell, interactive_error):
    append_debug_log(20, "RUN: " + str(ca))
    try:
        res = subprocess.check_output(ca, shell=shell, stderr=subprocess.STDOUT).decode("utf-8")
        append_debug_log(20, "+RUN: " + str(ca) + ' ' + res)
        return res
    except subprocess.CalledProcessError as e:
        est = str(ca) + '\n' + e.output.decode("utf-8")
        if interactive_error:
            errorBox('MutagenMon error', est)
        append_log(LOG_PATH + '/error.log', est)
        return est
    except Exception as e:
        est = str(ca) + '\n' + repr(e)
        if interactive_error:
            errorBox('MutagenMon error', est)
        append_log(LOG_PATH + '/error.log', est)
        return est

#####################
#      SCRIPT       #
#####################


def make_diff_path(url, fname, id):
    if ':/' not in url:
        return dir_and_name(url, fname)
    lname = 'diff/remote' + str(id)
    scp(dir_and_name(url, fname), lname)
    return lname


def append_debug_log(level, st):
    st2 = '[' + format_current_datetime() + '] ' + str(st)
    if level <= DEBUG_LEVEL:
        append_file(LOG_PATH + '/debug.log', st2)
        print(st2)


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


def notify(title, st):
    nm = wx.adv.NotificationMessage(title, st)
    # nm.MSWUseToasts("some_shortcut", "123")
    nm.Show()
    # toaster = ToastNotifier()
    # toaster.show_toast(title, st, duration=5) # icon_path='img/gray.png',


def messageBox(title, st):
    wx.MessageDialog(
        None,
        st,
        title,
        wx.OK | wx.ICON_INFORMATION).ShowModal()


def errorBox(title, st):
    wx.MessageDialog(
        None,
        st,
        title,
        wx.OK | wx.ICON_ERROR).ShowModal()


def scp(name1, name2):
    return run(
        [SCP_PATH, escape_if_remote(name1), escape_if_remote(name2)],
        shell=True,
        interactive_error=True)


def ssh_command(server, command):
    return run(
        [SSH_PATH, server, command],
        shell=True,
        interactive_error=True)


def mutagen_sync_list():
    st = run(
        [MUTAGEN_PATH, 'sync', 'list'],
        shell=True,
        interactive_error=True)
    st = st.replace('Attempting to start Mutagen daemon...', '')
    st = st.replace('Started Mutagen daemon in background (terminate with "mutagen daemon stop")', '')
    st = st.replace('\n\t', '\n    ')
    st = re.sub(r"Identifier: .*?\n", "", st)
    st = re.sub(r"Labels: .*?\n", "", st)
    st = st.strip()
    st = st.strip('-')
    st = format_current_datetime() + "\n" + st
    return st


def run_merge(name1, name2):
    return run(
        [MERGE_PATH, name1, name2],
        shell = False,
        interactive_error = True)


def stop_session(sname):
    return run(
        [MUTAGEN_PATH, 'sync', 'terminate', sname],
        shell = True,
        interactive_error = False)


def start_session(sname):
    ca = session_config[sname].split()
    ca[0] = MUTAGEN_PATH
    return run(
        ca,
        shell = True,
        interactive_error = False)


def get_session_status():
    st = mutagen_sync_list()
    sa = st.splitlines()
    name = ''
    aname = ''
    astate = ''
    session_status = defaultdict(lambda: defaultdict(lambda: ''))
    conflicts = defaultdict(list)
    side = 0
    for s in sa:
        s = s.strip()
        if s.startswith('Name: '):
            name = s[6:]
            # Detect if there are duplicate sessions with same name
            if name in session_status:
                session_status[name]['duplicate'] = "dupl"
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
                'bstate': bstate
            })
    return st, session_status, conflicts


def get_sessions():
    global session_config
    fa = file_to_list_strip(MUTAGEN_SESSIONS_BAT_FILE)
    for s in fa:
        if s.startswith('rem '):
            continue
        result = re.search(r'--name=(.*?) ', s)
        if result is None:
            continue
        sname = result.group(1)
        if sname:
            if sname in session_config:
                dlg = wx.MessageDialog(None, sname + ' session name is duplicate in ' + MUTAGEN_SESSIONS_BAT_FILE, 'MutagenMon', wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            session_config[sname] = s


def restart_session(sname):
    stop_session(sname)
    start_session(sname)


def stop_sessions():
    for sname in session_config:
        stop_session(sname)


def resolve(session_status, sname, fname, method, auto=False):
    if method == 'A wins':
        id1 = '1'
        id2 = '2'
    else:
        id1 = '2'
        id2 = '1'
    if session_status[sname]['transport1'] == session_status[sname]['transport2']:
        messageBox('Warning',
                   'Currently "A win" and "B win" strategies are not supported for local-local or ssh-ssh sessions. You can either use visual merge and change first file, or contribute to the project and rewrite code where you will find this message')
    scp(
        dir_and_name(session_status[sname]['url' + id1], fname),
        dir_and_name(session_status[sname]['url' + id2], fname))
    resolve_log(sname, session_status, fname, method, auto)


def get_size_time_ssh(session_status, sname, i, fname):
    res = ssh_command(
        session_status[sname]['server' + str(i)],
        "stat -c '%Y %s' " + remote_escape(dir_and_name(session_status[sname]['dir' + str(i)], fname)))
    ftime = int(res.split(' ')[0].strip())
    fsize = int(res.split(' ')[1].strip())
    return fsize, ftime


class Monitor(threading.Thread):
    def __init__(self, enabled_):
        self.stopping = 0
        self.enabled = enabled_
        self.data_lock = threading.Lock()
        self.mutagen_lock = threading.Lock()
        self.session_status = defaultdict(lambda: defaultdict(lambda: ''))
        self.session_status = defaultdict(lambda: defaultdict(lambda: ''))
        self.session_err = defaultdict(lambda: 0)
        self.session_laststatus = defaultdict(lambda: '')
        self.conflicts = defaultdict(list)
        self.session_ok = defaultdict(lambda: 0)
        self.status_log = ''
        self.autoresolve_history = {}
        self.messages = queue.Queue()
        threading.Thread.__init__(self)

    def StopThread(self):
        self.enabled = False
        self.stopping = 1

    def RestartMutagen(self):
        if self.enabled:
            with self.mutagen_lock:
                stop_sessions()
        with self.data_lock:
            self.enabled = True

    def DisableMutagen(self):
        with self.data_lock:
            self.enabled = False

    def getEnabled(self):
        with self.data_lock:
            return self.enabled

    def getStatus(self):
        with self.data_lock:
            return self.session_status

    def setStatus(self, session_status_):
        with self.data_lock:
            self.session_status = session_status_

    def getConflicts(self):
        with self.data_lock:
            return self.conflicts

    def setConflicts(self, conflicts_):
        with self.data_lock:
            self.conflicts = conflicts_

    def getErr(self):
        with self.data_lock:
            return self.session_err

    def setErr(self, session_err_):
        with self.data_lock:
            self.session_err = session_err_

    def getLastStatus(self):
        with self.data_lock:
            return self.session_laststatus

    def setLastStatus(self, session_laststatus_):
        with self.data_lock:
            self.session_laststatus = session_laststatus_

    def getOk(self):
        with self.data_lock:
            return self.session_ok

    def setOk(self, session_ok_):
        with self.data_lock:
            self.session_ok = session_ok_

    def setStatusLog(self, status_log_):
        with self.data_lock:
            self.status_log = status_log_

    def getStatusLog(self):
        with self.data_lock:
            return self.status_log

    def run(self):
        try:
            while True:
                with self.data_lock:
                    if self.stopping:
                        return
                self.update()
                self.restart_mutagen()
                self.stop_mutagen()
                self.auto_resolve()
                time.sleep(MUTAGEN_POLL_PERIOD / 1000.0)
        except Exception as e:
            append_log(LOG_PATH + '/error.log', traceback.format_exc())
            raise e

    def stop_mutagen(self):
        if self.getEnabled():
            return
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_config:
                status = session_status[sname]['status']
                if status:
                    stop_session(sname)

    def restart_mutagen(self):
        if not self.getEnabled():
            return
        session_err = self.getErr()
        session_log = self.getStatusLog()
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_config:
                status = session_status[sname]['status']
                # Set session_ok to -1 if connecting for a long time or no session or duplicate
                need_restart = False
                restart_msg = ''
                if not status:
                    if session_err[sname] > SESSION_MAX_NOSESSION:
                        need_restart = True
                        restart_msg = 'Restarting'
                elif session_status[sname]['duplicate']:
                    if session_err[sname] > SESSION_MAX_DUPLICATE:
                        need_restart = True
                        restart_msg = 'Restarting duplicate'
                        notify(sname, restart_msg + ': ' + session_status[sname]['status'])
                elif status.startswith(status_connecting):
                    if session_err[sname] > SESSION_MAX_ERRORS:
                        need_restart = True
                        restart_msg = 'Restarting connection'
                        notify(sname, restart_msg + ': ' + session_status[sname]['status'])
                if need_restart:
                    append_log(LOG_PATH + '/restart.log',
                               session_log + '\n' + restart_msg + ': ' + sname)
                    restart_session(sname)
                    session_err[sname] = 0
        self.setErr(session_err)

    def update(self):
        (session_log, session_status, conflicts) = get_session_status()
        self.setStatusLog(session_log)
        session_err = self.getErr()
        session_laststatus = self.getLastStatus()
        session_ok = self.getOk()
        for sname in session_config:
            status = session_status[sname]['status']
            estatus = status + session_status[sname]['duplicate']
            append_debug_log(5, 'Status ' + sname + ': ' + format_dict(session_status[sname]))
            # Set session_ok to -1 if connecting for a long time or no session or duplicate
            if not status or status.startswith(status_connecting) or session_status[sname]['duplicate']:
                if session_laststatus[sname] == estatus:
                    session_err[sname] += 1
                    if session_err[sname] > 1:
                        if not status:
                            session_ok[sname] = -1
                        else:
                            session_ok[sname] = -2
                else:
                    session_err[sname] = 0
            # If ready, set session_ok to 100
            elif status.startswith(status_ready):
                session_err[sname] = 0
                session_ok[sname] = 100
            # If working, set session_ok to 70
            elif status.startswith(status_working):
                session_err[sname] = 0
                session_ok[sname] = 70
            # If there are problems, decrease session_ok to 30 if it is greater
            if session_status[sname]['problems']:
                session_ok[sname] = min(session_ok[sname], 30)
            # If there are conflicts, decrease session_ok to 60 if it is greater
            if session_status[sname]['conflicts']:
                session_ok[sname] = min(session_ok[sname], 60)
            # Set last status
            session_laststatus[sname] = estatus
        self.setStatus(session_status)
        self.setErr(session_err)
        self.setLastStatus(session_laststatus)
        self.setOk(session_ok)
        self.setConflicts(conflicts)

    def clean_autoresolve_history(self):
        if not self.autoresolve_history:
            return
        # print('History:', self.autoresolve_history)
        now = time.time()
        for fname in list(self.autoresolve_history):
            if self.autoresolve_history[fname] < now - AUTORESOLVE_HISTORY_AGE:
                append_debug_log(30, 'Removing from autoresolve history: ' + fname)
                del self.autoresolve_history[fname]

    def auto_resolve(self):
        self.clean_autoresolve_history()
        conflicts = self.getConflicts()
        for sname in conflicts:
            for conflict in conflicts[sname]:
                self.auto_resolve_single(sname, conflict)

    def auto_resolve_single(self, sname, conflict):
        fname = conflict['aname']
        if fname in self.autoresolve_history:
            return
        for ar in AUTORESOLVE:
            result = re.search(ar['filepath'], fname)
            if result is None:
                continue
            session_status = self.getStatus()
            resolve(session_status, sname, fname, ar['resolve'], auto=True)
            notify(sname, 'Auto-resolved (' + ar['resolve'] + '): ' + fname)
            self.autoresolve_history[fname] = time.time()


class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.cur_icon = ''
        self.menu_items = []
        self.frame = frame
        self.load_session_config()
        super(TaskBarIcon, self).__init__()
        self.title = ''
        self.set_icon('img/lightgray.png', TRAY_TOOLTIP + ': waiting for status...')
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        self.timer.Start(1000)
        self.monitor = Monitor(START_ENABLED)
        self.monitor.start()

    def load_session_config(self):
        get_sessions()

    def get_worst_ok(self):
        session_ok = self.monitor.getOk()
        worst_ok = 100
        for sname in session_config:
            worst_ok = min(worst_ok, session_ok[sname])
        return worst_ok

    def has_ok(self, code):
        session_ok = self.monitor.getOk()
        for sname in session_config:
            if session_ok[sname] == code:
                return True
        return False

    def update(self, event):
        append_debug_log(20, 'Updating worst_ok')
        worst_ok = self.get_worst_ok()
        if worst_ok > 70:
            if self.monitor.getEnabled():
                self.set_icon('img/green.png', TRAY_TOOLTIP + ': mutagen is watching for changes')
            else:
                self.set_icon('img/green-stop.png', TRAY_TOOLTIP + ': mutagen is stopping')
        elif worst_ok > 60:
            self.set_icon('img/green-sync.png', TRAY_TOOLTIP + ': mutagen is syncing')
        elif worst_ok > 30:
            self.set_icon('img/green-conflict.png', TRAY_TOOLTIP + ': conflicts')
        elif worst_ok > 0:
            self.set_icon('img/green-error.png', TRAY_TOOLTIP + ': problems')
        elif worst_ok == 0:
            self.set_icon('img/lightgray.png', TRAY_TOOLTIP + ': mutagen is waiting for status...')
        elif worst_ok == -1:
            if self.monitor.getEnabled():
                self.set_icon('img/darkgray-restart.png', TRAY_TOOLTIP + ': mutagen is not running (restarting)')
            else:
                self.set_icon('img/darkgray.png', TRAY_TOOLTIP + ': mutagen is not running (disabled)')
        elif worst_ok == -2:
            if self.monitor.getEnabled():
                self.set_icon('img/orange-restart.png', TRAY_TOOLTIP + ': error (restarting)')
            else:
                self.set_icon('img/orange.png', TRAY_TOOLTIP + ': error (disabled)')
        append_debug_log(10, 'Updated worst_ok: ' + str(worst_ok))

    def CreatePopupMenu(self):
        worst_ok = self.get_worst_ok()
        menu = wx.Menu()
        create_menu_item(menu, 'Restart Mutagen sessions', self.on_start)
        create_menu_item(menu, 'Stop Mutagen sessions', self.on_stop)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit MutagenMon', self.on_exit)
        return menu

    def set_icon(self, path, title):
        append_debug_log(30, 'set_icon')
        self.title = title
        # if self.cur_icon == path:
        #     return
        self.cur_icon = path
        icon = wx.Icon(path)
        self.SetIcon(icon, title)

    def visual_merge(self, sname, fname, session_status):
        # Copy from remote
        lname1 = make_diff_path(session_status[sname]['url1'], fname, 1)
        lname2 = make_diff_path(session_status[sname]['url2'], fname, 2)
        old_mtime = os.path.getmtime(lname1)
        # Run merge
        run_merge(lname1, lname2)
        # Check if file time changed
        new_mtime = os.path.getmtime(lname1)
        if new_mtime != old_mtime:
            if session_status[sname]['transport1'] == 'ssh':
                scp(lname1, dir_and_name(session_status[sname]['url1'], fname))
            if session_status[sname]['transport2'] == 'ssh':
                scp(lname1, dir_and_name(session_status[sname]['url2'], fname))
            messageBox(
                'MutagenMon: resolved file conflict',
                'Merged file copied to both sides:\n\n' + fname
            )
            return True
        else:
            return False

    def resolve_single(self, sname, conflict, session_status):
        fname = conflict['aname']
        ftime1 = ''
        fsize1 = ''
        ftime2 = ''
        fsize2 = ''
        if session_status[sname]['transport1'] == 'ssh':
            fsize1, ftime1t = get_size_time_ssh(session_status, sname, 1, fname)
            ftime1 = format_datetime_from_timestamp(ftime1t)
        else:
            fsize1 = os.path.getsize(dir_and_name(session_status[sname]['url1'], fname))
            ftime1t = os.path.getmtime(dir_and_name(session_status[sname]['url1'], fname))
            ftime1 = format_datetime_from_timestamp(ftime1t)
        if session_status[sname]['transport2'] == 'ssh':
            fsize2, ftime2t = get_size_time_ssh(session_status, sname, 2, fname)
            ftime2 = format_datetime_from_timestamp(ftime2t)
        else:
            fsize2 = os.path.getsize(dir_and_name(session_status[sname]['url2'], fname))
            ftime2t = os.path.getmtime(dir_and_name(session_status[sname]['url2'], fname))
            ftime2 = format_datetime_from_timestamp(ftime2t)
        st = conflict['aname'] + '\n\n' + \
            'A: ' + session_status[sname]['url1'] + '\n' + \
            str(fsize1) + ' bytes, ' + str(ftime1) + '\n' + \
            conflict['astate'] + '\n\n' + \
            'B: ' + session_status[sname]['url2'] + '\n' + \
            str(fsize2) + ' bytes, ' + str(ftime2) + '\n' + \
            conflict['bstate']
        dlg = wx.SingleChoiceDialog(
            None,
            st,
            'MutagenMon: resolve file conflict',
            ['Visual merge', 'A wins', 'B wins'],
            style=wx.DEFAULT_DIALOG_STYLE | wx.OK | wx.CANCEL | wx.CENTRE)
        if ftime1t > ftime2t:
            dlg.SetSelection(1)
        else:
            dlg.SetSelection(2)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            sel = dlg.GetSelection()
            if sel == 0:
                if self.visual_merge(sname, fname, session_status):
                    resolve_log(sname, session_status, fname, "Visual merge")
                    return True
            if sel == 1:
                resolve(session_status, sname, fname, 'A wins')
                return True
            if sel == 2:
                resolve(session_status, sname, fname, 'B wins')
                return True
        if res == wx.ID_CANCEL:
            return True
        return False

    def resolve(self):
        session_status = self.monitor.getStatus()
        conflicts = self.monitor.getConflicts()
        self.monitor.setConflicts({})
        if not conflicts:
            return
        count = 0
        for sname in conflicts:
            for conflict in conflicts[sname]:
                count += 1
                if count > 100:
                    messageBox(
                        'MutagenMon: resolve file conflict',
                        "Too many conflicts. You can restart resolving or resolve manually")
                    return
                while not self.resolve_single(sname, conflict, session_status):
                    pass

    def on_left_down(self, event):
        append_debug_log(10, 'on_left_down')
        if self.has_ok(60):
            dlg = wx.MessageDialog(
                self.frame,
                self.monitor.getStatusLog(),
                self.title,
                wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            dlg.SetOKCancelLabels("Resolve conflicts", "Cancel")
            res = dlg.ShowModal()
            if res == wx.ID_OK:
                self.resolve()
        else:
            dlg = wx.MessageDialog(
                self.frame,
                self.monitor.getStatusLog(),
                self.title,
                wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

    def on_start(self, event):
        append_debug_log(10, 'on_start')
        self.monitor.RestartMutagen()

    def on_stop(self, event):
        append_debug_log(10, 'on_stop')
        self.monitor.DisableMutagen()

    def on_exit(self, event):
        append_debug_log(5, 'Exiting')
        self.monitor.StopThread()
        wx.CallAfter(self.Destroy)
        self.frame.Close()


class App(wx.App):
    def OnInit(self):
        frame=wx.Frame(None)
        self.SetTopWindow(frame)
        TaskBarIcon(frame)
        return True


def main():
    app = App(False)
    app.MainLoop()


if __name__ == '__main__':
    main()
