#!/usr/bin/env python
# coding=utf-8
# This script uses python3
# Optimized for mutagen.io version 0.10
import wx.adv
import wx
import sys

from mutagenmonlib.local.file import append_log, load_config, cfg
from mutagenmonlib.wx.wx import errorBox
from mutagenmonlib.wx.icon import TaskBarIcon


def my_excepthook(exctype, value, tb):
    est = str(exctype) + '\n' + str(value) + '\n' + str(tb)
    append_log(cfg('LOG_PATH') + '/error.log', est)
    errorBox('MutagenMon exception', est)


class App(wx.App):
    def OnInit(self):
        frame=wx.Frame(None)
        self.SetTopWindow(frame)
        TaskBarIcon(frame)
        return True


def main():
    load_config("config/config_mutagenmon.json")
    if not cfg('DEBUG_EXCEPTIONS_TO_CONSOLE'):
        sys.excepthook = my_excepthook
    app = App(False)
    app.MainLoop()


if __name__ == '__main__':
    main()
