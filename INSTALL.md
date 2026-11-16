# 安装与调用

## 当前仓库

当前项目通过 `.claude/skills/requirement-analyst` 相对符号链接安装，唯一源码位于 `skill/requirement-analyst/`。POSIX 系统正常检出 Git 符号链接后即可发现，不复制第二份源码；`tests/`、`tools/` 和试用工作区不随 Skill 安装。

入口设置 `user-invocable: false`，因此不提供 `/requirement-analyst` 命令；普通需求分析场景仍可由模型自动调用。未禁用模型调用，也未设置 `context: fork`，沿用当前会话已有信息。安装后需启动新会话发现，不能仅凭当前旧会话列表判断未安装。

## 安装到其他项目

在目标项目 `.claude/skills/` 下放置 `requirement-analyst/` 完整生产目录，或将该**单个 Skill 目录入口**链接到本仓库的生产目录。先检查同名目标；存在时先比较，不覆盖、不删除其他版本。不要将整个 `.claude/skills` 目录改为链接。

本 Skill 的参考文件、Schema、模板和脚本需要一起保留。Python 3.10+，脚本依赖见生产目录的 `scripts/requirements.txt`；例如使用已有 uv 环境：

```bash
uv run --no-project --python /usr/bin/python3 \
  --with-requirements skill/requirement-analyst/scripts/requirements.txt \
  python -I -B .claude/skills/requirement-analyst/scripts/validate_analysis.py \
  /path/to/analysis-result.json
```

安装 Skill 不等于在系统 Python 中自动安装依赖。实际保存仍须使用已具备该依赖的解释器或上述隔离运行方式。

## 本次实际验证

使用已安装的本地 Claude Code 2.1.325，通过普通“内部报修撤回需求”提示启动真实 CLI：

- 模型实际调用 `Skill(requirement-analyst)`，从项目安装路径读取按需参考文件。
- init 的用户技能与斜杠命令列表均未暴露该技能；这与 `user-invocable: false` 一致，不表示模型无法发现。
- 续接同一 session，仅输入“两个问题都选推荐 A”，实际正确承接“派单前可撤”和“先完成操作生效”，没有重复追问这两个已回答规则。
- 仅启用 Skill/Read，权限模式 dontAsk，无人可回答的权限提示直接拒绝；没有跳过权限、修改设置或读取凭据。
- 第一条命令因变长 `--tools` 吃掉提示参数而失败，已保留；修正为用 `--` 分隔提示参数后，新尝试通过。

入库证据：`workspace-sandbox/stage-4/installation/verification.json`。用户明确授权仅提交脱敏证据，已去除实际会话编号、本机绝对路径和无关初始化元数据；保留必要工具调用、相对参考路径和模拟业务回答。同会话用文件内别名关联，原始输出与诊断留本地、由.gitignore排除。测试只读取可入库证据，不依赖本地原始会话，也不重新调用模型。

参考官方文档：

- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/cli-reference

下游测试 Skill 尚未开发，已按用户要求延期集成验证；它不是安装本分析 Skill 的前提。
