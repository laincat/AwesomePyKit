# coding: utf-8

from typing import Sequence

from ..com import *

from .abstract_config import AbstractConfig, coerce_enum, coerce_size


class MainEntranceConfig(AbstractConfig):
    _key_app_style = "app_style"
    _key_window_size = "window_size"
    _key_selected_theme = "selected_theme"

    CONFIGFILE = "main_entrance.json"

    def __init__(self):
        super().__init__(self.CONFIGFILE)

    @property
    def app_style(self):
        value = self.setdefault(self._key_app_style, AppStyle.Windows.value)
        # 从 JSON 读回来是裸 int，还原成枚举再交给调用方，
        # 否则 AppStyle.WindowsVista.name 这类访问会失败。
        return coerce_enum(value, AppStyle, AppStyle.Windows)
    
    @app_style.setter
    def app_style(self, value):
        assert isinstance(value, AppStyle)
        self[self._key_app_style] = int(value)

    @property
    def window_size(self):
        # 默认值取 (0, 0)，作为「尚未记录过用户调整」的标记。
        #
        # 启动窗口的按钮是横向排列的（sizeHint 约 324x58），而这里原本写死成
        # (260, 320) —— 一个竖长条。于是首次启动时按钮被挤成竖排，用户必须先
        # 把窗口横向拉宽再缩回去，才能得到本该有的扁矩形外观。
        # 用 (0, 0) 表示「按内容自然尺寸显示」，见 MainEntrance.display()。
        return coerce_size(
            self.setdefault(self._key_window_size, (0, 0)), (0, 0)
        )

    @window_size.setter
    def window_size(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_window_size] = value

    @property
    def selected_thm(self):
        value = self.setdefault(self._key_selected_theme, -1)
        # 主题索引必须是整数；配置被改坏时回退到 -1（表示使用默认主题）
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    @selected_thm.setter
    def selected_thm(self, value):
        assert isinstance(value, int)
        self[self._key_selected_theme] = value
