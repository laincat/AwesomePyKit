# coding: utf-8
'''回归测试：包内模块不能被 site-packages 里的同名包顶掉。

这个包用的是「扁平」包内导入 —— from utils.thmt import ...、from com import *、
from settings import ...。这些名字都很普通，PyPI 上确实躺着同名的第三方包
（例如 utils）。

入口点原来只做了 sys.path.append(包目录)，而 append 的优先级低于
site-packages，于是一旦用户环境里装了同名的第三方包，程序会在启动时直接
ModuleNotFoundError。这里用一个假的 utils 包把这个行为锁住。
'''
import os
import subprocess
import sys
import textwrap
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'


def test_import_with_conflicting_top_level_package(tmp_path):
    '''模拟 site-packages 中存在第三方 utils 包的情况。'''
    shadow = tmp_path / 'shadow'
    (shadow / 'utils').mkdir(parents=True)
    # 一个不含 thmt 子模块的 utils 包，正是 PyPI 上那个 utils 的样子
    (shadow / 'utils' / '__init__.py').write_text('value = 1\n', encoding='utf-8')

    script = textwrap.dedent(
        '''
        import os, sys
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        sys.path.insert(0, sys.argv[1])   # 源码目录
        sys.path.append(sys.argv[2])      # 伪装成 site-packages 的冲突包
        import awespykit.runpykit as rpk
        print('OK', rpk.VERSION)
        '''
    )

    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    result = subprocess.run(
        [sys.executable, '-c', script, str(SRC_ROOT), str(shadow)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, (
        '包内模块被同名的第三方包遮蔽，程序无法启动：\n'
        f'stdout={result.stdout}\nstderr={result.stderr}'
    )
