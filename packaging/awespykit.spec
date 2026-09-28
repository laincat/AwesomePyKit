# coding: utf-8
'''PyInstaller 打包配置（单文件、无控制台窗口）。

为什么用 .spec 而不是命令行参数：
  · 命令行写法太长，且散落在 workflow 里，改动容易顾此失彼；
  · 这里需要 '--copy-metadata Awespykit'，把包的元数据一起打包，程序才能从
    importlib.metadata 读到真实版本号（否则会退回 __info__.py 里的 PRE_VER，
    发布出去的 exe 会显示成开发时的占位版本号）；
  · 显式声明 excludes，避免把构建环境里的无关大包吃进去。

用法（在仓库根目录）：pyinstaller --noconfirm packaging/awespykit.spec
'''
import sys
from pathlib import Path

# spec 文件执行时 __file__ 不可靠，用 SPECPATH 定位仓库根目录
REPO_ROOT = Path(SPECPATH).resolve().parent
SRC_DIR = REPO_ROOT / 'src' / 'awespykit'

block_cipher = None

a = Analysis(
    [str(SRC_DIR / 'runpykit.py')],
    # 入口脚本以包名绝对导入（from awespykit.com import ...），所以把 src 目录
    # 放进搜索路径，让 PyInstaller 能解析到整个 awespykit 包。
    pathex=[str(REPO_ROOT / 'src')],
    binaries=[],
    datas=[],
    hiddenimports=[],
    # 只打包程序真正用到的东西。这个程序是纯 QtWidgets 界面，未使用 QML / Quick /
    # 网络 / WebSocket / 多媒体 / 定位等模块，但 PyQt5 的默认 hook 会把整套
    # Qt5 DLL 都收进来（含 20 MB 的软件 OpenGL 回退、QML 引擎、Designer 等）。
    # 排除它们能让 exe 明显变小，且不影响功能 —— 每一条都在下方注明依据。
    excludes=[
        # 可选的美化主题包：没装就该安静跳过，不该报成构建错误
        'qdarkstyle',
        'qt_material',
        # 标准库里用不到的大块
        'tkinter',
        'unittest',
        'pydoc_data',
        'test',
        # 未使用的 PyQt5 子模块
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtWebSockets',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtSql',
        'PyQt5.QtTest',
        'PyQt5.QtBluetooth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtLocation',
        'PyQt5.QtSerialPort',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtXmlPatterns',
        'PyQt5.QtXml',
        'PyQt5.QtSvg',
        'PyQt5.QtOpenGL',
        'PyQt5.QtPrintSupport',
        'PyQt5.QtDBus',
        'PyQt5.QAxContainer',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebEngineWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 打包包元数据，让程序读到真实版本号
    copy_metadata=['Awespykit'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── 精简打包体积 ────────────────────────────────────────────────────────────
#
# 注意：上面 Analysis 的 excludes 只作用于「Python 模块导入」，不含二进制文件。
# Qt5 的 DLL 是 PyQt5 的 PyInstaller hook 直接收集的，所以 excludes 对它们无效
# —— 实测确认过：列上二十多个 PyQt5 子模块，exe 体积与 DLL 数量毫无变化。
#
# 要真正瘦身，必须在 Analysis 之后过滤 a.binaries 这个二进制清单。
#
# 排除的依据：本程序是纯 QtWidgets 界面，代码里只 from PyQt5 导入了 QtCore /
# QtGui / QtWidgets 三者（可用 grep 复核），未使用 QML / Quick / 网络 / WebSocket
# / 多媒体 / 定位 / 数据库 / 打印 / 蓝牙 / NFC 等任何模块。

# 明确要丢弃的 Qt 运行库（按文件名匹配，大小写不敏感）
_UNNEEDED_QT_DLLS = {
    # QML / Quick —— 纯 Widgets 程序不需要整个 QML 引擎
    'qt5qml.dll',
    'qt5qmlmodels.dll',
    'qt5quick.dll',
    'qt5quickwidgets.dll',
    'qt5quickcontrols2.dll',
    # 网络与通信
    'qt5network.dll',
    'qt5websockets.dll',
    'qt5bluetooth.dll',
    'qt5nfc.dll',
    'qt5serialport.dll',
    'qt5dbus.dll',
    # 未使用的扩展模块
    'qt5designer.dll',
    'qt5designercomponents.dll',
    'qt5help.dll',
    'qt5location.dll',
    'qt5positioning.dll',
    'qt5xmlpatterns.dll',
    'qt5xml.dll',
    'qt5sql.dll',
    'qt5test.dll',
    'qt5multimedia.dll',
    'qt5multimediawidgets.dll',
    'qt5multimediaquick.dll',
    # 图形后端的可选实现：opengl32sw 是 20 MB 的软件 OpenGL 回退，
    # 只在没有可用 GPU 驱动的极端环境才被用到；libGLESv2/libEGL 是 ANGLE。
    # d3dcompiler 是 QML 场景需要的着色器编译器。
    'opengl32sw.dll',
    'libglesv2.dll',
    'libegl.dll',
    'd3dcompiler_47.dll',
}

# 明确要丢弃的 Qt 图片格式插件（程序只用到 PNG 与 GIF）
_UNNEEDED_QT_PLUGINS = {
    'qsvg.dll',
    'qsvgicon.dll',
    'qtga.dll',
    'qtiff.dll',
    'qwbmp.dll',
    'qwebp.dll',
    'qicns.dll',
    'qwebgl.dll',
    'qxdgdesktopportal.dll',
    'qtuiotouchplugin.dll',
}
# 注意：qwindows.dll（真实 GUI）、qminimal.dll、qoffscreen.dll 属于「平台插件」，
# 必须保留。offscreen 尤其重要 —— CI 的 exe 冒烟测试就是用它跑的（无显示器环境），
# 删掉会让冒烟测试失败。这三者体积都很小，留着不心疼。


def _should_drop(entry):
    '''判断一个 (name, path, typecode) 条目是否应丢弃。'''
    try:
        name = entry[0]
    except (TypeError, IndexError):
        return False
    if not isinstance(name, str):
        return False
    # TOC 里的 name 带路径前缀，例如 'PyQt5\\Qt5\\bin\\Qt5Qml.dll'，
    # 因此必须取 basename 再比较 —— 直接比对全名会导致一条都匹配不上
    # （实测：全名匹配时只过滤掉 6 个，改用 basename 后能过滤掉全部目标）。
    lowered = name.lower()
    base = lowered.replace('/', '\\').rsplit('\\', 1)[-1]
    if base in _UNNEEDED_QT_DLLS or base in _UNNEEDED_QT_PLUGINS:
        return True
    # 图片格式插件：只保留程序实际使用的 png / gif（以及 ico 供窗口图标）。
    if 'imageformats' in lowered and base.endswith('.dll'):
        if base not in ('qpng.dll', 'qgif.dll', 'qico.dll', 'qjpeg.dll'):
            return True
    return False


_before = len(a.binaries)
a.binaries = TOC([e for e in a.binaries if not _should_drop(e)])
_dropped = _before - len(a.binaries)
# 输出刻意用 ASCII：spec 是在 PyInstaller 进程里执行的，而 GitHub 的 Windows
# runner 控制台编码是 cp1252，打印中文会抛 UnicodeEncodeError 并中断构建
# （这一条踩过两次，第一次在 packaging/make_version_info.py 里）。
print(f'[spec] slimmed binaries: removed {_dropped} ({_before} -> {len(a.binaries)})')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Awespykit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 压缩过的 exe 极易被安全软件误报
    runtime_tmpdir=None,
    console=False,  # 这是个 GUI 程序，不要弹控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SRC_DIR / 'res' / 'icon.ico'),
    version=str(REPO_ROOT / 'packaging' / 'version_info.txt'),
)
