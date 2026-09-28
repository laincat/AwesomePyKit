# coding: utf-8

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from ..ui import *

from ..logic.messagebox import MessageBox

# 原作者自 2024-10 起停止更新，本仓库继续维护。因此：
#   · 界面上的作者栏区分为「原作者」与「维护者」（文案在 .ui 里）；
#   · 各处的链接指向本仓库 —— 原仓库不会再有更新，把用户引过去只会造成困惑。
_REPO_GITHUB = "https://github.com/laincat/AwesomePyKit"


class AboutWindow(Ui_about_window, QMainWindow):
    def __init__(self, parent, appversion: str):
        self.__parent = parent
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.__v = appversion
        self.uiLabel_app_version.installEventFilter(self)
        self.uiLabel_app_version.setText(f"Awespykit - {self.__v}")
        self.uiLabel_license.installEventFilter(self)
        self.uiLabel_issue_github.installEventFilter(self)
        self.uiLabel_issue_gitee.installEventFilter(self)
        self.uiLabel_source_github.installEventFilter(self)
        self.uiLabel_source_gitee.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonRelease:
            hyperlink = None
            if obj == self.uiLabel_app_version:
                hyperlink = f"{_REPO_GITHUB}/releases"
            elif obj == self.uiLabel_issue_gitee:
                hyperlink = f"{_REPO_GITHUB}/issues"
            elif obj == self.uiLabel_issue_github:
                hyperlink = f"{_REPO_GITHUB}/issues"
            elif obj == self.uiLabel_source_gitee:
                hyperlink = _REPO_GITHUB
            elif obj == self.uiLabel_source_github:
                hyperlink = _REPO_GITHUB
            elif obj == self.uiLabel_license:
                hyperlink = f"{_REPO_GITHUB}/blob/main/LICENSE"
            if hyperlink is not None and not QDesktopServices.openUrl(
                QUrl(hyperlink)
            ):
                MessageBox("提示", "链接打开失败！", QMessageBox.Warning).exec_()
        return super(AboutWindow, self).eventFilter(obj, event)

    def display(self):
        self.showNormal()
