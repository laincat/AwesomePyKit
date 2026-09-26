# coding: utf-8

from typing import Iterable, Sequence

from ..com import *

from .abstract_config import AbstractConfig, coerce_size, coerce_enum

_shared_saved_pypaths = None


def get_shared_pypaths():
    return _shared_saved_pypaths


class PackageManagerConfig(AbstractConfig):
    """包管理器的设置类"""

    _key_python_paths = "python_paths"
    _key_include_pre = "include_pre"
    _key_install_for_user = "install_for_user"
    _key_index_url = "index_url"
    _key_last_path = "last_path"
    _key_use_index_url = "use_index_url"
    _key_package_names = "package_names"
    _key_window_size = "window_size"
    _key_install_winsize = "install_winsize"
    _key_input_winsize = "input_winsize"
    _key_output_side = "output_side"
    _key_output_winsize = "output_winsize"
    _key_query_winsize = "query_winsize"
    _key_query_name = "query_name"
    _key_query_mode = "query_mode"
    _key_query_case = "query_case"
    _key_force_reinsall = "force_reinsall"

    CONFIGFILE = "package_manager.json"

    def __init__(self):
        super().__init__(self.CONFIGFILE)
        global _shared_saved_pypaths
        _shared_saved_pypaths = self.pypaths

    @property
    def pypaths(self) -> list:
        if self._key_python_paths not in self:
            self[self._key_python_paths] = list()
        return self[self._key_python_paths]

    @pypaths.setter
    def pypaths(self, value: Iterable):
        assert isinstance(value, Iterable)
        assert all(isinstance(i, str) for i in value)
        self[self._key_python_paths].clear()
        self[self._key_python_paths].extend(value)

    @property
    def include_pre(self):
        if self._key_include_pre not in self:
            self[self._key_include_pre] = False
        return self[self._key_include_pre]

    @include_pre.setter
    def include_pre(self, value: bool):
        assert isinstance(value, bool)
        self[self._key_include_pre] = value

    @property
    def install_for_user(self):
        if self._key_install_for_user not in self:
            self[self._key_install_for_user] = False
        return self[self._key_install_for_user]

    @install_for_user.setter
    def install_for_user(self, value: bool):
        assert isinstance(value, bool)
        self[self._key_install_for_user] = value

    @property
    def last_path(self):
        if self._key_last_path not in self:
            self[self._key_last_path] = "."
        return self[self._key_last_path]

    @last_path.setter
    def last_path(self, value):
        assert isinstance(value, str)
        self[self._key_last_path] = value

    @property
    def index_url(self):
        if self._key_index_url not in self:
            self[self._key_index_url] = ""
        return self[self._key_index_url]

    @index_url.setter
    def index_url(self, value):
        assert isinstance(value, str)
        self[self._key_index_url] = value

    @property
    def use_index_url(self):
        if self._key_use_index_url not in self:
            self[self._key_use_index_url] = False
        return self[self._key_use_index_url]

    @use_index_url.setter
    def use_index_url(self, value: bool):
        assert isinstance(value, bool)
        self[self._key_use_index_url] = value

    @property
    def package_names(self):
        if self._key_package_names not in self:
            self[self._key_package_names] = list()
        return self[self._key_package_names]

    @package_names.setter
    def package_names(self, value: list):
        assert isinstance(value, list)
        self[self._key_package_names] = value

    @property
    def window_size(self):
        return coerce_size(
            self.setdefault(self._key_window_size, (960, 600)),
            (960, 600),
        )

    @window_size.setter
    def window_size(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_window_size] = value

    @property
    def install_winsize(self):
        return coerce_size(
            self.setdefault(self._key_install_winsize, (400, 420)),
            (400, 420),
        )

    @install_winsize.setter
    def install_winsize(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_install_winsize] = value

    @property
    def input_winsize(self):
        return coerce_size(
            self.setdefault(self._key_input_winsize, (580, 0)),
            (580, 0),
        )

    @input_winsize.setter
    def input_winsize(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_input_winsize] = value

    @property
    def output_side(self):
        # JSON 里存的是裸 int，读回时要还原成枚举，否则调用方的
        # Linkage(...) 虽然还能转，但任何 .name / 比较都会变得脆弱。
        value = self.setdefault(self._key_output_side, int(Linkage.Left))
        return coerce_enum(value, Linkage, Linkage.Left)

    @output_side.setter
    def output_side(self, value):
        assert isinstance(value, Linkage)
        self[self._key_output_side] = int(value)

    @property
    def output_winsize(self):
        return coerce_size(
            self.setdefault(self._key_output_winsize, (350, 500)),
            (350, 500),
        )

    @output_winsize.setter
    def output_winsize(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_output_winsize] = value

    @property
    def query_name(self):
        return self.setdefault(self._key_query_name, "")

    @query_name.setter
    def query_name(self, value):
        assert isinstance(value, str)
        self[self._key_query_name] = value

    @property
    def query_mode(self):
        value = self.setdefault(self._key_query_mode, int(QMode.Pkg2Imp))
        return coerce_enum(value, QMode, QMode.Pkg2Imp)

    @query_mode.setter
    def query_mode(self, value):
        assert isinstance(value, QMode)
        self[self._key_query_mode] = int(value)

    @property
    def query_case(self):
        return self.setdefault(self._key_query_case, False)

    @query_case.setter
    def query_case(self, value):
        assert isinstance(value, bool)
        self[self._key_query_case] = value

    @property
    def query_winsize(self):
        return coerce_size(
            self.setdefault(self._key_query_winsize, (330, 330)), (330, 330)
        )

    @query_winsize.setter
    def query_winsize(self, value):
        assert isinstance(value, Sequence)
        assert len(value) == 2
        assert isinstance(value[0], int) and isinstance(value[1], int)
        self[self._key_query_winsize] = value

    @property
    def force_reinstall(self):
        return self.setdefault(self._key_force_reinsall, False)

    @force_reinstall.setter
    def force_reinstall(self, value):
        assert isinstance(value, bool)
        self[self._key_force_reinsall] = value
