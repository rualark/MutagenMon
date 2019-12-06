import subprocess

from mutagenmonlib.local.file import *


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
        append_log(cfg('LOG_PATH') + '/error.log', est)
        return est
    except Exception as e:
        est = str(ca) + '\n' + repr(e)
        if interactive_error:
            errorBox('MutagenMon error', est)
        append_log(cfg('LOG_PATH') + '/error.log', est)
        return est


def run_merge(name1, name2):
    return run(
        [cfg('MERGE_PATH'), name1, name2],
        shell = False,
        interactive_error = True)


