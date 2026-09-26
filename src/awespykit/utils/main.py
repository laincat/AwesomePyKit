# coding: utf-8

__doc__ = """包含AwesomePyKit的主要类、函数、配置文件路径等。"""

import os.path as osp
import re
from subprocess import *
from typing import *
from typing import Match
from urllib.parse import urlparse

import win32api
from fastpip import PyEnv

# noinspection PyUnresolvedReferences
from win32com.shell import shell


def loop_install(
    pyenv, sequence, *, index_url="", pre=False, user=False, upgrade=False
):
    for name in sequence:
        cmd_exec_result = pyenv.install(
            name,
            pre=pre,
            user=user,
            index_url=index_url,
            upgrade=upgrade,
        )
        yield cmd_exec_result[0][0], cmd_exec_result[1]


def loop_uninstall(pyenv, sequence):
    for name in sequence:
        cmd_exec_result = pyenv.uninstall(name)
        yield cmd_exec_result[0][0], cmd_exec_result[1]


def check_py_path(py_dir_path):
    return PyEnv(py_dir_path).env_path != ""


def clean_py_paths(paths):
    return [pth for pth in paths if check_py_path(pth)]


def check_index_url(url):
    """判断字符串是否像一个可用的 pip 镜像源地址。

    原实现只接受 https 且必须以 /simple 结尾，会误拒两类真实存在的合法源：
      · http 源（内网私服、离线镜像非常常见）
      · 非 /simple 结尾的源（例如 PyTorch 官方的 download.pytorch.org/whl/cu118）
    两者都是 pip -i/--index-url 完全接受的形式。

    这里放宽到：必须是 http/https 的绝对地址，且带主机名；仍然拒绝空串、
    相对路径、以及明显写错的东西（比如把包名填进来）。
    """
    if not isinstance(url, str):
        return False
    url = url.strip()
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    # 必须有主机名，且主机名里得有个点或就是 localhost（拒绝 'https://simple'
    # 这种把路径当主机的情况）
    host = parsed.hostname or ""
    if not host or ("." not in host and host != "localhost"):
        return False
    return True


def clean_index_urls(urls):
    return [url for url in urls if check_index_url(url)]


def get_cmd_out(
    *commands, re_search=None, timeout=None
) -> Union[str, Match[str], None]:
    """执行命令并取回输出，可选地用正则从输出里提取信息。

    这是一个「尽力而为」的工具函数：命令不存在（例如 Python 环境已被删除、
    路径失效）、进程启动失败、执行超时，都应安静地返回空结果，由调用方按
    「拿不到信息」处理，而不是把异常抛到界面上。

    原实现的 try 只包住了 communicate()，Popen 本身在 try 之外 —— 当解释器
    路径失效时会抛 FileNotFoundError，直接把程序打包工具的版本探测打断。
    """
    info = STARTUPINFO()
    info.dwFlags = STARTF_USESHOWWINDOW
    info.wShowWindow = SW_HIDE
    try:
        proc = Popen(commands, stdout=PIPE, text=True, startupinfo=info)
    except OSError:
        # 命令不存在或无法启动（文件被删、路径失效、无执行权限）
        return ""
    try:
        strings, _ = proc.communicate(timeout=timeout)
    except Exception:
        # 超时或读取失败；确保子进程不会残留
        try:
            proc.kill()
            proc.communicate(timeout=5)
        except Exception:
            pass
        return ""
    if not re_search:
        return strings.strip()
    return re.search(re_search, strings)


def launch_explorer(folder_path: str, file_names: List[str] = None):
    """使用资源管理器打开文件夹并选择文件名列表中的文件"""
    assert isinstance(folder_path, str)
    assert osp.isdir(folder_path)
    assert file_names is None or all(isinstance(s, str) for s in file_names)
    if file_names is None:
        win32api.ShellExecute(0, "open", folder_path, None, None, 1)
        return
    folder_pidl = shell.SHILCreateFromPath(folder_path, 0)[0]
    files_tobe_selected = list()
    for file_name in file_names:
        file_fullpath = osp.join(folder_path, file_name)
        if not osp.isfile(file_fullpath):
            continue
        try:
            file_id = shell.SHParseDisplayName(file_fullpath, 0)[0]
            files_tobe_selected.append(file_id)
        except Exception:
            continue
    if not files_tobe_selected:
        return
    shell.SHOpenFolderAndSelectItems(folder_pidl, files_tobe_selected, 0)
