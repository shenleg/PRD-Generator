# 阶段 1：格式夹具与预期对照

本文件将已认可协议和生成规格 §9.9 映射到实际合成检查，不是新业务答案，不宣称全部 `PG` 端到端场景已通过。

## 输入性质

夹具由 `tests/prd_fixture_support.py` 确定性构造，需求编号为 `SYNTHETIC-PRD`，正文、资料、确认人均注明合成。此辅助代码只放在测试目录，不随产品安装。不存在用真实用户回答填补测试的情况。

| 规则 | 保存的反例 | 应有结果 | 实际结果入口 |
| --- | --- | --- | --- |
| 1 | 缺失追溯必填集合 | `fail`，结构诊断 | `attempt-02/rule-01/process.json` |
| 2 | 正式编号计数器落后 | `fail`，编号诊断 | `attempt-02/rule-02/process.json` |
| 3 | 分析引用不存在 | `fail`，引用诊断 | `attempt-02/rule-03/process.json` |
| 4 | 正文编号无追溯 | `fail`，正文对应诊断 | `attempt-02/rule-04/process.json` |
| 5 | 推断条目缺可见标注 | `fail`，条目内标签诊断 | `attempt-02/rule-05/process.json` |
| 6 | 废止条目进入有效正文 | `fail`，状态诊断 | `attempt-02/rule-06/process.json` |
| 7 | 草稿类型与提示及分析不符 | `fail`，草稿诊断 | `attempt-02/rule-07/process.json` |
| 8 | 未列适用推断遗留项 | `fail`，遗留项诊断 | `attempt-02/rule-08/process.json` |
| 9 | 游离占位无缺口 | `fail`，占位诊断 | `attempt-02/rule-09/process.json` |
| 10 | 可见版本与元数据不符 | `fail`，文档信息诊断 | `attempt-02/rule-10/process.json` |
| 11 | 快照没有发布记录 | `fail`，快照诊断 | `attempt-02/rule-11/process.json` |
| 12 | 已交接缺口没有接收问题 | `fail`，唯一关联诊断 | `attempt-02/rule-12/process.json` |

表中路径相对于 `workspace-sandbox/prd-generator/stage-1/`。每个反例可能因共同约束产生其他诊断，不隐藏它们；必须包含指定规则的失败。最小合法工作稿 `attempt-02/valid/` 为 `pass / 0`；合法合成快照 `snapshot-valid/` 为 `pass / 0`，篡改快照 `snapshot-tampered/` 为规则 11 的 `fail / 2`。

## 额外边界

`test_prd_schemas.py`、`test_prd_validation.py` 在临时目录覆盖：旧追溯兼容、未知扩展、严格补丁字段、完整跨需求引用、历史编号身份、数字序号重复、隐藏编号和标注、缺口接收中断状态、无效关闭依据、待同步差异、坏事件、空 JSON、来源名称缺失降级和只读 CLI。

`test_prd_format_runs.py` 复核保存内容的指纹、真实响应与退出码，再使用公开驱动重放；不靠“脚本自报通过”代替保存证据检查。

## 重放

输出必须是不存在的新目录：

```bash
uv run --offline --no-project --python /usr/bin/python3 \
  --with-requirements tests/requirements.txt \
  python -I -B tests/run_prd_format_checks.py --output /path/to/new-format-trial
```

不调用模型，不执行编号写入、缺口接收或发布器。自然语言忠实性和缺口充分性仍按人工认可参考要点评审，不由这些夹具代替。
