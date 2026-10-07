# coding: utf-8

import json
import os
import os.path as op
import sys
from pathlib import Path

_frozen_program = getattr(sys, "frozen", False)
if _frozen_program:
    # noinspection PyUnresolvedReferences
    _res_root = sys._MEIPASS
else:
    _res_root = op.dirname(op.dirname(op.abspath(__file__)))
_appdata_local_folder = os.getenv("LOCALAPPDATA")
if not _appdata_local_folder:
    if _frozen_program:
        _user_data_root = op.dirname(sys.executable)
    else:
        _user_data_root = _res_root
else:
    _user_data_root = op.join(_appdata_local_folder, "Awespykit")
config_root = op.join(_user_data_root, "config")
themes_root = op.join(_user_data_root, "themes")


def generate_respath(*p):
    """
    用于在不同运行环境之下获取正确的资源文件路径

    不同的运行环境：Python 源代码运行、Pyinstaller 打包为单文件运行/打包为单目录运行
    """
    return op.join(_res_root, *p)


def coerce_enum(value, enum_cls, default):
    """把配置文件里读出来的原始值还原成枚举成员。

    配置是以 JSON 保存的，枚举成员写进去序列化成裸数字/字符串，读回来就是
    int 或 str。若不做还原，像 AppStyle.WindowsVista.name 这种访问枚举属性
    的代码就会抛 AttributeError（int 没有 name），而且通常要到用户真正用到
    那个功能时才暴露。

    无法识别时返回 default，保证配置损坏也不会让程序起不来。
    """
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, TypeError, KeyError):
        return default


def coerce_str_list(value, default=None):
    """把配置里的字符串列表还原成 list[str]。

    配置被手工改坏或版本升级后，字段可能是字符串（'a,b' 或 '/path'）、
    含非字符串元素的列表、None 等。若直接返回，调用方遍历时会按字符拆开
    （'abc' 会变成 'a','b','c'），或在拼接路径时抛 TypeError。

    返回的是规范化后的**新**列表。属性 getter 必须把它写回配置再返回，
    否则调用方拿到的是临时副本：``config.pypaths.append(...)``、
    ``del config.pypaths[i]`` 这类就地修改会丢在副本上 —— 界面显示操作
    成功，重新打开配置却又回到原样。
    """
    if default is None:
        default = []
    if isinstance(value, str):
        # 单个字符串按一行一项处理；空串视为空列表
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if isinstance(item, str)]
    return list(default)


def coerce_size(value, default):
    """把配置里读出来的窗口尺寸还原成 (宽, 高) 整数元组。

    JSON 没有元组类型，存盘后 (800, 600) 会变成 [800, 600]；若配置被手工
    改坏（例如写成字符串或长度不对），这里统一退回 default，避免把异常值
    传给 resize() 才在界面上炸掉。

    (0, 0) 是合法值，表示「按内容自然尺寸显示」（见 MainEntrance 的启动窗口），
    因此只拒绝负数。
    """
    try:
        width, height = value
        width, height = int(width), int(height)
    except (TypeError, ValueError):
        return tuple(default)
    # 负数的窗口尺寸对 Qt 没有意义，多半是配置被改坏；回退到默认值。
    # 0 是允许的：作为「未记录过尺寸、按内容自适应」的标记。
    if width < 0 or height < 0:
        return tuple(default)
    return width, height


class AbstractConfig(dict):
    root = Path(config_root)

    def __init__(self, fname):
        super().__init__()
        self.__cfg = self.root.joinpath(fname)
        self.__load_json()

    def save_config(self):
        """把配置写回磁盘。

        写失败时不再默默忽略：返回 False 由调用方决定是否提示用户。
        之前这里是 except: pass，磁盘满、目录只读、杀毒软件拦截等情况都会
        静默丢失用户的设置（例如刚调好的窗口布局、刚添加的 Python 环境），
        用户只会觉得「设置怎么没保存」。
        """
        try:
            with open(self.__cfg, "wt", encoding="utf-8") as f:
                json.dump(self, f, ensure_ascii=False)
        except Exception:
            return False
        return True

    def __load_json(self):
        """如果 __cfg 文件无法读取则返回空字典"""
        try:
            if not self.root.exists():
                self.root.mkdir(parents=True)
        except Exception:
            return
        if not self.__cfg.exists():
            try:
                with open(self.__cfg, "wt", encoding="utf-8") as f:
                    json.dump(dict(), f)
            except Exception:
                return
        else:
            try:
                with open(self.__cfg, "rt", encoding="utf-8") as f:
                    self.update(json.load(f))
            except Exception:
                return
