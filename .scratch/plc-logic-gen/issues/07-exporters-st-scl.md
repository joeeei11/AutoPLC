---
Status: ready-for-agent
---

# 07 — 通用 ST + 西门子 SCL 导出器（+ 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现两个导出器，均接受 `PLCProgram` 对象，返回对应格式的字符串。

**通用 ST 导出器**：
- 直接输出 `PLCProgram.st_code` 字段内容
- 在文件头部添加变量声明块（`VAR ... END_VAR`）
- 文件扩展名 `.st`

**西门子 SCL 导出器**：
- 以 ST 副本为基础，添加 TIA Portal 兼容的 `FUNCTION_BLOCK` 封装头
- 添加 TIA Portal 格式的头部注释（版本、作者占位）
- 文件扩展名 `.scl`

两个导出器各有测试：输入相同 `PLCProgram`，断言输出包含各格式的关键结构标志。

## Acceptance criteria

- [ ] ST 导出器输出包含 `VAR` 块和逻辑体
- [ ] SCL 导出器输出包含 `FUNCTION_BLOCK` 关键字和头部注释
- [ ] 两个导出器输入相同 `PLCProgram` 时，逻辑体内容一致（仅封装不同）
- [ ] 导出器不依赖外部服务，测试全部通过

## Blocked by

- `issues/01-ld-data-model.md`
