import wx

def create_menu_item(menu, label, func):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


def create_menu_item_disabled(menu, label):
    item = wx.MenuItem(menu, -1, label)
    item.Enable(False)
    menu.Append(item)
    return item


def info_message(st):
    d = wx.Dialog(None, style=wx.CAPTION)
    d.SetTitle(st)
    d.SetSize((300, 50))
    d.CenterOnScreen()
    d.Show(True)
    return d


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


