# 双 Skill 安装与使用

需求分析和 PRD 生成共享需求工作区，不共享写入职责。使用同一版本的两个完整生产目录，目录名分别为 `requirement-analyst` 和 `prd-generator`，并放在目标项目的 `.claude/skills/` 下。安装后请在目标项目打开新的 Claude Code 会话，按[快速上手](../shared/quickstart.md#2-动手示例撤销会议室预约)跑第一项需求。

## 安装到新项目或隔离试用项目

在本仓库根目录运行下列命令，将 `PROJECT` 换成目标项目目录。若已经安装任一同名 Skill，请先比较版本，不覆盖或删除现有安装。

```bash
PROJECT=/path/to/target-project
(
  set -eu
  mkdir -p "$PROJECT/.claude/skills"
  for skill in requirement-analyst prd-generator; do
    target="$PROJECT/.claude/skills/$skill"
    if [ -e "$target" ] || [ -L "$target" ]; then
      printf '目标已存在：%s\n' "$target" >&2
      exit 1
    fi
  done
  cp -R skill/requirement-analyst skill/prd-generator "$PROJECT/.claude/skills/"
)
```

也可在支持符号链接的系统中分别链接两个生产目录；不要链接整个 `.claude/skills`。保留每个 Skill 的 `SKILL.md`、脚本、参考、Schema 和模板，不安装测试、沙盒或 `tools/minimal_prd_consumer.py`。分析侧已有的仓库链接保持原样，阶段 7 使用另建的隔离项目验证。

## 依赖和验证

生产脚本需要 Python 3.10+，以及分析侧 `scripts/requirements.txt` 中的依赖。安装 Skill 不会替你安装 Python 依赖。以下示例从目标项目运行，只读检查**分析侧已创建的需求目录**：

```bash
uv run --no-project --python /usr/bin/python3 \
  --with-requirements .claude/skills/requirement-analyst/scripts/requirements.txt \
  python -I -B .claude/skills/prd-generator/scripts/check_gate.py /path/to/requirement
```

- 开启新会话确认发现新安装的入口。用自然语言提出需求分析，模型可以自动调用 `requirement-analyst`；分析入口没有用户斜杠命令。
- 对已有分析说“根据当前分析生成可追溯 PRD”，观察模型自动调用 `prd-generator`。也可以直接使用 `/prd-generator`。随后可在当前会话补充答案、同步文档或查看遗留事项；不使用 `context: fork`。
- 尚无分析时先进入分析，不让生成侧自行创建需求；PRD 写出的缺口可切回分析接收和补充，生成侧同步时核实后才关闭。任何业务发布仍须产品经理针对送审稿明示确认。

参考：[分析 Skill 安装说明](../requirement-analyst/installation.md)、[生成脚本说明](../../skill/prd-generator/scripts/README.md)、[阶段 7 实测记录](../../tests/results/prd-generator/stage-7.md)。
