# coding: utf-8

__license__ = "GNU General Public License v3 (GPLv3)"

import sys
from functools import partial

from fastpip import VERNUM
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# 这个文件是本程序的入口，需要同时支持三种启动方式：
#   1. 控制台脚本 rpk（由 pyproject.toml 的 [project.scripts] 生成）
#   2. python -m awespykit
#   3. 直接运行本文件：python src/awespykit/runpykit.py（以及 PyInstaller 打包后
#      以本文件为入口脚本运行）
#
# 第 3 种方式没有包上下文（__package__ 为空），相对导入会直接失败，所以本文件
# 一律使用「以包名开头」的绝对导入。这样无论以哪种方式启动，导入都能成立，
# 也不需要额外做一次 runpy 重定向 —— 那种做法在包路径推导不如预期时，会抛出
# “No module named 'awespykit'” 这种指向前提条件、很难排查的错误。
#
# 直接运行脚本时，包目录的父目录（即项目的 src 目录）需要位于 sys.path 上。
# 这里按 __file__ 推导并补上；推导不出来时不做任何事，让下面的导入语句给出
# 原本的错误信息（而不是被这层逻辑掩盖）。
if __package__ in (None, ""):
    from os import path as _path

    _pkg_parent = _path.dirname(_path.dirname(_path.abspath(__file__)))
    if _path.isdir(_path.join(_pkg_parent, "awespykit")) and (
        _pkg_parent not in sys.path
    ):
        sys.path.insert(0, _pkg_parent)

from awespykit.__info__ import *
from awespykit.com import *
from awespykit.logic import *
from awespykit.res.res import *
from awespykit.settings import *
from awespykit.ui import *
from awespykit.utils.thmt import *

if VERNUM[0] != REQ_FPVER[0]:
    raise Exception(f"当前环境的 fastpip 主版本号({VERNUM[0]})非本程序要求：{REQ_FPVER[0]}")
if VERNUM[1] < REQ_FPVER[1]:
    raise Exception(f"当前环境的 fastpip 次版本号({VERNUM[1]})低于本程序要求：{REQ_FPVER[1]}")
elif VERNUM[1] == REQ_FPVER[1] and VERNUM[2] < REQ_FPVER[2]:
    raise Exception(f"当前环境的 fastpip 修订号({VERNUM[2]})低于本程序要求：{REQ_FPVER[2]}")
################################################################
# 版本号的定义：主版本号.次版本号.修订号，对 fastpip 的版本号要求：
# 1. 主版本号必须与要求一致，次版本号必须大于等于要求的次版本号
# 2. 如次版本号等于要求的次版本号，则修订号必须大于等于要求的修订号
################################################################

_IS_MAIN_MODULE = False


class MainEntrance(Ui_main_entrance, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowFlags(
            Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
        )
        self.__config = MainEntranceConfig()
        self.__themes: Themes[ThemeData] = PreThemeList
        self.setWindowTitle(APP_NAME)
        self.__about_window = AboutWindow(
            self, PRE_VER if _IS_MAIN_MODULE else VERSION
        )
        self.__pkgmgr_win = PackageManagerWindow(self)
        self.__pyitool_win = PyinstallerToolWindow(self)
        self.__indexmgr_win = IndexUrlManagerWindow(self)
        self.__pkgdl_win = PackageDownloadWindow(self)
        self.__cloudfunction_win = CloudFunctionWindow(self)
        self.__setup_other_widgets()
        self.__theme_action(self.__config.selected_thm)

    def display(self):
        self.resize(*self.__config.window_size)
        self.showNormal()

    def __store_window_size(self):
        if self.isMaximized() or self.isMinimized():
            return
        self.__config.window_size = self.width(), self.height()

    def closeEvent(self, event: QCloseEvent):
        if (
            self.__pkgmgr_win.thread_repo.is_empty()
            and self.__pyitool_win.thread_repo.is_empty()
            and self.__pkgdl_win.thread_repo.is_empty()
            and self.__cloudfunction_win.thread_repo.is_empty()
        ):
            event.accept()
        else:
            user_messagebox_role = MessageBox(
                "警告",
                "有后台任务正在运行，是否强制结束任务？",
                QMessageBox.Warning,
                (("accept", "强制退出"), ("reject", "取消")),
                self,
            ).exec_()
            if user_messagebox_role == 0:
                self.__pkgdl_win.thread_repo.kill_all()
                self.__pkgmgr_win.thread_repo.kill_all()
                self.__pyitool_win.thread_repo.kill_all()
                self.__cloudfunction_win.thread_repo.kill_all()
                event.accept()
            else:
                event.ignore()
        self.__store_window_size()
        save_config_or_warn(self.__config, self)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.close()

    def _show_about(self):
        self.__about_window.display()

    def __setup_other_widgets(self):
        self.uiPushButton_pkg_mgr.setIcon(QIcon(":/manage.png"))
        self.uiPushButton_pkg_mgr.clicked.connect(self.__pkgmgr_win.display)
        self.uiPushButton_pyi_tool.setIcon(QIcon(":/bundle.png"))
        self.uiPushButton_pyi_tool.clicked.connect(self.__pyitool_win.display)
        self.uiPushButton_index_mgr.setIcon(QIcon(":/indexurl2.png"))
        self.uiPushButton_index_mgr.clicked.connect(self.__indexmgr_win.display)
        self.uiPushButton_pkg_dload.setIcon(QIcon(":/download.png"))
        self.uiPushButton_pkg_dload.clicked.connect(self.__pkgdl_win.display)
        self.uiPushButton_cloudfunction.setIcon(QIcon(":/cloudfunction.png"))
        self.uiPushButton_cloudfunction.clicked.connect(
            self.__cloudfunction_win.display
        )
        self.uiPushButton_settings.setIcon(QIcon(":/settings.png"))
        # noinspection PyTypeChecker
        menu_setstyle = QMenu("主题", self)
        for theme in self.__themes:
            action = QAction(theme.name, self)
            action.triggered.connect(partial(self.__theme_action, theme.index))
            menu_setstyle.addAction(action)
        menu_main_settings = QMenu(self)
        menu_main_settings.setObjectName("settings_menu")
        menu_main_settings.addMenu(menu_setstyle)
        menu_main_settings.addAction("关于", self._show_about)
        self.uiPushButton_settings.setMenu(menu_main_settings)

    def __theme_action(self, index: int):
        self.__config.selected_thm = self.__themes.apply_theme(index)


def runpykit_and_sysexit():
    translator = QTranslator()
    translator.load(":/trans/widgets_zh-CN.qm")
    _App.installTranslator(translator)
    _App.setWindowIcon(QIcon(":/icon2_64.png"))
    main = MainEntrance()
    main.display()
    sys.exit(_App.exec_())


if __name__ == "__main__":
    _IS_MAIN_MODULE = True
    runpykit_and_sysexit()
