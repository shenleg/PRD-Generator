# 双 Skill 安装与使用

需求分析和 PRD 生成共享工作区，分别负责写入各自的产物。安装器从同一份仓库安装两个 Skill 及其共用的 Python 依赖。

## 安装到新项目或隔离试用项目

把 **`install.py`、`skill/`、`offline/`** 放在同一个目录，原样拷进内网；也可以拷贝整个仓库。首次安装只读随附的 [wheel 包和 SHA-256 锁](../../offline/README.md)，不访问 PyPI，不需要 `uv`、pip 缓存或额外参数。缺包、哈希不符或架构不匹配会退出，不回退联网。

目标机器需有 Claude Code 和带 `venv`、`ensurepip` 的标准 CPython。离线包覆盖 **3.10–3.15** 常见 Windows、macOS、Linux 架构，范围见[平台清单](../../offline/README.md#支持范围)。部分 Linux 发行版单独提供 `python3-venv`；如系统缺少，需先通过内网系统包源或安装介质补齐。对话沿用客户端已配置的内网模型，安装器不访问或配置模型服务。

从 `install.py` 所在目录运行，把参数换成一个**已存在**的目标项目目录。路径含空格时保留引号。第一次试用可以选择另建的空目录。

**Windows（PowerShell）**：使用本机 Python 安装和运行，无需 WSL。

```powershell
py -3 install.py "C:\path\to\target-project"
```

没有 `py` 启动器时改用 `python`，确保它指向本机 Python 3.10+。

**macOS / Linux**：

```bash
python3 install.py "/path/to/target-project"
```

安装器先准备 `.claude/.prd-skills-venv/`，再把两个完整生产目录复制到 `.claude/skills/`，不安装测试、沙盒或 `tools/minimal_prd_consumer.py`。依赖只装到这个虚拟环境，不改系统 Python；不需要激活环境。虚拟环境按机器创建，不随项目提交或跨机器复制。若同名 Skill 或虚拟环境已存在，安装器会退出，不覆盖；试用新版可另选空目录。

## 工作区边界

- Windows 使用本地 NTFS，macOS 使用本地 APFS，Linux 使用本地 Linux 文件系统。目标项目和工作区都放在本地；同一工作区固定由同一个系统运行，不在 Windows、WSL 或其他系统之间混写。
- 支持按原事务恢复进程中断，包括原生 Windows：分析写入由下一次更新调用先恢复，PRD 写入按诊断用 `write_draft.py --recover` 恢复。遇到冲突保留现场，不手动删除锁文件或事务记录。
- PRD 正文、快照和引用资料按原始字节计算摘要。若将工作区交给 Git 或同步工具管理，请保留这些文件的原始换行；自动把 LF 换成 CRLF 也会被识别为修改。
- 不承诺网络盘或断电后的持久性，也不向绕过脚本锁的读写者提供跨文件原子快照。以上是支持范围，不是三端实测记录。

## 依赖和验证

安装成功后，在**目标项目目录**开启新的 Claude Code 会话，按[快速上手](../shared/quickstart.md#2-动手示例撤销会议室预约)保存第一项需求。Skill 会使用项目虚拟环境：Windows 为 `.claude/.prd-skills-venv/Scripts/python.exe`，macOS 和 Linux 为 `.claude/.prd-skills-venv/bin/python`。

要单独检查**分析侧已创建的需求目录**，可在目标项目目录运行以下只读门禁：

**Windows（PowerShell）**：

```powershell
& ".\.claude\.prd-skills-venv\Scripts\python.exe" -I -B ".\.claude\skills\prd-generator\scripts\check_gate.py" "C:\path\to\requirement"
```

**macOS / Linux**：

```bash
.claude/.prd-skills-venv/bin/python -I -B \
  .claude/skills/prd-generator/scripts/check_gate.py "/path/to/requirement"
```

- 用自然语言提出需求分析，模型可以自动调用 `requirement-analyst`；分析入口没有用户斜杠命令。
- 对已有分析说“根据当前分析生成可追溯 PRD”，或直接使用 `/prd-generator`。随后可在当前会话补充答案、同步文档或查看遗留事项；不使用 `context: fork`。
- 尚无分析时先进入分析，不让生成侧自行创建需求。任何业务发布仍须产品经理针对送审稿明示确认。

无模型安装验证见[安装态 smoke](../../tests/README.md#安装态-smoke)。[阶段 7 实测记录](../../tests/results/prd-generator/stage-7.md)只说明当时的试用范围。
