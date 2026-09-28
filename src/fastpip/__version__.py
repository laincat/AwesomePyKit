# coding: utf-8

__all__ = ["NAME", "AUTHOR", "WEBSITE", "VERSION", "VERNUM"]

NAME = "fastpip"
# 跟随本仓库（AwesomePyKit）的维护版本，而非上游 fastpip 的版本号。
# 上游自 2023-03 起停更，本仓库在其 1.7.0 基础上做了修复，修订号递增以示区别。
VERNUM = 1, 7, 1
AUTHOR = "hrpzcf"
WEBSITE = "https://github.com/hrpzcf/fastpip"
VERSION = ".".join(map(str, VERNUM))
