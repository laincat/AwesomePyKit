# coding: utf-8
'''把 git 标签规范化成合法的 PEP 440 版本号。

为什么需要这一步：发布流程把标签名直接交给 setuptools_scm 当作版本号
（SETUPTOOLS_SCM_PRETEND_VERSION）。但 git 标签是自由文本，而 PEP 440 有严格
语法 —— 若标签写成 v2.1.1-test 或 v2.1.1-beta，构建会以一条深层 traceback 结束：

    packaging.version.InvalidVersion: Invalid version: '2.1.1-test'

错误信息完全没提「是标签命名的问题」，维护者很难从 CI 日志里看出原因。
这个脚本负责：
  1. 把常见的标签写法（v 前缀、rc/beta/alpha 后缀）转成 PEP 440 形式；
  2. 转不了就带着明确提示失败，而不是让它烂在构建流程深处。
'''
import re
import sys


def _force_utf8_output():
    '''让脚本在非 UTF-8 控制台（Windows 默认 cp936 / cp1252）上也能打印中文。'''
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is not None:
            try:
                reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


# PEP 440 的预发布后缀写法各不相同，先统一成标准形式
#   rc1 / -rc1 / .rc1 / _rc1  -> rc1
#   beta1 / -beta1 / b1       -> b1
#   alpha1 / -alpha1 / a1     -> a1
#   post1 / -post1            -> .post1
_PRE_ALIASES = (
    # 备选项必须按长度从长到短排：正则的可选分支是「先匹配先赢」，
    # 若把 pre 写在 preview 前面，'preview3' 会被拆成 pre + view3。
    (r'(?i)[-_.]?(?:preview|pre|rc)[-_.]?(\d*)', r'rc\1'),
    (r'(?i)[-_.]?(?:beta)[-_.]?(\d*)', r'b\1'),
    (r'(?i)[-_.]?(?:alpha)[-_.]?(\d*)', r'a\1'),
    # 这里刻意不收录 'r' 这个简写：它是 post 的遗留别名，但单字母太容易误伤
    # 别的词 —— 例如 'rc1' 里的 r 会被吃掉，2.1.1rc1 变成 2.1.1.postc1。
    (r'(?i)[-_.]?(?:post|rev)[-_.]?(\d*)', r'.post\1'),
)


def normalize(tag: str) -> str:
    '''把标签规范化为 PEP 440 版本号；无法规范化时返回空串。'''
    version = tag.strip()
    if not version:
        return ''
    # 去掉常见的 v / V 前缀
    version = re.sub(r'^[vV](?=\d)', '', version)
    # .dev / -dev 这类已经是合法写法的先保留，避免误改
    for pattern, replacement in _PRE_ALIASES:
        version = re.sub(pattern, replacement, version)
    # 去掉其它分隔符，PEP 440 只认 . - _ 与字母数字
    version = re.sub(r'[^0-9A-Za-z._+-]', '', version)
    # 用打包生态自己的实现来判定，避免手写正则漏掉边界情况
    try:
        from packaging.version import InvalidVersion, Version
    except ImportError:
        return version
    try:
        return str(Version(version))
    except InvalidVersion:
        return ''


def main(argv=None) -> int:
    _force_utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print('用法: python packaging/normalize_version.py <tag>', file=sys.stderr)
        return 2

    raw = args[0]
    normalized = normalize(raw)
    if not normalized:
        print(
            f'无法把标签 {raw!r} 转换成合法的 PEP 440 版本号。\n'
            '  标签需要形如 v2.1.1、v2.1.1-rc1、v2.1.1-beta.2 的写法。\n'
            '  像 -test 这种自定义后缀不是合法的版本号，请改用 -rc1 之类，\n'
            '  或直接使用纯数字版本（如 v2.1.1）。',
            file=sys.stderr,
        )
        return 1

    if normalized != raw:
        print(f'标签 {raw!r} 已规范化为版本号 {normalized!r}', file=sys.stderr)
    # 结果单独打到 stdout，方便在 workflow 里用 $(...) 取值
    print(normalized)
    return 0


if __name__ == '__main__':
    sys.exit(main())
