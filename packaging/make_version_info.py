# coding: utf-8
'''生成 PyInstaller 用的 Windows 版本信息文件（version_info.txt）。

这个文件决定 exe 在“属性 -> 详细信息”里显示的版本号。
版本号来源优先级：
  1. 命令行 --version（CI 里从 git tag 取，最准）
  2. 环境变量 AWESPY_VERSION
  3. 已安装包的元数据（setuptools_scm 从 git 推导出来）
  4. 兜底的 0.0.0.0

注意 Windows 的 4 段版本号每段上限是 65535，所以像 2026.926.1234 这种
基于日期的版本号不能直接塞进去，需要截断处理。
'''
import argparse
import os
import sys
from pathlib import Path


def _force_utf8_output():
    '''让脚本在非 UTF-8 控制台（Windows 默认 cp936 / cp1252）上也能打印中文。'''
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            try:
                reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

TEMPLATE = '''# UTF-8
#
# 由 packaging/make_version_info.py 生成，请勿手工编辑。
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={tuple4},
        prodvers={tuple4},
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '080404b0',
                    [
                        StringStruct('CompanyName', '{author}'),
                        StringStruct('FileDescription', '{description}'),
                        StringStruct('FileVersion', '{version}'),
                        StringStruct('InternalName', 'Awespykit'),
                        StringStruct('LegalCopyright', '{copyright}'),
                        StringStruct('OriginalFilename', 'Awespykit.exe'),
                        StringStruct('ProductName', 'Awespykit'),
                        StringStruct('ProductVersion', '{version}')
                    ]
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [2052, 1200])])
    ]
)
'''


def to_ms_numbers(version: str) -> list:
    '''转成 4 段版本号列表（每段 0..65535，不足补 0）。'''
    numbers = []
    for part in version.replace('-', '.').split('.')[:4]:
        digits = ''.join(ch for ch in part if ch.isdigit())
        numbers.append(min(int(digits), 65535) if digits else 0)
    while len(numbers) < 4:
        numbers.append(0)
    return numbers


def to_ms_version(version: str) -> str:
    '''转成点分形式的版本号字符串（用于展示字段）。'''
    return '.'.join(str(n) for n in to_ms_numbers(version))


def resolve_version(explicit=None) -> str:
    if explicit:
        return explicit
    if os.getenv('AWESPY_VERSION'):
        return os.environ['AWESPY_VERSION']
    try:
        from importlib.metadata import version

        return version('Awespykit')
    except Exception:
        return '0.0.0'


def render(version: str) -> str:
    ms_version = to_ms_version(version)
    # PyInstaller 用 eval 解析这个文件，元组必须带逗号：不能写成 (2.1.1.0)
    tuple4 = '(' + ', '.join(str(n) for n in to_ms_numbers(version)) + ')'
    return TEMPLATE.format(
        tuple4=tuple4,
        version=ms_version,
        author='hrp/hrpzcf',
        description='Python 工具箱（包管理 / 程序打包 / 镜像源设置 / 分发包下载）',
        copyright='GPLv3',
    )


def main(argv=None) -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=None, help='显式指定版本号')
    parser.add_argument(
        '--output', default='packaging/version_info.txt', help='输出路径'
    )
    args = parser.parse_args(argv)

    version = resolve_version(args.version)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(version), encoding='utf-8')
    print(f'已生成 {output} -> 版本 {version}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
