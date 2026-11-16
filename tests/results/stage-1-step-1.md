# 阶段 1 第 1 步：格式定义验证记录

本文记录四份 JSON Schema 的验证结果，不代表黄金样例、一致性校验或下游格式评审已经完成。

| 日期 | 场景编号 | 结果 | 追问轮数 | 无效问题数 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 2026-11-15 | S1-01 | pass | 不适用 | 不适用 | 13 个格式测试全部通过；不涉及分析对话，不计入 RA 场景指标 |

## 产出核对

- [x] 四份 Schema 均通过 JSON Schema Draft 2020-12 元格式校验。
- [x] 必填节、必填字段不能遗漏；可选节可省略，允许为空的条目数组可为空。
- [x] 分析状态、就绪度、输入类型、标签、条目状态、问题优先级、解决途径、问题状态、价值结论和技术结论的枚举均受约束。
- [x] 条目编号前缀与类别一致，本需求和跨需求引用的格式受约束；用户自带需求编号可保留。
- [x] 文档、项目资料来源必须带 `source_id`；用户回答可以仅通过轮次定位。
- [x] 假设、决策、矛盾的额外字段必填，决策确认时间必须为带时区的 RFC 3339 时间。
- [x] 范围声明、可选分析数组和技术评估依据的元素结构明确。
- [x] 新增字段不破坏旧格式读取，所有 Schema 引用通过本地注册表解析，不访问远程地址。

## 运行方法

在仓库根目录执行：

```bash
uv run --no-project --python /usr/bin/python3 \
  --with-requirements tests/requirements.txt \
  python -I tests/test_schemas.py
```

测试依赖固定在 `tests/requirements.txt`，不随 Skill 安装。

## 本次运行

先写测试再创建 Schema：首次执行因 `analysis-result.schema.json` 不存在而报 `FileNotFoundError`，符合预期。

创建 Schema 后，`uv run` 被执行环境的检查服务超时阻止，未能启动测试。改用首次运行时已创建、已安装相同依赖的解释器执行：

```bash
/root/.cache/uv/archive-v0/ktyN1PjjCLX7_PJJ/bin/python -I tests/test_schemas.py
```

实际结果：

```text
Ran 13 tests in 0.082s

OK
```

缓存路径仅记录本次实际执行方式；其他环境使用上面的 `uv run` 命令。

## 规格补充与边界

先在规格 9.5 补充了数组元素结构、修订号、范围条目、回答正文和引用表示，并补齐技术评估所需的可信程度、潜在影响、研发问题引用字段，再编写 Schema。

本步只验证格式。编号唯一性、引用是否存在、就绪度是否自洽等 9.6 的跨条目一致性规则，留给第 3 步的 `validate_analysis.py`；第 4 步才编写这些规则的业务反例。

`schema_version` 按规格使用 `1.0`，仍需第 6 步下游格式评审后定稿。本步没有编写黄金样例、报告模板、`SKILL.md`、检索脚本或 `update_analysis.py`。
