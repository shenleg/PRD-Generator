# Requirement Analyst：需求分析 Skill

先把需求想清楚，再向文档生成或测试分析交接。负责需求理解、拆分、澄清、业务与完整性分析、增量变更、历史对照、有依据的技术/体验判断，以及具体批准后的领域知识沉淀；不编写或发布正式PRD。

## 当前交付

阶段1～8已在用户批准范围内完成，阶段8已提交`be0f8ba`并合并`master`。整体收口记录见[最终验收](tests/results/final-acceptance.md)；收口文档及链路检查另在`chore/final-skill-acceptance`分支，尚未提交或合并，不推送、不自动打标签。

结论为阶段场景和本地接口链路验收通过，不是实际产品/研发签核；真实下游Skill集成经用户批准延期，八项量化评价指标的统一基线/阈值待后续样本评审。各阶段模拟材料、实际模型调用、确定性重放和人工批准的范围在验收报告中分别说明。

## 开始使用

1. 阅读[安装与调用](INSTALL.md)，保留完整`skill/requirement-analyst/`生产目录；当前项目通过单个相对链接安装，不复制测试或消费者。
2. 在普通对话中给出需求、工作区和项目；有需求编号则沿用。Skill沿用当前会话信息，由模型在需求分析场景调用，不提供独立斜杠命令。
3. 按展示的当前理解回答关键问题。用户可随时结束；未回答P0会保留，不因结束或校验pass而视为已就绪。
4. 正式JSON由更新器写入，报告仅为视图。下游使用唯一校验器，按`readiness`决定草稿用途；知识沉淀须另取具体批准。

## 导航

| 内容 | 入口 |
| --- | --- |
| 能力与数据协议 | [需求规格](需求分析skill-需求规格说明.md) |
| 阶段目标与退出条件 | [执行文档](分阶段执行文档.md) |
| Skill入口与按需参考 | [SKILL.md](skill/requirement-analyst/SKILL.md) |
| 校验、更新、资料及知识脚本 | [脚本说明](skill/requirement-analyst/scripts/README.md) |
| 最小交接消费者（开发验证，不随安装） | [消费者说明](tools/README.md) |
| 测试及已保存模型证据 | [测试说明](tests/README.md) |
| 最终验收与保留事项 | [验收报告](tests/results/final-acceptance.md) |

## 本地验证

Python 3.10+，Linux/Unix本地工作区。使用已具备依赖的解释器或uv隔离环境，不需要新增API Key：

```bash
uv run --offline --no-project --python /usr/bin/python3 --with-requirements tests/requirements.txt \
  python -I -B -m unittest discover -s tests -p 'test_*.py' -v
```

测试不调用模型、不启动浏览器，写入测试使用临时目录。`--offline`要求依赖已有缓存；新环境按[安装说明](INSTALL.md)准备依赖。实际模型自动调用/图像读取的历史证据不等同于每次测试重新运行模型。

## 边界

不包含正式PRD Generator、真实下游测试Skill、发布部署、完整产品前端、高保真制作、PDF/图像自动索引解析、向量检索、知识审批身份认证或旧知识替换/废止。当前锁和持久化面向可信、遵锁的Linux/Unix本地进程，不承诺Windows/NFS或恶意并发路径换链安全。具体降级与失败处理以生产参考为准。
