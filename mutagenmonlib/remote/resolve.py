import wx.adv

from .monitor import *


def visual_merge(sname, fname, session_status):
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


def resolve_single(sname, conflict, session_status):
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
        str(fsize1) + ' bytes, ' + str(ftime1) + '\n\n' + \
        'B: ' + session_status[sname]['url2'] + '\n' + \
        str(fsize2) + ' bytes, ' + str(ftime2)
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
            if visual_merge(sname, fname, session_status):
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


def resolve_all(session_status, conflicts):
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
            while not resolve_single(sname, conflict, session_status):
                pass


def get_conflict_names(conflicts, session_code):
    cnames = set()
    for sname in session_config():
        if session_code[sname] and conflicts[sname]:
            for conflict in conflicts[sname]:
                if conflict['autoresolved']:
                    continue
                cnames.add(sname + ':' + conflict['aname'])
    return cnames

