import wx.adv
import signal

from ..remote.resolve import *
from ..remote.monitor import *


class GracefulKiller:
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self,signum, frame):
        self.kill_now = True


class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.killer = GracefulKiller()
        self.cur_icon = ''
        self.worst_code = 0
        self.restarting = False
        self.frame = frame
        get_sessions()
        self.session_archive_time = init_session_default(0)
        self.session_archive_time_grace = init_session_default(0)
        self.session_archive_time_grace_updated = init_session_default(0)
        super(TaskBarIcon, self).__init__()
        self.title = ''
        self.set_icon('img/lightgray.png', cfg('TRAY_TOOLTIP') + ': waiting for status...')
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
        self.exiting = False
        self.timer = wx.Timer(self)
        self.had_conflicts = set()
        self.Bind(wx.EVT_TIMER, self.update, self.timer)
        self.timer.Start(1000)
        self.cycle = 0
        self.monitor = Monitor(cfg('START_ENABLED'))
        self.monitor.start()

    def notify(self, title, text):
        try:
            if not self.ShowBalloon(title, text, msec=5000):
                nm = wx.adv.NotificationMessage(title, text)
                nm.Show()
        except:
            pass

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

    def notify_conflicts(self):
        if not cfg('NOTIFY_CONFLICTS'):
            return
        cnames = get_conflict_names(self.monitor.getConflicts(), self.monitor.getCode())
        append_debug_log(60, "CNAMES:" + str(cnames) + ' old: ' + str(self.had_conflicts))
        if cnames.difference(self.had_conflicts):
            cst = '\n'.join(cnames.difference(self.had_conflicts))
            self.notify('New conflicts', cst)
        if cnames or self.worst_code == 100:
            self.had_conflicts = cnames

    def check_restarting(self):
        status = self.monitor.getStatus()
        for sname in status:
            if status[sname]:
                return
        self.restart_process()

    def update(self, event):
        if self.exiting:
            return
        if self.restarting:
            self.check_restarting()
        self.cycle += 1
        self.check_killer()
        self.update_icon()
        self.get_messages()
        self.notify_conflicts()

    def restart_process(self):
        self.exiting = True
        append_log(cfg('LOG_PATH') + '/error.log', 'Restarting application')
        # self.notify(self.title, 'Icon crashed. Restarting application')
        subprocess.Popen(['mutagenmon'], shell=True)
        self.exit()

    def update_icon(self):
        updated_profile = self.check_mutagen_profile_dir()
        append_debug_log(90, 'Updating worst_code')
        self.worst_code = get_worst_code(self.monitor.getCode())
        now = time.time()
        session_log, session_log_time = self.monitor.getStatusLog()
        if self.worst_code > 70 and not updated_profile:
            if self.monitor.getEnabled():
                if now - session_log_time > cfg('STATUS_MAX_LAG'):
                    self.set_icon('img/green-timeout.png', cfg('TRAY_TOOLTIP') + ': mutagen is watching for changes (stale)')
                else:
                    if updated_profile:
                        self.set_icon('img/green-success.png', cfg('TRAY_TOOLTIP') + ': mutagen is watching for changes (updated)')
                    else:
                        self.set_icon('img/green.png', cfg('TRAY_TOOLTIP') + ': mutagen is watching for changes')
            else:
                self.set_icon('img/green-stop.png', cfg('TRAY_TOOLTIP') + ': mutagen is stopping')
        elif self.worst_code > 65:
            if now - session_log_time > cfg('STATUS_MAX_LAG'):
                self.set_icon('img/green-timeout.png', cfg('TRAY_TOOLTIP') + ': mutagen is syncing (stale)')
            else:
                if updated_profile:
                    self.set_icon('img/green-success.png', cfg('TRAY_TOOLTIP') + ': mutagen is syncing (updated)')
                else:
                    self.set_icon('img/green-sync.png', cfg('TRAY_TOOLTIP') + ': mutagen is syncing')
        elif self.worst_code > 60:
            if now - session_log_time > cfg('STATUS_MAX_LAG'):
                self.set_icon('img/green-timeout.png', cfg('TRAY_TOOLTIP') + ': mutagen is scanning (stale)')
            else:
                if updated_profile:
                    self.set_icon('img/green-success.png',
                                  cfg('TRAY_TOOLTIP') + ': mutagen is scanning (updated)')
                else:
                    self.set_icon('img/green-scan.png', cfg('TRAY_TOOLTIP') + ': mutagen is scanning')
        elif self.worst_code > 30:
            self.set_icon('img/green-conflict.png', cfg('TRAY_TOOLTIP') + ': conflicts')
        elif self.worst_code > 0:
            self.set_icon('img/green-error.png', cfg('TRAY_TOOLTIP') + ': problems')
        elif self.worst_code == 0:
            self.set_icon('img/lightgray.png', cfg('TRAY_TOOLTIP') + ': mutagen is waiting for status...')
        elif self.worst_code == -1:
            if self.monitor.getEnabled():
                self.set_icon('img/darkgray-restart.png', cfg('TRAY_TOOLTIP') + ': mutagen is not running (starting)')
            else:
                self.set_icon('img/darkgray.png', cfg('TRAY_TOOLTIP') + ': mutagen is not running (disabled)')
        elif self.worst_code == -2:
            if self.monitor.getEnabled():
                self.set_icon('img/orange-restart.png', cfg('TRAY_TOOLTIP') + ': error (starting)')
            else:
                self.set_icon('img/orange.png', cfg('TRAY_TOOLTIP') + ': error (disabled)')
        append_debug_log(40, 'Updated worst_code: ' + str(self.worst_code))
        self.show_profile_updates()

    def show_profile_updates(self):
        if not cfg('NOTIFY_MUTAGEN_PROFILE_UPDATE'):
            return
        for sname in session_config():
            if self.session_archive_time_grace_updated[sname]:
                self.notify('Updated', sname)

    def check_mutagen_profile_dir(self):
        if not cfg('MUTAGEN_PROFILE_DIR_WATCH_PERIOD'):
            return
        if self.cycle % cfg('MUTAGEN_PROFILE_DIR_WATCH_PERIOD'):
            return
        status = self.monitor.getStatus()
        updating = False
        for sname in session_config():
            self.session_archive_time_grace_updated[sname] = False
            if not status[sname]:
                continue
            mtime = 0
            try:
                mtime = os.path.getmtime(
                    dir_and_name(cfg('MUTAGEN_PROFILE_DIR'), 'archives\\' + status[sname]['id']))
            except:
                # Reset timestamp to ignore first change in the future
                self.session_archive_time[sname] = 0
                self.session_archive_time_grace[sname] = 0
                continue
            if not self.session_archive_time_grace[sname]:
                self.session_archive_time_grace[sname] = mtime
                continue
            if self.session_archive_time_grace[sname] + cfg('MUTAGEN_PROFILE_GRACE') < mtime:
                self.session_archive_time_grace[sname] = mtime
                self.session_archive_time_grace_updated[sname] = True
            if not self.session_archive_time[sname]:
                self.session_archive_time[sname] = mtime
                continue
            if self.session_archive_time[sname] < mtime:
                self.session_archive_time[sname] = mtime
                updating = True
        return updating

    def CreatePopupMenu(self):
        menu = wx.Menu()
        if self.restarting:
            create_menu_item_disabled(menu, 'Restarting...')
        else:
            create_menu_item(menu, 'Reload config && restart mutagen', self.on_restart)
            if self.monitor.getEnabled():
                create_menu_item(menu, 'Stop Mutagen sessions', self.on_stop)
            else:
                create_menu_item(menu, 'Start Mutagen sessions', self.on_start)
            menu.AppendSeparator()
            create_menu_item(menu, 'Show status', self.on_left_down)
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
        # if self.cur_icon == path:
        #     return
        self.cur_icon = path
        icon = wx.Icon(path)
        self.SetIcon(icon, title)
        if not self.IsIconInstalled():
            self.exiting = True
            append_log(cfg('LOG_PATH') + '/error.log', 'Icon crashed. Restarting application')
            # self.notify(self.title, 'Icon crashed. Restarting application')
            subprocess.Popen(['mutagenmon'], shell=True)
            self.exit()
        append_debug_log(85, 'Icon state 2: ' +
                         str(self.IsAvailable()) +
                         str(self.IsIconInstalled()) +
                         str(self.IsOk()) +
                         str(self.IsUnlinked()))

    def get_nice_log(self):
        st, session_log_time = self.monitor.getStatusLog()
        st = st.replace('Conflicts:', '')
        st = re.sub(r"Identifier: .*?\n", "", st)
        st = re.sub(r"    \(α\).*?\n", "", st)
        st = re.sub(r"    \(β\).*?\n", "", st)
        #st = re.sub(r"    \(β\).*?$", "", st)
        st = st.replace('\n\n', '\n')
        st = st.replace('\n\n', '\n')
        st = st.strip()
        conflicts = self.monitor.getConflicts()
        session_code = self.monitor.getCode()
        cst = ''
        for sname in session_config():
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
        if get_conflict_names(self.monitor.getConflicts(), self.monitor.getCode()):
            dlg = wx.MessageDialog(
                self.frame,
                st,
                self.title,
                wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            dlg.SetOKCancelLabels("Resolve conflicts", "Cancel")
            res = dlg.ShowModal()
            if res == wx.ID_OK:
                resolve_all(self.monitor.getStatus(), self.monitor.getConflicts())
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

    def on_restart(self, event):
        self.restarting = True
        self.on_stop(event)

    def on_exit(self, event):
        self.exit()

    def exit(self):
        append_debug_log(5, 'Exiting')
        self.monitor.StopThread()
        wx.CallAfter(self.Destroy)
        self.frame.Close()


