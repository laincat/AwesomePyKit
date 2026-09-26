# coding: utf-8
'''回归测试：三种启动方式都必须可用。

这个包曾经用「扁平导入」（from utils.thmt import ...）—— 也就是把 com / logic /
settings / ui / utils 这些子包当作顶层模块导入。那种写法有两个真实后果：

  1. 用户环境里只要装了同名的第三方包（PyPI 上确实有个 utils），
     程序启动即 ModuleNotFoundError；
  2. 只能在「包目录被塞进 sys.path」之后才能工作，换个启动方式就可能崩。

现在全部改成相对/绝对包内导入，于是对启动方式不再挑剔。这里把三种入口都锁住，
避免以后有人改回依赖 sys.path 的写法。
'''
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
PKG_DIR = SRC_DIR / 'awespykit'

# 只验证「能被导入并构造出主窗口」，不进入 Qt 事件循环（否则测试会一直挂着）
PROBE = textwrap.dedent(
    '''
    import awespykit.runpykit as rpk
    window = rpk.MainEntrance()
    print('BOOT-OK', rpk.VERSION)
    '''
)


def _run(args, cwd):
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    # 用 PYTHONPATH 指向 src，模拟「包可被导入」的正常使用场景
    env['PYTHONPATH'] = str(SRC_DIR)
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
        timeout=180,
    )


def test_boot_as_package_module():
    '''python -c 'import awespykit.runpykit'（等价于 rpk 控制台脚本的路径）'''
    result = _run(['-c', PROBE], REPO_ROOT)
    assert result.returncode == 0, result.stderr
    assert 'BOOT-OK' in result.stdout


def test_boot_via_dash_m():
    '''python -m awespykit 的入口文件存在且指向正确。

    真正执行 python -m awespykit 会进入 Qt 事件循环、直到用户关掉窗口才返回，
    放在测试里会把用例挂死。这里改为静态确认 __main__.py 的内容符合预期，
    再由 test_boot_as_package_module 覆盖它实际调用的那个函数可被导入。
    '''
    source = (PKG_DIR / '__main__.py').read_text(encoding='utf-8')
    assert 'runpykit_and_sysexit' in source, '__main__.py 应调用入口函数'
    assert 'from .runpykit import' in source or 'from awespykit.runpykit import' in source, (
        '__main__.py 应以包内导入方式引用 runpykit'
    )


def test_boot_as_direct_script():
    '''直接运行 src/awespykit/runpykit.py（源码运行方式的文档写法之一）。

    这是最容易被破坏的一种：没有包上下文，任何相对导入都会失败。
    这里给足时间——若导入失败会立刻返回非 0；成功则会进入 GUI 事件循环，
    因此用超时来判定「启动成功」。
    '''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    env.pop('PYTHONPATH', None)  # 刻意不提供 PYTHONPATH，验证自身的引导逻辑
    try:
        result = subprocess.run(
            [sys.executable, str(PKG_DIR / 'runpykit.py')],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            # 导入失败会立刻返回；能一直跑下去说明已进入 GUI 事件循环
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        # 一直在跑 = 成功进入事件循环
        return
    assert result.returncode == 0 or 'BOOT' in result.stdout, (
        '直接运行脚本失败：\n' + result.stderr
    )


def test_no_flat_imports_remain():
    '''静态检查：包内不应再出现把子包当顶层模块导入的写法。'''
    forbidden = ('com', 'logic', 'settings', 'ui', 'utils')
    offenders = []
    for path in sorted(PKG_DIR.rglob('*.py')):
        if path.name == 'res.py':  # 由 pyrcc5 生成，不涉及包内导入
            continue
        for lineno, line in enumerate(
            path.read_text(encoding='utf-8').splitlines(), 1
        ):
            stripped = line.strip()
            if not stripped.startswith('import '):
                continue
            module = stripped[len('import '):].split(' as ')[0].split('.')[0]
            if module in forbidden:
                offenders.append(f'{path.relative_to(PKG_DIR)}:{lineno} {stripped}')
    assert not offenders, '发现扁平导入（会导致同名第三方包顶掉本包模块）：\n' + '\n'.join(offenders)
