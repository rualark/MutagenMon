from ..local.run import *


def make_diff_path(url, fname, id):
    if ':/' not in url:
        return dir_and_name(url, fname)
    lname = 'diff/remote' + str(id)
    scp(dir_and_name(url, fname), lname)
    return lname


def remote_escape(st):
    return st.replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)').replace('&', '\\&')


def escape_if_remote(st):
    if ':/' in st:
        return remote_escape(st)
    else:
        return st


def scp(name1, name2):
    return run(
        [cfg('SCP_PATH'), escape_if_remote(name1), escape_if_remote(name2)],
        shell=True,
        interactive_error=True)


def ssh_command(server, command):
    return run(
        [cfg('SSH_PATH'), server, command],
        shell=True,
        interactive_error=True)


def get_size_time_ssh(session_status, sname, i, fname):
    res = ssh_command(
        session_status[sname]['server' + str(i)],
        "stat -c '%Y %s' " + remote_escape(dir_and_name(session_status[sname]['dir' + str(i)], fname)))
    ftime = int(res.split(' ')[0].strip())
    fsize = int(res.split(' ')[1].strip())
    return fsize, ftime


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

