import time
import threading
import queue
import traceback
from copy import copy

from mutagenmonlib.remote.resolve import *
from mutagenmonlib.remote.mutagen import *
from mutagenmonlib.local.file import *
from mutagenmonlib.wx.wx import *

status_connecting = (
    'Connecting to',
    'Waiting to connect',
    'Unknown')
status_scanning = (
    'Scanning files')
status_working = (
    'Waiting 5 seconds for rescan',
    'Reconciling changes',
    'Staging files on',
    'Applying changes',
    'Saving archive')
status_ready = (
    'Watching for changes')


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
        self.status_log_time = 0
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
            self.status_log_time = time.time()

    def getStatusLog(self):
        with self.data_lock:
            return self.status_log, self.status_log_time

    def run(self):
        try:
            while True:
                with self.data_lock:
                    if self.stopping:
                        return
                self.update()
                self.restart_mutagen()
                self.stop_mutagen()
                time.sleep(cfg('MUTAGEN_POLL_PERIOD') / 1000.0)
        except Exception as e:
            est = traceback.format_exc()
            append_log(cfg('LOG_PATH') + '/error.log', est)
            errorBox('MutagenMon error', est)
            raise e

    def stop_mutagen(self):
        if self.getEnabled():
            return
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_status:
                if not session_status[sname]:
                    continue
                status = session_status[sname]['status']
                if status:
                    try:
                        stop_session(sname)
                    except Exception as e:
                        pass


    def restart_mutagen(self):
        if not self.getEnabled():
            return
        session_err = copy(self.getErr())
        session_log, session_log_time = self.getStatusLog()
        session_status = self.getStatus()
        with self.mutagen_lock:
            for sname in session_config():
                # Set session_code to -1 if connecting for a long time or no session or duplicate
                need_restart = False
                restart_msg = ''
                if not session_status[sname]:
                    if session_err[sname] > cfg('SESSION_MAX_NOSESSION'):
                        need_restart = True
                        restart_msg = 'Restarting'
                else:
                    status = session_status[sname]['status']
                    if session_status[sname]['duplicate']:
                        if session_err[sname] > cfg('SESSION_MAX_DUPLICATE'):
                            need_restart = True
                            restart_msg = 'Restarting duplicate'
                            self.messages.put({
                                'type': 'notify',
                                'title': sname,
                                'text': restart_msg + ': ' + status})
                    elif status.startswith(status_connecting):
                        if session_err[sname] > cfg('SESSION_MAX_ERRORS'):
                            need_restart = True
                            restart_msg = 'Restarting connection'
                            if cfg('NOTIFY_RESTART_CONNECTION'):
                                self.messages.put({
                                    'type': 'notify',
                                    'title': sname,
                                    'text': restart_msg + ': ' + status})
                if need_restart:
                    append_log(cfg('LOG_PATH') + '/restart.log',
                               session_log + '\n' + restart_msg + ': ' + sname)
                    restart_session(sname)
                    session_err[sname] = 0
        self.setErr(session_err)

    def update(self):
        try:
            (session_log, session_status, conflicts) = get_session_status()
        except Exception as e:
            """
            self.messages.put({
                'type': 'notify',
                'title': 'Error getting mutagen status',
                'text': repr(e)})
            """
            return
        self.setStatusLog(session_log)
        session_err = copy(self.getErr())
        session_laststatus = copy(self.getLastStatus())
        session_code = copy(self.getCode())
        for sname in session_config():
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
            # If scanning, set session_code to 65
            elif status.startswith(status_scanning):
                session_err[sname] = 0
                session_code[sname] = 65
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
            if self.auto_resolve_history[sfname][0] < now - cfg('AUTORESOLVE_HISTORY_AGE'):
                append_debug_log(10, 'Removing from autoresolve history: ' + sfname)
                del self.auto_resolve_history[sfname]

    def auto_resolve(self, conflicts):
        session_status = self.getStatus()
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
                    self.auto_resolve_single(sname, conflict, fname, session_status))

    def auto_resolve_single(self, sname, conflict, fname, session_status):
        append_debug_log(60, 'Trying to autoresolve ' + sname + ':' + fname)
        for ar in cfg('AUTORESOLVE'):
            result = re.search(ar['filepath'], fname)
            if result is None:
                continue
            resolve(session_status, sname, fname, ar['resolve'], auto=True)
            conflict['autoresolved'] = True
            est = 'Auto-resolved conflict: ' + ar['resolve']
            append_debug_log(40, est + ' - ' + sname + ':' + fname)
            if cfg('NOTIFY_AUTORESOLVE'):
                self.messages.put({
                    'type': 'notify',
                    'title': est,
                    'text': sname + ': ' + fname})
            return True
        return False


