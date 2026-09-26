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
        return coerce_size(
            self.setdefault(self._key_window_size, (260, 320)), (260, 320)
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
