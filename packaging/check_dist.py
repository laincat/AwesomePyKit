# coding: utf-8
'''分发包内容自检：发布出去的东西里不能混进顶层模块。

这个项目内部用的是扁平导入（com / logic / settings / ui / utils），
而 PyPI 上确实存在同名的第三方包。如果 setup 配置不当，把这几个目录当成
顶层包一起打进 wheel，装上的用户会遇到两类问题：
  1. 自己的环境里凭空多出 com / ui / utils 这些极通用的顶层包，
     可能把别人依赖的同名包顶掉；
  2. 顶层 utils 等目录与包内的同名模块并存，导入到哪个要看运气。

这里直接读 wheel 的 namelist 判断，比解析命令行输出可靠得多。
'''
import argparse
import sys
import zipfile
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

# 这些名字只允许出现在 awespykit/ 目录里面
PRIVATE_TOP_LEVEL = ('com', 'logic', 'settings', 'ui', 'utils')
REQUIRED_WHEEL_FILES = ('fastpip/LICENSE',)


def check_wheel(wheel: Path) -> list:
    problems = []
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        for required in REQUIRED_WHEEL_FILES:
            if required not in names:
                problems.append(f'缺少必需文件: {required}')
        for name in archive.namelist():
            parts = name.split('/')
            if len(parts) > 1 and parts[0] in PRIVATE_TOP_LEVEL:
                problems.append(name)
    return problems


def main(argv=None) -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dist_dir', nargs='?', default='dist-python')
    args = parser.parse_args(argv)

    wheels = sorted(Path(args.dist_dir).glob('*.whl'))
    if not wheels:
        print(f'在 {args.dist_dir} 里没找到 wheel 文件', file=sys.stderr)
        return 2

    exit_code = 0
    for wheel in wheels:
        problems = check_wheel(wheel)
        if problems:
            exit_code = 1
            print(f'{wheel.name}: 发现分发包内容问题：')
            for name in problems[:20]:
                print('   ', name)
            if len(problems) > 20:
                print(f'    ... 另有 {len(problems) - 20} 个')
        else:
            print(f'{wheel.name}: 内容检查通过')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
