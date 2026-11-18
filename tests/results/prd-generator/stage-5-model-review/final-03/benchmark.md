# Skill Benchmark: prd-generator

**Model**: sonnet (Agent tool alias; exact served model ID not exposed)
**Date**: 2026-11-17T20:21:20Z
**Evals**: 1, 2 (1 runs each per configuration)

## Summary

| Metric | With Skill | Old Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 93% ± 10% | 39% ± 15% | +0.54 |
| Time | 253.0s ± 64.7s | 190.6s ± 39.8s | +62.5s |
| Tokens | 42826 ± 3608 | 39089 ± 19871 | +3736 |

## Notes

- 每配置每组仅一次，共四份模型执行，不是稳定通过率估计。
- 保护断言通过不证明语义分流正确，人工仍需看实际差异。
- 旧Skill按已声明边界拒绝不是程序故障，但不计编辑完成。
- 时间与token保留通知原值；部分run有后续轮及调度暂停，不据此作效率结论。
- 用户坚持保留的回答来自已批准合成剧本，不是真实业务签核。