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

#####################
#      CONFIG       #
#####################

DEBUG_LEVEL = 5
START_ENABLED = True
MERGE_PATH = r'C:\Program Files (x86)\WinMerge\WinMergeU'
SCP_PATH = r'C:\Program Files\Git\usr\bin\scp'
SSH_PATH = r'C:\Program Files\Git\usr\bin\ssh'
MUTAGEN_PATH = r'mutagen\mutagen'
TRAY_TOOLTIP = 'MutagenMon'
LOG_PATH = 'log'
MUTAGEN_SESSIONS_BAT_FILE = 'mutagen/mutagen-create.bat'
SESSION_MAX_ERRORS = 4

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


def formatted_current_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def append_log(fname, st):
    append_file(fname, '[' + formatted_current_datetime() + '] ' + str(st))


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
    if ':/' in st:
        return st.replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)').replace('&', '\\&')
    else:
        return st


def run(ca, shell, interactive_error):
    try:
        res = subprocess.check_output(ca, shell=shell, stderr=subprocess.STDOUT).decode("utf-8")
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
    st2 = '[' + formatted_current_datetime() + '] ' + str(st)
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
        [SCP_PATH, remote_escape(name1), remote_escape(name2)],
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
    st = st.strip()
    st = st.strip('-')
    st = formatted_current_datetime() + "\n" + st
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
                session_status[name]['duplicate'] = 1
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


def get_size_time_ssh(session_status, sname, i, fname):
    res = ssh_command(
        session_status[sname]['server' + str(i)],
        "stat -c '%y %s' " + remote_escape(dir_and_name(session_status[sname]['dir' + str(i)], fname)))
    ftime = res.split('.')[0].strip()
    fsize = res.split(' ')[3].strip()
    return fsize, ftime


