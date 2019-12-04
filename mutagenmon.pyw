#!/usr/bin/env python
# coding=utf-8
# This script uses python3

import wx.adv
import wx
import os
import sys
import subprocess
import datetime
import re
import threading
import traceback
import queue
from shutil import copyfile
import signal
import time
import json
from copy import copy

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
cfg = {}

#####################
#      HELPERS      #
#####################


def file_to_list_strip(filename):
    with open(filename) as f:
        fa = f.readlines()
    return [x.strip() for x in fa]


def load_config(fname):
    global cfg
    fa = file_to_list_strip(fname)
    st = '\n'.join(fa)
    st = re.sub(r"#.*?\n", "", st)
    cfg = json.loads(st)


load_config("config/config_mutagenmon.json")


class GracefulKiller:
  def __init__(self):
     self.kill_now = False
     signal.signal(signal.SIGINT, self.exit_gracefully)
     signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
     self.kill_now = True


def my_excepthook(exctype, value, tb):
    est = str(exctype) + '\n' + str(value) + '\n' + str(tb)
    append_log(cfg['LOG_PATH'] + '/error.log', est)
    errorBox('MutagenMon exception', est)


if not cfg['DEBUG_EXCEPTIONS_TO_CONSOLE']:
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


def resolve_log(sname, session_status, fname, method, auto=False):
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
    append_debug_log(90, "RUN: " + str(ca))
    try:
        res = subprocess.check_output(ca, shell=shell, stderr=subprocess.STDOUT).decode("utf-8")
        append_debug_log(90, "+RUN: " + str(ca) + ' ' + res)
        return res
    except subprocess.CalledProcessError as e:
        est = str(ca) + '\n' + e.output.decode("utf-8")
        if interactive_error:
            errorBox('MutagenMon error', est)
        append_log(cfg['LOG_PATH'] + '/error.log', est)
        return est
    except Exception as e:
        est = str(ca) + '\n' + repr(e)
        if interactive_error:
            errorBox('MutagenMon error', est)
        append_log(cfg['LOG_PATH'] + '/error.log', est)
        return est


def test_autoresolve():
    test_fnames = [""]

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
    if level <= cfg['DEBUG_LEVEL']:
        append_file(cfg['LOG_PATH'] + '/debug.log', st2)
        print(st2)


def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


def info_message(st):
    d = wx.Dialog(None, style=wx.CAPTION)
    d.SetTitle(st)
    d.SetSize((300, 50))
    d.CenterOnScreen()
    d.Show(True)
    return d


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


def copy_local(name1, name2):
    try:
        copyfile(name1, name2)
    except Exception as e:
        est = 'Error copying file ' + name1 + ' to ' + name2 + ': ' + repr(e)
        errorBox('MutagenMon error', est)
        append_log(cfg['LOG_PATH'] + '/error.log', est)

def scp(name1, name2):
    return run(
        [cfg['SCP_PATH'], escape_if_remote(name1), escape_if_remote(name2)],
        shell=True,
        interactive_error=True)


def ssh_command(server, command):
    return run(
        [cfg['SSH_PATH'], server, command],
        shell=True,
        interactive_error=True)


def mutagen_sync_list():
    st = run(
        [cfg['MUTAGEN_PATH'], 'sync', 'list'],
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
        [cfg['MERGE_PATH'], name1, name2],
        shell = False,
        interactive_error = True)


def stop_session(sname):
    return run(
        [cfg['MUTAGEN_PATH'], 'sync', 'terminate', sname],
        shell = True,
        interactive_error = False)


def start_session(sname):
    ca = session_config[sname].split()
    ca[0] = cfg['MUTAGEN_PATH']
    return run(
        ca,
        shell = True,
        interactive_error = False)


def init_session_dict():
    return {x: {} for x in session_config}


def init_session_list():
    return {x: [] for x in session_config}


