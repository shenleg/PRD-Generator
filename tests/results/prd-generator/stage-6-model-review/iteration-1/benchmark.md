# Skill Benchmark: prd-generator

**Model**: sonnet (Agent tool alias)
**Date**: 2026-11-18T02:19:38Z
**Evals**: 1, 2 (1 runs each per configuration)

## Summary

| Metric | With Skill | Old Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100% ± 0% | 35% ± 21% | +0.65 |
| Time | 387.1s ± 142.7s | 193.7s ± 27.2s | +193.4s |
| Tokens | 34028 ± 13250 | 21500 ± 1358 | +12528 |

## Notes

- 每配置每组一次；同一模型会话的后续轮不算新样本。
- 旧 Skill 如实拒绝是正确处理能力边界；不能计作成功执行新增操作。
- 数字来自实际产物；原因与确认措辞需人工核对。时间与 token 不作为效率结论。