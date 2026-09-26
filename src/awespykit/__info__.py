# coding: utf-8

try:
    import importlib.metadata as metadata
except ImportError:
    import importlib_metadata as metadata

APP_NAME = "Awespykit"
# 仅作为「拿不到包元数据」时的兜底版本号（例如直接从源码运行）。
# 正式分发包与 exe 的版本号由 git 标签经 setuptools_scm 推导，不读这里。
PRE_VER = "2.1.1"
try:
    VERSION = metadata.version(APP_NAME)
except Exception:
    # 包未安装（直接跑源码）时拿不到元数据，退回兜底版本号。
    # 这里刻意用 Exception 而不是裸 except：裸 except 会连 KeyboardInterrupt
    # 和 SystemExit 一起吞掉，调试时很难受。
    VERSION = PRE_VER
AUTHOR = "hrp/hrpzcf"

__all__ = ["APP_NAME", "AUTHOR", "PRE_VER", "VERSION"]
