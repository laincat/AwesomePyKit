# coding: utf-8
'''冒烟测试：确认程序在真实运行环境下能加载起来。

这个项目把资源编译进了 res/res.py（由 res.qrc 生成），控件、图标、样式表、
翻译文件全部从 Qt 的 ':/' 资源系统读取。一旦 res.py 与 res.qrc 不同步、某个
子包漏进分发包，或者入口点的 sys.path 处理有误，程序都会在启动瞬间崩掉 ——
而这些错误用 python -m compileall 是发现不了的。

所以这里真的把主窗口构建出来（用 offscreen 平台插件，不需要显示器），
再逐个检查关键资源是否存在。
'''
import os
import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'

# 必须在导入 PyQt5 之前设置，否则会去连真实显示服务
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='module')
def rpk():
    '''以源码方式导入入口模块（不依赖包是否已安装）。'''
    sys.path.insert(0, str(SRC_ROOT))
    import awespykit.runpykit as module

    return module


def test_entry_module_imports(rpk):
    assert rpk.APP_NAME == 'Awespykit'
    assert rpk.VERSION


def test_qt_resources_are_registered(rpk):
    '''图标、动图、翻译文件都必须能从内置资源里取到。'''
    resources = (
        ':/manage.png',
        ':/bundle.png',
        ':/indexurl2.png',
        ':/download.png',
        ':/cloudfunction.png',
        ':/settings.png',
        ':/loading.gif',
        ':/icon2_64.png',
        ':/trans/widgets_zh-CN.qm',
    )
    missing = [name for name in resources if rpk.QIcon(name).isNull()]
    assert not missing, f'资源缺失（res.py 与 res.qrc 可能不同步）：{missing}'


def test_builtin_themes_load(rpk):
    '''内置主题是从资源文件里解析出来的，解析失败会静默少几个主题。'''
    names = [theme.name for theme in rpk.PreThemeList]
    # 至少要有：两套内置 QSS + Fusion + 原生风格
    assert len(names) >= 4, f'内置主题数量异常：{names}'
    assert any(name.isascii() for name in names), f'主题名未解析出来：{names}'


def test_main_window_can_be_constructed(rpk):
    '''构造主窗口会连带实例化全部功能窗口，能覆盖绝大部分导入与初始化。'''
    window = rpk.MainEntrance()
    try:
        assert window.windowTitle() == rpk.APP_NAME
    finally:
        window.deleteLater()
