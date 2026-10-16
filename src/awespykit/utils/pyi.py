# coding: utf-8

__doc__ = """包含 pyinstaller 工具相关的类或函数。"""

import os
import ast
import re
from ..safe_files import owned_workspace, remove_owned_workspace
from subprocess import *
from typing import *

from ..__info__ import *
from ..com import *
from fastpip import PyEnv, decode_bytes
from fastpip.utils.process import run_process
from PyQt5.QtCore import *
from ..settings import *

from ..utils.main import get_cmd_out

PYI_P = r"(\d+\.\d+(\.\d+)?)"


class PyiTool(QObject):
    STARTUP = STARTUPINFO()
    STARTUP.dwFlags = STARTF_USESHOWWINDOW
    STARTUP.wShowWindow = SW_HIDE
    stdout = pyqtSignal(str)
    run_time = pyqtSignal(int)
    completed = pyqtSignal(int)
    pyi_init = os.path.join("PyInstaller", "__init__.py")
    using_pyi = "-m", "PyInstaller"
    read_pyi_ver = "-m", "PyInstaller", "-v"

    def __init__(self, pyenv: PyEnv = None, cwd=None):
        super().__init__()
        # 不要在参数默认值里写 os.getcwd()：默认值只在函数定义时求值一次，
        # 之后进程再切换工作目录都不会更新，会静默用上过期的目录。
        if cwd is None:
            cwd = os.getcwd()
        self.__pyenv: Union[PyEnv, None] = None
        self.__cwd = None
        self.__process = None
        self.owned_work = None
        self.__commands = None
        self.initialize(pyenv, cwd)
        self.cumulative = -200
        self.__qtimer = QTimer()
        self.__qtimer.timeout.connect(self.__time)
        self.run_time.connect(self.__timer_control)
        self.__log_level = "INFO"

    @property
    def cwd(self):
        return self.__cwd

    @cwd.setter
    def cwd(self, path):
        if os.path.isdir(path):
            self.__cwd = path

    @property
    def pyi_is_ready(self):
        """给出的 Python 环境中安装了 Pyinstaller 返回 True，否则返回 False。"""
        if not self.__pyenv or not self.__pyenv.env_is_valid:
            return False
        return os.path.isfile(
            os.path.join(self.__pyenv.site_packages_home(), self.pyi_init)
        ) or os.path.isfile(
            os.path.join(self.__pyenv.user_site_packages_home(), self.pyi_init)
        )

    def initialize(self, pyenv: PyEnv, cwd):
        assert pyenv is None or isinstance(pyenv, PyEnv)
        self.__pyenv = pyenv
        self.__cwd = cwd if cwd else None
        self.__process = None
        if not self.__pyenv or not self.__pyenv.env_is_valid:
            self.__commands = None
            return
        self.__commands = [self.__pyenv.interpreter, *self.using_pyi]

    def __time(self):
        if self.cumulative > 10000:
            self.cumulative = 0
        self.cumulative += 10

    def __timer_control(self, code):
        if code:
            self.__qtimer.start(10)
        else:
            self.__qtimer.stop()
            self.cumulative = -200

    def execute_cmd(self):
        """Run the owned build, draining output even after immediate exit."""
        if not self.__commands:
            self.stdout.emit("当前环境中找不到 PyInstaller 模块。")
            self.completed.emit(-1)
            return
        try:
            _, code = run_process(
                self.__commands, startupinfo=self.STARTUP, cwd=self.__cwd,
                callback=lambda data: self.stdout.emit((decode_bytes(data) or "").rstrip()),
            )
        except Exception as exc:
            self.stdout.emit("无法完成打包：" + str(exc))
            code = -1
        self.completed.emit(code)

    @staticmethod
    def __generate_infofile(verinfo_dict):
        version_info = """# coding: utf-8
VSVersionInfo(
ffi=FixedFileInfo(
filevers=$filevers$,
prodvers=$prodvers$,
mask=0x3F,
flags=0x0,
OS=0x40004,
fileType=0x1,
subtype=0x0,
date=(0, 0),
),
kids=[StringFileInfo(
[StringTable(
"080404b0",
[
StringStruct("CompanyName", "$CompanyName$"),
StringStruct("FileDescription", "$FileDescription$"),
StringStruct("FileVersion", "$FileVersion$"),
StringStruct("LegalCopyright", "$LegalCopyright$"),
StringStruct("OriginalFilename", "$OriginalFilename$"),
StringStruct("ProductName", "$ProductName$"),
StringStruct("ProductVersion", "$ProductVersion$"),
StringStruct("LegalTrademarks", "$LegalTrademarks$"),
],)]),
VarFileInfo([VarStruct("Translation", [2052, 1200])]),
],
)
"""
        file_path = os.path.join(config_root, "VERSION_INFO")
        def replacement(match):
            key = match.group(0)
            if key in ("$filevers$", "$prodvers$"):
                value = ast.literal_eval(verinfo_dict[key])
                if not isinstance(value, tuple) or len(value) != 4 or not all(
                    type(n) is int and 0 <= n <= 65535 for n in value
                ):
                    raise ValueError("Invalid Windows version tuple")
                return repr(value)
            return repr(str(verinfo_dict.get(key, "")))

        # Replace the whole string literal, once, so embedded placeholders stay data.
        version_info = re.sub(r'"(\$[A-Za-z]+\$)"', r'\1', version_info)
        version_info = re.sub(r'\$[A-Za-z]+\$', replacement, version_info)
        try:
            with open(file_path, "wt", encoding="utf-8") as f:
                f.write(version_info)
        except Exception:
            file_path = ""
        return file_path

    def pyi_info(self):
        version_info = VerInfo()
        if self.pyi_is_ready:
            result = get_cmd_out(
                self.__pyenv.interpreter, *self.read_pyi_ver, re_search=PYI_P
            )
            if result:
                version_info.set(result.group(1))
        return version_info

    def prepare_cmds(self, commands: PyiConfigure):
        """从 commands 添加 PyInstaller 命令选项。"""
        self.owned_work = None
        name = commands.bundle_spec_name
        if name and (name in (".", "..") or "/" in name or "\\" in name or ":" in name):
            raise ValueError("Program name must not contain path components")
        self.__log_level = commands.log_level
        if commands.onedir_bundle:
            self.__commands.append("-D")
        else:
            self.__commands.append("-F")
        if commands.spec_dir:
            self.__commands.extend(("--specpath", commands.spec_dir))
        if commands.bundle_spec_name:
            self.__commands.extend(("-n", commands.bundle_spec_name))
        for data in commands.other_datas:
            self.__commands.extend(("--add-data", rf"{data[0]};{data[1]}"))
        for module_path in commands.module_paths:
            self.__commands.extend(("-p", module_path))
        if commands.encryption_key:
            self.__commands.extend(("--key", commands.encryption_key))
        debug_options = commands.debug_options
        for option in debug_options:
            if debug_options[option]:
                self.__commands.extend(("--debug", option))
        if commands.donot_use_upx:
            self.__commands.append("--noupx")
        for binary in commands.upx_excludes:
            self.__commands.extend(("--upx-exclude", binary.lower()))
        if commands.provide_console:
            self.__commands.append("-c")
        else:
            self.__commands.append("-w")
        if commands.upx_dir:
            self.__commands.extend(("--upx-dir", commands.upx_dir))
        if commands.icon_path:
            self.__commands.extend(("-i", commands.icon_path))
        if commands.distribution_dir:
            self.__commands.extend(("--distpath", commands.distribution_dir))
        if commands.delete_working_dir:
            parent = commands.working_dir or "build"
            if not os.path.isabs(parent):
                parent = os.path.join(self.__cwd, parent)
            self.owned_work = owned_workspace(parent, self.__cwd)
            self.__commands.extend(("--workpath", str(self.owned_work[0])))
            self.stdout.emit("本次独占临时目录（成功后清理）：" + str(self.owned_work[0]))
        elif commands.working_dir:
            self.__commands.extend(("--workpath", commands.working_dir))
        info_path = self.__generate_infofile(commands.version_info)
        if commands.add_verfile and info_path:
            self.__commands.extend(("--version-file", info_path))
        if commands.runtime_tmpdir:
            self.__commands.extend(
                ("--runtime-tmpdir", commands.runtime_tmpdir)
            )
        if commands.no_confirm:
            self.__commands.append("-y")
        if commands.clean_building:
            self.__commands.append("--clean")
        for imp in commands.hidden_imports:
            self.__commands.extend(("--hidden-import", imp))
        for mod in commands.exclude_modules:
            self.__commands.extend(("--exclude-module", mod))
        if commands.uac_admin:
            self.__commands.append("--uac-admin")
        self.__commands.extend(("--log-level", self.__log_level))
        self.__commands.append(commands.script_path)

    def cleanup_workspace(self):
        if self.owned_work is not None:
            try:
                remove_owned_workspace(self.owned_work)
            except (OSError, ValueError) as exc:
                self.stdout.emit("临时目录清理失败，已保留目录：" + str(exc))
            else:
                self.owned_work = None
