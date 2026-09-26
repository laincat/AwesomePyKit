<div align="center">

<h1>Python 工具箱 - Awespykit</h1>

![GitHub stars](https://img.shields.io/github/stars/laincat/AwesomePyKit?style=flat)
![GitHub forks](https://img.shields.io/github/forks/laincat/AwesomePyKit?style=flat)
![GitHub issues](https://img.shields.io/github/issues/laincat/AwesomePyKit)
![GitHub license](https://img.shields.io/github/license/laincat/AwesomePyKit)
![GitHub release](https://img.shields.io/github/v/release/laincat/AwesomePyKit)

</div>

[程序简介](#程序简介) · [下载安装](#下载安装) · [功能说明](#功能说明) · [常见问题](#常见问题) · [开发与贡献](#开发与贡献)

---

## 程序简介

一个面向 Windows 的 Python 工具箱，把平时要在命令行里折腾的事情做成图形界面：

- **包管理器** —— 管理多个 Python 环境里的包（安装、卸载、升级）
- **程序打包工具** —— 把 Python 程序打包成 exe
- **镜像源设置工具** —— 一键切换 pip 镜像源
- **模块安装包下载器** —— 下载包及其依赖的安装文件
- **云函数部署包打包工具** —— 生成云函数部署用的 zip

启动后的主界面：

![启动窗口](img/MainEntrance.png)

> 仅支持 Windows 系统。

---

## 运行环境

- **操作系统**：Windows 7 / 10 / 11
- **Python**：3.9 或更高（用 exe 版则不需要装 Python）

下限取 3.9 的原因：PyQt5-sip、chardet 等依赖的新版本已要求 3.10，pywin32 要求 3.9；而 Python 3.7 与 3.8 分别已于 2023、2024 年终止支持。用更低的 Python 版本时，pip 会直接提示版本不符，不会装出一个跑不起来的环境。

CI 覆盖 3.9 ~ 3.14，每个版本都实际跑测试。

---
## 下载安装

### 方式一：直接运行 exe（推荐，不需要装 Python）

到 [Releases 页面](https://github.com/laincat/AwesomePyKit/releases) 下载 `Awespykit.exe`，双击即可运行。

想固定一个永远指向最新版的下载地址，可以用：

```
https://github.com/laincat/AwesomePyKit/releases/download/dev-latest/Awespykit.exe
```

> 这个地址指向的是跟着 `main` 分支自动构建的开发版，可能包含尚未充分验证的改动。
> 想要稳定版本请到 Releases 页面下载带版本号的那一份。

### 方式二：pip 安装

> **先说结论：不能直接用 `pip install Awespykit`。**
>
> PyPI 上的 `Awespykit` 是原作者发布的，目前只到 **2.1.0**，不包含本仓库的修复。
> 本仓库的版本要从下面两个地址装。

**装最新版**（地址固定，不需要改）：

```cmd
pip install git+https://github.com/laincat/AwesomePyKit.git@main
```

需要已安装 git。这是唯一一个「地址永远不变、内容永远是最新」的安装方式 ——
因为它直接从仓库源码构建，而不是从附件下载。

**装指定版本**（不需要 git）：

```cmd
pip install https://github.com/laincat/AwesomePyKit/releases/download/2.2.0/awespykit-2.2.0-py3-none-any.whl
```

这个地址里带版本号，升级到新版本时需要把 `2.2.0` 换成新版本号 —— 到
[Releases 页面](https://github.com/laincat/AwesomePyKit/releases) 找到对应版本，
右键复制 `awespykit-*.whl` 的链接即可。

> 为什么没有「永久指向最新 wheel」的地址：pip 要求 wheel 文件名里必须包含版本号，
> 所以附件名无法固定。这一点是 pip 的限制，不是本仓库的选择。

两种方式都会由 pip 自动安装好依赖（PyQt5、fastpip、pywin32 等）。

安装完成后，在命令行输入 `rpk` 即可启动。如果提示 `rpk 不是内部或外部命令`，
说明 Python 的 Scripts 目录没在 PATH 里，请自行添加，或用 `python -m awespykit` 启动。

> **注意**：用 pip 安装或从源码运行时，不要用 Awespykit 去卸载或升级它自己所在的
> Python 环境里的 Awespykit、PyQt5，否则可能造成文件残留或程序意外退出。
> 直接运行 exe 没有这个限制。

### 方式三：从源码运行

```cmd
git clone https://github.com/laincat/AwesomePyKit.git
cd AwesomePyKit
pip install -r requirements.txt
python src\awespykit\runpykit.py
```

注意：`pip install -r requirements.txt` 会把依赖装进你当前使用的 Python 环境。
如果不想污染现有环境，建议先建一个虚拟环境再执行。

用 PyCharm 打开项目时，请右键 `src` -> `awespykit` 目录，选择
「将目录标记为 -> 源代码根目录」，否则导入提示会有误报。

---

## 功能说明

### 包管理器

封装了 pip 命令，用图形界面管理多个 Python 环境里的包。

- 支持常规 Python 环境、venv 虚拟环境、Anaconda 主环境与虚拟环境
- 批量安装、按版本号安装、检查更新、批量卸载、批量升级
- 右键环境可打开目录、复制路径、导出包列表（requirements.txt）
- 右键包可升级、卸载、强制重装、查询导入名

> 批量升级/卸载前请确认了解各包之间的依赖关系，以免破坏环境。

![包管理器](img/PackageManager.png)

### 程序打包工具

封装了 PyInstaller 的常用命令。

- 支持选择不同环境进行打包，可在项目下创建 venv 虚拟环境
- 打包前检查项目所用模块在环境中的安装情况，缺什么可一键安装
- 支持多套配置的保存与应用；支持自定义版本信息、图标、UPX 等

![程序打包工具](img/PyinstallerTool.png)

### 镜像源设置工具

一键切换 pip 使用的镜像源，支持保存自己常用的镜像源地址。

![镜像源设置工具](img/IndexUrlTool.png)

### 模块安装包下载器

下载包及其依赖的安装文件（.whl / .tar.gz），适合离线安装或分发。

- 支持从 requirements.txt 批量读取
- 支持指定平台、Python 版本、解释器实现、ABI 等兼容条件

![模块安装包下载器](img/PackageDownloader.png)

### 云函数部署包打包工具

把云函数项目连同依赖打包成可上传的 zip 部署包，可配置排除文件。

---

## 常见问题

**Q：双击 exe 没反应？**

新版本会在依赖版本不符时弹出对话框说明原因。如果完全没有窗口出现，请确认：
- 下载的 exe 是否完整（对照 `Awespykit.exe.sha256` 校验）
- 是否被杀毒软件拦截（单文件打包的程序偶尔会被误报，可加入白名单）

校验下载文件（PowerShell）：

```powershell
Get-FileHash .\Awespykit.exe -Algorithm SHA256
```

**Q：`pip install Awespykit` 装到的不是这个版本？**

是的，PyPI 上的包名由原作者持有，本仓库的版本要用[方式二](#方式二pip-安装)里的地址安装。

**Q：提示缺少模块 / 导入失败？**

用包管理器或打包工具时若提示某模块未安装，按提示安装即可。
如果提示的是 `fastpip` 版本不符，按弹窗里的命令升级。

**Q：配置文件存放在哪里？**

`%LOCALAPPDATA%\Awespykit`（配置在 `config` 子目录，自定义主题放 `themes` 子目录）。
卸载程序不会删除这个目录，需要清理可手动删除。

---

## 关于本项目

本仓库是 [hrpzcf/AwesomePyKit](https://github.com/hrpzcf/AwesomePyKit) 的延续。
原作者自 2024 年 10 月起没有再更新，本仓库在其基础上继续维护。

与原版相比，本仓库的主要差别：

- 修复了一批会在使用中真实碰到的问题，详见各版本的 Release 说明
- 包内导入规范化，不再依赖 sys.path 的注入顺序
- 加入 CI（多 Python 版本测试 + exe 构建冒烟测试）与自动发布
- 支持三种启动方式：rpk 命令、python -m awespykit、直接运行脚本

界面布局与操作方式保持原样，原有的配置文件可以直接继续使用。

**授权**：沿用原项目的 [GPL-3.0](./LICENSE) 许可，作者署名保留原样。

---

## 开发与贡献

### 环境准备

```cmd
pip install -r requirements-dev.txt
```

### 常用命令

```cmd
ruff check src/ tests/ packaging/      :: 静态检查
python -m pytest tests                 :: 测试（无头运行，不需要显示器）
python -m build --outdir dist-python   :: 构建 pip 分发包
python packaging/make_version_info.py  :: 生成 exe 的版本信息
python -m PyInstaller --noconfirm packaging/awespykit.spec   :: 构建 exe
```

测试与 CI 都通过 `QT_QPA_PLATFORM=offscreen` 无头运行，因此在没有图形界面的环境
（CI、远程终端）里也能跑。

### 项目结构

```
src/awespykit/
    runpykit.py      程序入口（同时支持 rpk 命令、python -m awespykit、直接运行脚本）
    __info__.py      版本号等基本信息
    com/             通用组件：枚举、自定义控件、线程封装、导入名对照表
    logic/           各功能窗口的逻辑
    settings/        配置读写（JSON，带类型还原与容错）
    ui/              由 Qt Designer 生成的界面代码，请勿手工修改
    utils/           工具：打包、虚拟环境、导入检查、主题
    res/             图标、样式表等资源（res.py 由 res.qrc 生成，请勿手工修改）
packaging/           PyInstaller 配置与发布辅助脚本
tests/               测试
```

### 发布流程

不需要本地打包，产物由 GitHub Actions 自动构建，分两种：

**开发版** —— 每次推送到 `main` 都自动构建并发布，版本号由 git 提交历史推导
（形如 `2.2.1.dev3`）。它挂在固定的 tag `dev-latest` 下，每轮覆盖同名附件，
所以下载地址恒定不变：

```
https://github.com/laincat/AwesomePyKit/releases/download/dev-latest/Awespykit.exe
```

开发版会标记为 Pre-release，也不会占用 `releases/latest` —— 那个位置留给正式发版。

**正式发版** —— 在 GitHub 上创建 release（打 tag）即可，产物附件会补到那一条 release 上。
标签需要是合法的版本号，例如 `v2.3.0`、`v2.3.0-rc1`；工作流会先把标签规范化为
PEP 440 版本号，无法转换时会在第一步就明确报错指出问题。

两种方式都会：构建 sdist 与 wheel → 构建 Windows 单文件 exe 并启动它做冒烟测试
→ 计算全部产物的 SHA256 → 上传附件。

只想验证打包配置、不发布时，手动触发工作流（`workflow_dispatch`）即可，
产物只留在 Actions 的 artifact 里（保留 14 天）。

### 依赖自动更新

Dependabot 每周检查 `requirements*.txt` 与 workflow 里引用的 Action。
patch 级更新会在 CI 通过后自动合并；minor 与 major 留给人看 ——
这个项目要把 exe 发给真实用户，打包工具链的版本变化需要人工确认。