class Monitor(threading.Thread):
    def __init__(self, enabled_):
        self.stopping = 0
        self.enabled = enabled_
        self.data_lock = threading.Lock()
        self.mutagen_lock = threading.Lock()
        self.session_status = defaultdict(lambda: defaultdict(lambda: ''))
        self.session_status = defaultdict(list)
        self.session_errcount = defaultdict(lambda: 0)
        self.session_ok = defaultdict(lambda: 0)
        self.status_log = ''
        self.messages = queue.Queue()
        threading.Thread.__init__(self)

    def StopThread(self):
        with self.data_lock:
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
        with self.mutagen_lock:
            stop_sessions()

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

    def getErrCount(self):
        with self.data_lock:
            return self.session_errcount

    def setErrCount(self, session_errcount_):
        with self.data_lock:
            self.session_errcount = session_errcount_

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
                time.sleep(1)
        except Exception as e:
            append_log(LOG_PATH + '/error.log', traceback.format_exc())
            raise e

    def update(self):
        (session_log, session_status, conflicts) = get_session_status()
        self.setStatusLog(session_log)
        session_errcount = self.getErrCount()
        session_ok = self.getOk()
        with self.mutagen_lock:
            for sname in session_config:
                append_debug_log(5, 'Status ' + sname + ': ' + format_dict(session_status[sname]))
                status = session_status[sname]['status']
                # Set session_ok to -1 if connecting for a long time or no session or duplicate
                if not status or status.startswith(status_connecting) or session_status[sname]['duplicate']:
                    session_errcount[sname] += 1
                    if session_errcount[sname] > 1:
                        if not status:
                            session_ok[sname] = -1
                        else:
                            session_ok[sname] = -2
                    if session_errcount[sname] > SESSION_MAX_ERRORS:
                        if self.getEnabled():
                            if session_status[sname]['status']:
                                notify(sname, 'Restarting: ' + session_status[sname]['status'])
                            append_log(LOG_PATH + '/restart.log',
                                        session_log + '\nRestarting: ' + sname)
                            restart_session(sname)
                            session_errcount[sname] = 0
                # If ready, set session_ok to 100
                elif status.startswith(status_ready):
                    session_errcount[sname] = 0
                    session_ok[sname] = 100
                # If working, set session_ok to 70
                elif status.startswith(status_working):
                    session_errcount[sname] = 0
                    session_ok[sname] = 70
                # If there are problems, decrease session_ok to 30 if it is greater
                if session_status[sname]['problems']:
                    session_ok[sname] = min(session_ok[sname], 30)
                # If there are conflicts, decrease session_ok to 60 if it is greater
                if session_status[sname]['conflicts']:
                    session_ok[sname] = min(session_ok[sname], 60)
        self.setStatus(session_status)
        self.setConflicts(conflicts)
        self.setErrCount(session_errcount)
        self.setOk(session_ok)


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
        worst_ok = self.get_worst_ok()
        if worst_ok > 70:
            self.set_icon('img/green.png', TRAY_TOOLTIP + ': watching for changes')
        elif worst_ok > 60:
            self.set_icon('img/green-sync.png', TRAY_TOOLTIP + ': syncing')
        elif worst_ok > 30:
            self.set_icon('img/green-conflict.png', TRAY_TOOLTIP + ': conflicts')
        elif worst_ok > 0:
            self.set_icon('img/green-error.png', TRAY_TOOLTIP + ': problems')
        elif worst_ok == 0:
            self.set_icon('img/lightgray.png', TRAY_TOOLTIP + ': waiting for status...')
        elif worst_ok == -1:
            self.set_icon('img/darkgray.png', TRAY_TOOLTIP + ': not running')
        elif worst_ok == -2:
            self.set_icon('img/orange.png', TRAY_TOOLTIP + ': error')

    def CreatePopupMenu(self):
        worst_ok = self.get_worst_ok()
        menu = wx.Menu()
        create_menu_item(menu, 'Restart Mutagen sessions', self.on_start)
        create_menu_item(menu, 'Stop Mutagen sessions', self.on_stop)
        menu.AppendSeparator()
        create_menu_item(menu, 'Exit MutagenMon', self.on_exit)
        return menu

    def set_icon(self, path, title):
        self.title = title
        if self.cur_icon == path:
            return
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
            fsize1, ftime1 = get_size_time_ssh(session_status, sname, 1, fname)
        else:
            fsize1 = os.path.getsize(dir_and_name(session_status[sname]['url1'], fname))
            ftime1 = datetime.datetime.fromtimestamp(
                os.path.getmtime(dir_and_name(session_status[sname]['url1'], fname))
            ).strftime("%Y-%m-%d %H:%M:%S")
        if session_status[sname]['transport2'] == 'ssh':
            fsize2, ftime2 = get_size_time_ssh(session_status, sname, 2, fname)
        else:
            fsize2 = os.path.getsize(dir_and_name(session_status[sname]['url2'], fname))
            ftime2 = datetime.datetime.fromtimestamp(
                os.path.getmtime(dir_and_name(session_status[sname]['url2'], fname))
            ).strftime("%Y-%m-%d %H:%M:%S")
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
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            sel = dlg.GetSelection()
            if sel == 0:
                if self.visual_merge(sname, fname, session_status):
                    return False
            if sel == 1:
                if session_status[sname]['transport1'] == session_status[sname]['transport2']:
                    messageBox('Warning', 'Currently "A win" and "B win" strategies are not supported for local-local or ssh-ssh sessions. You can either use visual merge and change first file, or contribute to the project and rewrite code where you will find this message')
                scp(
                    dir_and_name(session_status[sname]['url1'], fname),
                    dir_and_name(session_status[sname]['url2'], fname))
                return False
            if sel == 2:
                if session_status[sname]['transport1'] == session_status[sname]['transport2']:
                    messageBox('Warning', 'Currently "A win" and "B win" strategies are not supported for local-local or ssh-ssh sessions. You can either use visual merge and change first file, or contribute to the project and rewrite code where you will find this message')
                scp(
                    dir_and_name(session_status[sname]['url2'], fname),
                    dir_and_name(session_status[sname]['url1'], fname))
                return False
        if res == wx.ID_CANCEL:
            return False
        return True

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
                while self.resolve_single(sname, conflict, session_status):
                    pass

    def on_left_down(self, event):
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
        self.monitor.RestartMutagen()

    def on_stop(self, event):
        self.monitor.DisableMutagen()

    def on_exit(self, event):
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
