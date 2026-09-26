# coding: utf-8

from PyQt5.QtWidgets import *


class MessageBox(QMessageBox):
    """
    点击按钮后返回该按钮在参数中的次序值

    多按钮：关闭窗口返回值跟随'reject'按钮次序值

    只有一个按钮：直接关闭窗口返回 0

    多按钮的情况下，'reject'按钮在最右侧

    有'destructive'按钮，无'reject'按钮，窗口不可关闭
    """

    def __init__(
        self,
        title,
        message,
        icon=None,
        buttons=(("accept", "确定"),),
        parent=None,
    ):
        if icon is None:
            icon = QMessageBox.Information
        super().__init__(icon, title, message, parent=parent)
        self._buttons = buttons
        self.__set_push_buttons()

    def __set_push_buttons(self):
        for btn in self._buttons:
            role, text = btn
            if role == "accept":
                self.addButton(text, QMessageBox.AcceptRole)
            elif role == "destructive":
                self.addButton(text, QMessageBox.DestructiveRole)
            elif role == "reject":
                self.setDefaultButton(
                    self.addButton(text, QMessageBox.RejectRole)
                )

    def get_role(self):
        return self.exec_()


def save_config_or_warn(config, parent=None):
    """保存配置；失败时明确告诉用户，而不是静默丢弃。

    配置里存着用户辛苦调好的东西：窗口布局、已添加的 Python 环境列表、
    打包工具的成套配置……写失败的原因（磁盘满、目录只读、被杀毒软件拦截）
    用户往往察觉不到，只会觉得「设置下次打开又没了」。

    返回 True 表示保存成功。
    """
    # 兼容旧签名：部分调用点可能没有返回值
    if config.save_config() is False:
        MessageBox(
            "提示",
            "配置保存失败。\n\n"
            "可能是配置目录没有写入权限，或磁盘空间不足。\n"
            "本次的界面设置与选项将不会被记住，但程序功能不受影响。",
            QMessageBox.Warning,
            parent=parent,
        ).exec_()
        return False
    return True
