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
except:
    VERSION = PRE_VER
AUTHOR = "hrp/hrpzcf"

__all__ = ["APP_NAME", "AUTHOR", "PRE_VER", "VERSION"]
