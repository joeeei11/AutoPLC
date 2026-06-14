---
Status: ready-for-agent
---

# 13 — LLM 生成器升级——支持功能块和并联分支

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

升级 LLM 生成器的 System Prompt 和 PydanticAI schema，使其能在需要时生成包含 `FunctionBlock` 和 `Branch` 的完整 `PLCProgram`。

升级内容：
- System Prompt 增加功能块使用指引（何时用 TON/TOF/CTU，引脚连接方式）
- System Prompt 增加并联分支使用指引（OR 逻辑时用 Branch）
- 在已有 mock 测试基础上，补充含功能块和并联分支的生成场景测试

## Acceptance criteria

- [ ] 输入"电机在温度超过 80°C 时停止，延时 5 秒后重启"时，生成结果包含 TON 定时器功能块
- [ ] 输入含 OR 逻辑的描述时，生成结果包含 `Branch`
- [ ] 生成结果仍通过 LD 验证器（Issue 02）的所有检验
- [ ] 新增的 mock 测试全部通过

## Blocked by

- `issues/03-llm-generator-basic.md`
- `issues/12-svg-renderer-phase2.md`
