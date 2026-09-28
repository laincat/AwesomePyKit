# coding: utf-8
'''回归测试：fastpip 必须是本仓库 vendored 的那一份。

fastpip 的上游（hrpzcf/fastpip）自 2023-03 起停更，本仓库把它的源码放进
src/fastpip/ 一并打包维护。

这里锁住两件事：

1. 实际 import 到的 fastpip 来自本仓库，而不是 site-packages 里从 PyPI 装的同名包。
   两者包名相同，若 requirements.txt 里仍声明 fastpip，pip 会把两份装进同一个
   目录互相覆盖 —— 实际生效的是哪一份取决于安装顺序，这种不确定性极难排查。

2. vendored 副本的源码里没有无效转义序列。上游 1.7.0 有两处（fastpip.py 的正则、
   findpath.py 的文档字符串），Python 3.12 起报 SyntaxWarning，将来的版本会升级为
   SyntaxError —— 届时整个程序会无法导入。
'''
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
VENDORED = SRC_ROOT / 'fastpip'


def test_vendored_fastpip_exists():
    assert (VENDORED / '__init__.py').is_file(), 'src/fastpip 应存在（vendored 副本）'
    assert (VENDORED / 'core' / 'fastpip.py').is_file()
    assert (VENDORED / 'LICENSE').is_file(), 'upstream 是 MIT，须保留许可证'


def test_imported_fastpip_comes_from_repo():
    '''在子进程里导入，确认来源路径在本仓库内。'''
    probe = (
        'import fastpip, os, sys;'
        'print(os.path.dirname(os.path.abspath(fastpip.__file__)));'
        'print(fastpip.VERNUM)'
    )
    env = {**__import__('os').environ}
    env['PYTHONPATH'] = str(SRC_ROOT)
    result = subprocess.run(
        [sys.executable, '-c', probe],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    location = Path(lines[0])
    assert location == VENDORED, (
        f'导入到的 fastpip 不在本仓库内：{location}\n'
        '说明加载的是 PyPI 上的同名包，可能与 vendored 副本冲突。'
    )


def test_no_invalid_escape_sequences():
    '''扫源码里的无效转义（用编译警告来判定最可靠）。'''
    problems = []
    for path in sorted(VENDORED.rglob('*.py')):
        code = (
            'import warnings, py_compile;'
            'warnings.simplefilter("error");'
            f'py_compile.compile(r"{path}", doraise=True)'
        )
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            problems.append(f'{path.relative_to(VENDORED)}: {result.stderr.strip()[-160:]}')
    assert not problems, 'vendored fastpip 存在语法警告（将来会变成硬错误）：\n' + '\n'.join(problems)


def test_requirements_does_not_declare_fastpip():
    '''requirements.txt 不应声明 fastpip，否则会与 vendored 副本互相覆盖。'''
    for name in ('requirements.txt', 'requirements-dev.txt'):
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('#', 1)[0].strip()
            if not code:
                continue
            # 只看包名部分
            pkg = code.split('>')[0].split('<')[0].split('=')[0].split(';')[0].strip().lower()
            assert pkg != 'fastpip', (
                f'{name}:{lineno} 声明了 fastpip。它会从 PyPI 再装一份同名包，'
                '与 src/fastpip/ 的副本装进同一目录互相覆盖。'
            )
