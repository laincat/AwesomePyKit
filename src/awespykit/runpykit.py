# coding: utf-8

__license__ = "GNU General Public License v3 (GPLv3)"

import sys
from functools import partial

# ── 启动引导 ────────────────────────────────────────────────────────────────
#
# 本程序需要同时支持三种启动方式：
#   1. 控制台脚本 rpk（由 pyproject.toml 的 [project.scripts] 生成）
#   2. python -m awespykit
#   3. 直接运行本文件：python src/awespykit/runpykit.py
#      （以及 PyInstaller 以本文件为入口脚本打包后的 exe）
#
# 第 3 种没有包上下文（__package__ 为空），相对导入会直接失败，因此本文件一律
# 使用「以包名开头」的绝对导入。
#
# 但绝对导入要求 src 目录位于 sys.path 上。前两种方式由安装器或 Python 自身
# 保证；直接运行脚本时没有这层保证，所以在这里补上 —— 而且必须在导入
# awespykit 与 fastpip 之前执行（fastpip 也放在 src/ 下，是本仓库 vendored 的
# 副本，不从 PyPI 安装）。
if __package__ in (None, ""):
    from os import path as _path

    # __file__ 是 .../src/awespykit/runpykit.py，上溯两级即 src
    _src_dir = _path.dirname(_path.dirname(_path.abspath(__file__)))
    if _path.isdir(_path.join(_src_dir, "awespykit")) and (
        _src_dir not in sys.path
    ):
        sys.path.insert(0, _src_dir)

from fastpip import VERNUM
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from awespykit.__info__ import *
from awespykit.com import *
from awespykit.logic import *
from awespykit.res.res import *
from awespykit.settings import *
from awespykit.ui import *
from awespykit.utils.thmt import *

# ── 依赖版本自检 ────────────────────────────────────────────────────────────
#
# fastpip 是本程序的核心依赖，版本不符时必须停下，否则会在后续操作里以各种
# 难以理解的方式出错（例如少了某个方法、返回结构变了）。
#
# 但「直接 raise」在这个程序里是个糟糕的选择：打包成 exe 时 console=False，
# 没有控制台窗口，异常信息写在 stderr 里谁也看不到 —— 用户双击图标后只会
# 看到进程一闪而过，完全没有提示，无从排查（典型的「双击没反应」）。
#
# 因此改成用对话框把原因和解决办法直接告诉用户，再退出。
# 判断逻辑放在 com/requires.py 里，便于单独测试。
_version_error = check_fastpip_version(VERNUM)
if _version_error:
    try:
        _error_app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            f"{APP_NAME} 无法启动",
            f"{_version_error}\n\n"
            f"如果问题持续存在，请重新安装本程序。",
        )
    except Exception:
        # 连图形界面都起不来时，退回命令行输出
        print(f"{APP_NAME} 无法启动：\n{_version_error}", file=sys.stderr)
    sys.exit(1)

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
        # 配置里是 (0, 0) 时表示从未记录过用户调整，按内容自然尺寸显示。
        # 启动窗口的按钮是横向排列的，自然尺寸约为 324x58；若强行用写死的
        # 竖长条尺寸，按钮会被挤成竖排，外观与预期不符。
        width, height = self.__config.window_size
        if width > 0 and height > 0:
            self.resize(width, height)
        else:
            self.adjustSize()
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
                "有后台任务正在运行。\n\n"
                "强制结束会立即中断正在执行的 pip 操作，可能让相关 Python "
                "环境留下装了一半的包。\n\n"
                "确定要强制退出吗？",
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
