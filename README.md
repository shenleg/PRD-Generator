# 需求协作 Skills

本仓库维护两个独立、通过共享工作区协作的 Skill：需求分析负责“想清楚”，文档生成负责“写清楚”。源码、文档和测试代码按 Skill 分类，共享规范与历史证据单独保留。

## 按 Skill 查找

| Skill | 当前范围 | 源码 | 文档 | 测试 |
| --- | --- | --- | --- | --- |
| `requirement-analyst` | 原阶段 1～8及最终收口完成；真实下游联调仍需补验 | [生产目录](skill/requirement-analyst/) | [文档导航](docs/requirement-analyst/README.md) | [测试与历史证据](tests/requirement-analyst/README.md) |
| `prd-generator` | 阶段 0～5 已验收；支持首稿、未发布稿同步、排版及手改处理，评审和发布尚未实现 | [生产入口](skill/prd-generator/SKILL.md) | [文档导航](docs/prd-generator/README.md) | [测试说明](tests/prd-generator/README.md) |

阶段记录说明各自的通过范围。合成案例、程序回归、模型行为、人工认可和真实业务签核不混称；草稿生成、格式校验或阶段验收均不等同于正式发布批准。

## 目录

```text
skill/                         可安装的生产载荷，两个 Skill 并列
├── requirement-analyst/
└── prd-generator/
docs/                          当前维护文档
├── requirement-analyst/        规格、执行计划、安装说明和样例说明
├── prd-generator/              规格与执行计划
└── shared/                     写作规范、仓库布局说明
tests/                         统一测试入口与按 Skill 分类的维护代码
├── requirement-analyst/        分析测试、辅助模块及重放驱动
├── prd-generator/              生成测试、辅助模块及格式重放驱动
├── fixtures/<skill>/           按 Skill 分类的输入，原文字节不变
├── expected/<skill>/           按 Skill 分类的人工参考，保留认可范围
├── scenarios/<skill>/          按 Skill 分类的场景剧本
└── results/                    既有运行记录，不改旧指纹
tools/                         跨 Skill 最小交接消费者，开发验证用
workspace-sandbox/             历史试跑证据，保留原位置
```

- [目录职责及历史路径约定](docs/shared/repository-layout.md)
- [分阶段执行文档写作规范](docs/shared/staged-execution-guide.md)
- [统一测试入口](tests/README.md)
- [最小交接消费者](tools/README.md)：不是正式 PRD Generator，不随产品安装。

## 安装与使用

需求分析 Skill 的安装、普通对话触发和当前会话承接见 [安装说明](docs/requirement-analyst/installation.md)。现有 `.claude/skills/requirement-analyst` 仍指向唯一生产目录；阶段 2 修改分析侧接收能力，不改安装链接。

`prd-generator` 已有 [Skill 入口](skill/prd-generator/SKILL.md)，支持首次草稿、同一分析输入重复生成及未发布工作稿的显式增量同步；两个 Skill 需并列安装。门禁、比较、编号、统一保存及恢复用法见 [脚本说明](skill/prd-generator/scripts/README.md)，阶段 4 的实际验证与待验收项见 [进度记录](tests/results/prd-generator/stage-4.md)。本次未改实际安装链接，不把显式加载试跑称为安装自动触发。阶段 5 编辑和手改处理的实施方案、参考及四次隔离模型试跑已获认可，实现、回归、模型及当前源码重放完成，并获用户最终语义认可，见 [阶段记录](tests/results/prd-generator/stage-5.md) 与 [最终认可](tests/results/prd-generator/stage-5-final-approval.json)；评审、发布及发布后另建工作稿仍属后续阶段。

## 运行全部测试

Python 3.10+，使用已有依赖缓存：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

统一入口发现两组测试，不静默漏掉子目录。测试不调用模型、不启动浏览器；写入测试使用临时目录，实际模型及人工认可仍以保存证据为准。`--offline` 需要依赖已缓存，新环境按安装说明准备依赖。

阶段实施范围以用户指令和阶段记录为准；不删除历史材料，不自动提交、推送、合并或打标签。
