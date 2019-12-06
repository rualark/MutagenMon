import re
import json
import os
from shutil import copyfile

from mutagenmonlib.wx.wx import *
from mutagenmonlib.local.lib import *

config = {}


def cfg(key):
    return config[key]


def file_to_list_strip(filename):
    with open(filename) as f:
        fa = f.readlines()
    return [x.strip() for x in fa]


def load_config(fname):
    global config
    fa = file_to_list_strip(fname)
    st = '\n'.join(fa)
    st = re.sub(r"#.*?\n", "", st)
    config = json.loads(st)
    config['MUTAGEN_PROFILE_DIR'] = config['MUTAGEN_PROFILE_DIR'].replace("%USERPROFILE%", os.getenv("USERPROFILE"))


def dir_and_name(dname, fname):
    # dname = dname.replace("\\", '/')
    if dname[-1:] == '/':
        dname = dname[:-1]
    if fname[0] == '/':
        fname = fname[1:]
    return dname + '/' + fname


def dir_and_name_local(dname, fname):
    # dname = dname.replace("/", os.path.sep)
    if dname[-1:] == os.path.sep:
        dname = dname[:-1]
    if fname[0] == os.path.sep:
        fname = fname[1:]
    return dname + os.path.sep + fname


def write_file(fname, st):
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(st + '\n')


def append_file(fname, st):
    with open(fname, 'a+', encoding='utf-8') as f:
        f.write(st + '\n')


def append_log(fname, st):
    append_file(fname, '[' + format_current_datetime() + '] ' + str(st))


def resolve_log(sname, session_status, fname, method, auto=False):
    st = ''
    if auto:
        st += ' [AUTO]'
    st += '\n'
    st += sname + '\n'
    st += session_status[sname]['url1'] + '\n'
    st += session_status[sname]['url2'] + '\n'
    st += fname + '\n'
    st += method + '\n'
    append_log('log/resolve.log', st)


def append_debug_log(level, st):
    st2 = '[' + format_current_datetime() + '] ' + str(st)
    if level <= config['DEBUG_LEVEL']:
        append_file(config['LOG_PATH'] + '/debug.log', st2)
        print(st2)


def copy_local(name1, name2):
    try:
        copyfile(name1, name2)
    except Exception as e:
        est = 'Error copying file ' + name1 + ' to ' + name2 + ': ' + repr(e)
        errorBox('MutagenMon error', est)
        append_log(config['LOG_PATH'] + '/error.log', est)

