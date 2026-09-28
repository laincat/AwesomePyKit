# coding: utf-8
'''回归测试：能在 CI 的 Windows 控制台（cp1252）下正常输出。

GitHub 的 Windows runner 控制台编码是 cp1252，而本仓库的脚本与 spec 都会 print
信息。若 print 的内容含中文，会抛 UnicodeEncodeError 并中断整个构建。

这个坑踩过两次：
  · packaging/make_version_info.py（首次，已加 reconfigure 修复）
  · packaging/awespykit.spec（新增精简逻辑时又踩了一次）

因此这里用子进程模拟 cp1252 环境，实际执行这些脚本，确保不会再犯。
'''
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_with_encoding(args, encoding='cp1252'):
    '''在指定的控制台编码下运行脚本，返回 (returncode, stdout+stderr 文本)。

    注意用 bytes 模式读取：子进程的输出是 cp1252，若用 text=True 让 Python 按
    UTF-8 解码，解码失败会让 stderr 变成 None（子进程的输出读取线程抛异常），
    测试反而测不出真正的问题。
    '''
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = encoding
    proc = subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=120,
    )
    raw = (proc.stdout or b'') + (proc.stderr or b'')
    return proc.returncode, raw.decode('utf-8', errors='replace')


def test_version_info_script_survives_cp1252(tmp_path):
    '''make_version_info.py 在 cp1252 控制台下不应因中文输出而失败。'''
    out = tmp_path / 'version_info.txt'
    code, output = _run_with_encoding([
        'packaging/make_version_info.py',
        '--version', '9.9.9',
        '--output', str(out),
    ])
    assert code == 0, (
        '在 cp1252 环境下失败（多半是 print 了非 ASCII 字符）：\n'
        f'{output[-600:]}'
    )
    assert out.is_file()


def test_check_dist_script_survives_cp1252(tmp_path):
    '''check_dist.py 同理。'''
    code, output = _run_with_encoding(['packaging/check_dist.py', str(tmp_path)])
    # 目录里没有 wheel 会返回 2，但不是因为编码崩溃（编码问题会是 traceback）
    assert 'UnicodeEncodeError' not in output, (
        '在 cp1252 环境下输出中文导致崩溃：\n' + output[-600:]
    )


def test_normalize_version_survives_cp1252():
    '''normalize_version.py 同理。'''
    code, output = _run_with_encoding(['packaging/normalize_version.py', 'v9.9.9'])
    assert code == 0, output[-600:]
    assert '9.9.9' in output


def test_spec_file_prints_no_non_ascii():
    '''spec 是在 PyInstaller 进程里直接执行的，没有 reconfigure 的保护，
    所以它的 print 必须是纯 ASCII。这里做静态检查，比跑一次完整打包快得多。'''
    spec = REPO_ROOT / 'packaging' / 'awespykit.spec'
    offenders = []
    for lineno, line in enumerate(spec.read_text(encoding='utf-8').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('print(') and not stripped.isascii():
            offenders.append(f'{lineno}: {stripped[:80]}')
    assert not offenders, (
        'spec 里的 print 含非 ASCII 字符，在 cp1252 控制台下会崩溃：\n' + '\n'.join(offenders)
    )