def init_session_default(dflt):
    return {x: dflt for x in session_config}


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
    global session_config
    fa = file_to_list_strip(cfg['MUTAGEN_SESSIONS_BAT_FILE'])
    for s in fa:
        if s.startswith('rem '):
            continue
        result = re.search(r'--name=(.*?) ', s)
        if result is None:
            continue
        sname = result.group(1)
        if sname:
            if sname in session_config:
                dlg = wx.MessageDialog(None, sname + ' session name is duplicate in ' + cfg['MUTAGEN_SESSIONS_BAT_FILE'], 'MutagenMon', wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            session_config[sname] = s


def restart_session(sname):
    stop_session(sname)
    start_session(sname)


def resolve(session_status, sname, fname, method, auto=False):
    imes = None
    if not auto:
        imes = info_message('Remote connection...')
    fpath1 = dir_and_name(session_status[sname]['url1'], fname)
    fpath2 = dir_and_name(session_status[sname]['url2'], fname)
    if method == 'B wins':
        fpath1, fpath2 = fpath2, fpath1
    if session_status[sname]['transport1'] == 'local' and session_status[sname]['transport2'] == 'local':
        copy_local(fpath1, fpath2)
    elif session_status[sname]['transport1'] == 'ssh' and session_status[sname]['transport2'] == 'ssh':
        scp(fpath1, 'cache/temp')
        scp('cache/temp', fpath2)
    else:
        scp(fpath1, fpath2)
    resolve_log(sname, session_status, fname, method, auto)
    if not auto:
        imes.Destroy()


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
        self.session_status = init_session_dict()
        self.session_status = init_session_dict()
        self.session_err = init_session_default(0)
        self.session_laststatus = init_session_default('')
        self.conflicts = init_session_list()
        self.session_code = init_session_default(0)
        self.status_log = ''
        self.auto_resolve_history = {}
        self.messages = queue.Queue()
        threading.Thread.__init__(self)

    def StopThread(self):
        self.enabled = False
        self.stopping = 1

    def StartMutagen(self):
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

    def getCode(self):
        with self.data_lock:
            return self.session_code

    def setCode(self, session_code_):
        with self.data_lock:
            self.session_code = session_code_

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
                time.sleep(cfg['MUTAGEN_POLL_PERIOD'] / 1000.0)
        except Exception as e:
            est = traceback.format_exc()
            append_log(cfg['LOG_PATH'] + '/error.log', est)
            errorBox('MutagenMon error', est)
            raise e

    def stop_mutagen(self):
        if self.getEnabled():
            return
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_config:
                if not session_status[sname]:
                    continue
                status = session_status[sname]['status']
                if status:
                    stop_session(sname)

    def restart_mutagen(self):
        if not self.getEnabled():
            return
        session_err = copy(self.getErr())
        session_log = self.getStatusLog()
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_config:
                # Set session_code to -1 if connecting for a long time or no session or duplicate
                need_restart = False
                restart_msg = ''
                if not session_status[sname]:
                    if session_err[sname] > cfg['SESSION_MAX_NOSESSION']:
                        need_restart = True
                        restart_msg = 'Restarting'
                else:
                    status = session_status[sname]['status']
                    if session_status[sname]['duplicate']:
                        if session_err[sname] > cfg['SESSION_MAX_DUPLICATE']:
                            need_restart = True
                            restart_msg = 'Restarting duplicate'
                            self.messages.put({
                                'type': 'notify',
                                'title': sname,
                                'text': restart_msg + ': ' + status})
                    elif status.startswith(status_connecting):
                        if session_err[sname] > cfg['SESSION_MAX_ERRORS']:
                            need_restart = True
                            restart_msg = 'Restarting connection'
                            if cfg['NOTIFY_RESTART_CONNECTION']:
                                self.messages.put({
                                    'type': 'notify',
                                    'title': sname,
                                    'text': restart_msg + ': ' + status})
                if need_restart:
                    append_log(cfg['LOG_PATH'] + '/restart.log',
                               session_log + '\n' + restart_msg + ': ' + sname)
                    restart_session(sname)
                    session_err[sname] = 0
        self.setErr(session_err)

    def update(self):
        (session_log, session_status, conflicts) = get_session_status()
        self.setStatusLog(session_log)
        session_err = copy(self.getErr())
        session_laststatus = copy(self.getLastStatus())
        session_code = copy(self.getCode())
        for sname in session_config:
            if not session_status[sname]:
                estatus = ''
                if session_laststatus[sname] == estatus:
                    session_err[sname] += 1
                    if session_err[sname] > 1:
                        session_code[sname] = -1
                else:
                    session_err[sname] = 0
                session_laststatus[sname] = estatus
                continue
            status = session_status[sname]['status']
            estatus = status + session_status[sname]['duplicate']
            append_debug_log(95, 'Status ' + sname + ': ' + format_dict(session_status[sname]))
            # Set session_code to -1 if connecting for a long time or no session or duplicate
            if not status or status.startswith(status_connecting) or session_status[sname]['duplicate']:
                if session_laststatus[sname] == estatus:
                    session_err[sname] += 1
                    if session_err[sname] > 1:
                        session_code[sname] = -2
                else:
                    session_err[sname] = 0
            # If ready, set session_code to 100
            elif status.startswith(status_ready):
                session_err[sname] = 0
                session_code[sname] = 100
            # If working, set session_code to 70
            elif status.startswith(status_working):
                session_err[sname] = 0
                session_code[sname] = 70
            # If there are problems, decrease session_code to 30 if it is greater
            if session_status[sname]['problems']:
                session_code[sname] = min(session_code[sname], 30)
            # If there are conflicts, decrease session_code to 60 if it is greater
            if session_status[sname]['conflicts']:
                session_code[sname] = min(session_code[sname], 60)
            # Set last status
            session_laststatus[sname] = estatus
        self.setStatus(session_status)
        self.setErr(session_err)
        self.setLastStatus(session_laststatus)
        self.setCode(session_code)
        append_debug_log(60, 'Conflicts1: ' + str(conflicts))
        self.auto_resolve(conflicts)
        append_debug_log(60, 'Conflicts2: ' + str(conflicts))
        self.setConflicts(conflicts)

    def clean_auto_resolve_history(self):
        if not self.auto_resolve_history:
            return
        # print('History:', self.auto_resolve_history)
        now = time.time()
        for sfname in list(self.auto_resolve_history):
            if self.auto_resolve_history[sfname][0] < now - cfg['AUTORESOLVE_HISTORY_AGE']:
                append_debug_log(10, 'Removing from autoresolve history: ' + sfname)
                del self.auto_resolve_history[sfname]

    def auto_resolve(self, conflicts):
        self.clean_auto_resolve_history()
        append_debug_log(40, 'ARHistory: ' + str(self.auto_resolve_history))
        now = time.time()
        for sname in conflicts:
            for conflict in conflicts[sname]:
                fname = conflict['aname']
                sfname = sname + ':' + fname
                if sfname in self.auto_resolve_history:
                    append_debug_log(60, 'Setting ' + sname + ':' + fname + ' = ' + str(self.auto_resolve_history[sfname][1]))
                    conflict['autoresolved'] = self.auto_resolve_history[sfname][1]
                    continue
                self.auto_resolve_history[sfname] = (
                    now,
                    self.auto_resolve_single(sname, conflict, fname))

    def auto_resolve_single(self, sname, conflict, fname):
        append_debug_log(60, 'Trying to autoresolve ' + sname + ':' + fname)
        for ar in cfg['AUTORESOLVE']:
            result = re.search(ar['filepath'], fname)
            if result is None:
                continue
            session_status = self.getStatus()
            resolve(session_status, sname, fname, ar['resolve'], auto=True)
            conflict['autoresolved'] = True
            est = 'Auto-resolved conflict: ' + ar['resolve']
            append_debug_log(40, est + ' - ' + sname + ':' + fname)
            if cfg['NOTIFY_AUTORESOLVE']:
                self.messages.put({
                    'type': 'notify',
                    'title': est,
                    'text': sname + ': ' + fname})
            return True
        return False


class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.killer = GracefulKiller()
        self.cur_icon = ''
        self.worst_code = 0
        self.frame = frame
        self.load_session_config()
        super(TaskBarIcon, self).__init__()
        self.title = ''
        self.set_icon('img/lightgray.png', cfg['TRAY_TOOLTIP'] + ': waiting for status...')
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
        self.exiting = False
        self.timer = wx.Timer(self)
        self.had_conflicts = set()
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        self.timer.Start(1000)
        self.cycle = 0
        self.monitor = Monitor(cfg['START_ENABLED'])
        self.monitor.start()

    def notify(self, title, text):
        if not self.ShowBalloon(title, text):
            nm = wx.adv.NotificationMessage(title, text)
            nm.Show()

    def load_session_config(self):
        get_sessions()

    def get_worst_code(self):
        session_code = self.monitor.getCode()
        worst_code = 100
        for sname in session_config:
            worst_code = min(worst_code, session_code[sname])
        return worst_code

    def get_messages(self):
        try:
            message = self.monitor.messages.get_nowait()
            # messageBox('test', repr(message))
            if message['type'] == 'notify':
                self.notify(message['title'], message['text'])
        except:
            pass

    def check_killer(self):
        if self.killer.kill_now:
            self.exit()

    def get_conflict_names(self):
        conflicts = self.monitor.getConflicts()
        session_code = self.monitor.getCode()
        cnames = set()
        for sname in session_config:
            if session_code[sname] and conflicts[sname]:
                for conflict in conflicts[sname]:
                    if conflict['autoresolved']:
                        continue
                    cnames.add(sname + ':' + conflict['aname'])
        return cnames

    def notify_conflicts(self):
        if not cfg['NOTIFY_CONFLICTS']:
            return
        cnames = self.get_conflict_names()
        append_debug_log(60, "CNAMES:" + str(cnames) + ' old: ' + str(self.had_conflicts))
        if cnames.difference(self.had_conflicts):
            cst = '\n'.join(cnames.difference(self.had_conflicts))
            self.notify('New conflicts', cst)
        if cnames or self.worst_code == 100:
            self.had_conflicts = cnames

    def update(self, event):
        if self.exiting:
            return
        self.cycle += 1
        self.check_killer()
        self.get_messages()
        self.update_icon()
        self.notify_conflicts()

    def update_icon(self):
        append_debug_log(90, 'Updating worst_code')
        self.worst_code = self.get_worst_code()
        if self.worst_code > 70:
            if self.monitor.getEnabled():
                self.set_icon('img/green.png', cfg['TRAY_TOOLTIP'] + ': mutagen is watching for changes')
            else:
                self.set_icon('img/green-stop.png', cfg['TRAY_TOOLTIP'] + ': mutagen is stopping')
        elif self.worst_code > 60:
            self.set_icon('img/green-sync.png', cfg['TRAY_TOOLTIP'] + ': mutagen is syncing')
        elif self.worst_code > 30:
            self.set_icon('img/green-conflict.png', cfg['TRAY_TOOLTIP'] + ': conflicts')
        elif self.worst_code > 0:
            self.set_icon('img/green-error.png', cfg['TRAY_TOOLTIP'] + ': problems')
        elif self.worst_code == 0:
            self.set_icon('img/lightgray.png', cfg['TRAY_TOOLTIP'] + ': mutagen is waiting for status...')
        elif self.worst_code == -1:
            if self.monitor.getEnabled():
                self.set_icon('img/darkgray-restart.png', cfg['TRAY_TOOLTIP'] + ': mutagen is not running (starting)')
            else:
                self.set_icon('img/darkgray.png', cfg['TRAY_TOOLTIP'] + ': mutagen is not running (disabled)')
        elif self.worst_code == -2:
            if self.monitor.getEnabled():
                self.set_icon('img/orange-restart.png', cfg['TRAY_TOOLTIP'] + ': error (starting)')
            else:
                self.set_icon('img/orange.png', cfg['TRAY_TOOLTIP'] + ': error (disabled)')
        append_debug_log(40, 'Updated worst_code: ' + str(self.worst_code))

    def CreatePopupMenu(self):
        menu = wx.Menu()
        create_menu_item(menu, 'Show status', self.on_left_down)
        if self.monitor.getEnabled():
            create_menu_item(menu, 'Stop Mutagen sessions', self.on_stop)
        else:
            create_menu_item(menu, 'Start Mutagen sessions', self.on_start)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit MutagenMon', self.on_exit)
        return menu

    def set_icon(self, path, title):
        append_debug_log(85, 'Icon state 1: ' +
                         str(self.IsAvailable()) +
                         str(self.IsIconInstalled()) +
                         str(self.IsOk()) +
                         str(self.IsUnlinked()))
        self.title = title
        if self.cur_icon == path:
            return
        self.cur_icon = path
        icon = wx.Icon(path)
        self.SetIcon(icon, title)
        if not self.IsIconInstalled():
            self.exiting = True
            append_log(cfg['LOG_PATH'] + '/error.log', 'Icon crashed. Restarting application')
            # self.notify(self.title, 'Icon crashed. Restarting application')
            subprocess.Popen(['mutagenmon'], shell=True)
            self.exit()
        append_debug_log(85, 'Icon state 2: ' +
                         str(self.IsAvailable()) +
                         str(self.IsIconInstalled()) +
                         str(self.IsOk()) +
                         str(self.IsUnlinked()))

    def visual_merge(self, sname, fname, session_status):
        imes = info_message('Remote connection...')
        # Copy from remote
        lname1 = make_diff_path(session_status[sname]['url1'], fname, 1)
        lname2 = make_diff_path(session_status[sname]['url2'], fname, 2)
        old_mtime = os.path.getmtime(lname1)
        imes.Destroy()
        # Run merge
        run_merge(lname1, lname2)
        # Check if file time changed
        new_mtime = os.path.getmtime(lname1)
        if new_mtime != old_mtime:
            imes = info_message('Remote connection...')
            if session_status[sname]['transport1'] == 'ssh':
                scp(lname1, dir_and_name(session_status[sname]['url1'], fname))
            if session_status[sname]['transport2'] == 'ssh':
                scp(lname1, dir_and_name(session_status[sname]['url2'], fname))
            else:
                copy_local(lname1, dir_and_name(session_status[sname]['url2'], fname))
            imes.Destroy()
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
        imes = info_message('Remote connection...')
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
        imes.Destroy()
        dlg = wx.SingleChoiceDialog(
            None,
            st,
            'MutagenMon: resolve file conflict',
            ['Visual merge', 'A wins', 'B wins'],
            style=wx.DEFAULT_DIALOG_STYLE | wx.OK | wx.CANCEL | wx.CENTRE | wx.OK_DEFAULT)
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

    def get_nice_log(self):
        st = self.monitor.getStatusLog()
        st = st.replace('Conflicts:', '')
        st = re.sub(r"    \(α\).*?\n", "", st)
        st = re.sub(r"    \(β\).*?\n", "", st)
        #st = re.sub(r"    \(β\).*?$", "", st)
        st = st.strip()
        conflicts = self.monitor.getConflicts()
        session_code = self.monitor.getCode()
        cst = ''
        for sname in session_config:
            if session_code[sname] and conflicts[sname]:
                for conflict in conflicts[sname]:
                    if conflict['autoresolved']:
                        cst += sname + ': ' + conflict['aname'] + ' [autoresolving]\n'
                    else:
                        cst += sname + ': ' + conflict['aname'] + '\n'
        if cst:
            st += "\n==================== CONFLICTS ====================\n" + cst
        return st.strip()

    def on_left_down(self, event):
        append_debug_log(10, 'on_left_down')
        st = self.get_nice_log()
        if self.get_conflict_names():
            dlg = wx.MessageDialog(
                self.frame,
                st,
                self.title,
                wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            dlg.SetOKCancelLabels("Resolve conflicts", "Cancel")
            res = dlg.ShowModal()
            if res == wx.ID_OK:
                self.resolve()
        else:
            dlg = wx.MessageDialog(
                self.frame,
                st,
                self.title,
                wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

    def on_start(self, event):
        append_debug_log(10, 'on_start')
        self.monitor.StartMutagen()

    def on_stop(self, event):
        append_debug_log(10, 'on_stop')
        self.monitor.DisableMutagen()

    def on_exit(self, event):
        self.exit()

    def exit(self):
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
