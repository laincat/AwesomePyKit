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
    pathex=[str(SRC_DIR)],  # 包内用的是扁平导入（com / logic / ui / utils ...）
    binaries=[],
    datas=[],
    hiddenimports=[],
    # 这些是可选的美化主题包，没装就该安静地跳过，不必报成构建错误
    excludes=['qdarkstyle', 'qt_material', 'tkinter', 'unittest', 'pydoc_data'],
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
