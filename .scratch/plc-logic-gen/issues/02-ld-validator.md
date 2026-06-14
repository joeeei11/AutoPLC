---
Status: ready-for-agent
---

# 02 — LD 验证器（四条验证规则 + 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现一个纯函数验证器，接受 `PLCProgram` 对象，返回结构化错误列表。不依赖 LLM 或外部服务。

四条验证规则：
1. 所有 `Contact` 和 `Coil` 引用的变量名必须已在 `PLCProgram.variables` 中声明
2. 每个 `Rung` 有且仅有一个 `Coil` 作为输出（含嵌套在 `Branch` 中的情况）
3. `Branch` 内每条并联路径至少有一个元素
4. `FunctionBlock.block_type` 属于已知类型集合（TON/TOF/CTU/CTD/CMP 等）

编写测试，每条规则对应至少一个合法用例和一个非法用例。

## Acceptance criteria

- [ ] 合法的 `PLCProgram` 返回空错误列表
- [ ] 未声明变量时返回含变量名的错误信息
- [ ] `Rung` 缺少线圈时返回对应错误
- [ ] `Rung` 有多个线圈时返回对应错误
- [ ] 空 `Branch` 路径时返回对应错误
- [ ] 未知 `FunctionBlock` 类型时返回对应错误
- [ ] 测试全部通过，不依赖外部服务

## Blocked by

- `issues/01-ld-data-model.md`
