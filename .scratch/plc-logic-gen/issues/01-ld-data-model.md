---
Status: done
---

# 01 — LD 数据模型定义（PLCProgram Pydantic schema）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

定义整个系统共用的梯形图数据契约。所有模块（生成器、验证器、渲染器、导出器）都以这套 Pydantic 模型作为输入输出类型。

核心类型：
- `ContactType`：枚举，`NO`（常开）/ `NC`（常闭）
- `Contact`：触点，含 `type`、`variable`
- `Coil`：线圈，含 `variable`、`negated`
- `FunctionBlock`：功能块，含 `block_type`（TON/TOF/CTU/CTD/CMP 等）、`instance_name`、`inputs`、`outputs`
- `Branch`：并联分支，含多条串联路径（每条路径是元素列表）
- `Rung`：一行梯形图，含串联元素序列（元素可以是 Contact/Coil/FunctionBlock/Branch）
- `Variable`：变量声明，含 `name`、`data_type`、`initial_value`
- `PLCProgram`：顶层模型，含 `title`、`description`、`variables`、`rungs`、`st_code`

同时编写数据模型的单元测试，覆盖合法和非法实例化场景。

## Acceptance criteria

- [ ] 所有类型可以从单一入口导入
- [ ] `PLCProgram` 可以包含多个 `Rung`，每个 `Rung` 可以嵌套 `Branch`
- [ ] 非法数据（如 `ContactType` 传入未知字符串）实例化时抛出 `ValidationError`
- [ ] 测试全部通过，不依赖外部服务

## Blocked by

None — can start immediately.
