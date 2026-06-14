---
Status: ready-for-agent
---

# 08 — 罗克韦尔 L5X 导出器（+ 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现罗克韦尔 L5X 导出器，接受 `PLCProgram` 对象，输出符合 Studio 5000 导入格式的 XML 文件。

格式要求：
- 根元素为 `<RSLogix5000Content>`，包含版本和导出信息属性
- 变量声明映射为 `<Tag>` 元素，包含 `Name`、`DataType` 属性
- 每个 `Rung` 映射为 `<Rung>` 元素，`Type="N"`，内嵌 ST 文本（Textual Rung 格式）
- 文件扩展名 `.L5X`

编写测试：输入 `PLCProgram`，断言输出 XML 包含 `<RSLogix5000Content>`、`<Tag>` 和 `<Rung>` 标签，且 XML 可被标准库解析（格式合法）。

## Acceptance criteria

- [ ] 输出 XML 包含 `<RSLogix5000Content>` 根元素
- [ ] 变量声明输出为 `<Tag>` 元素
- [ ] 每个 Rung 输出为 `<Rung>` 元素，内含 ST 文本
- [ ] 输出 XML 可被 Python `xml.etree` 正确解析（无格式错误）
- [ ] 测试全部通过，不依赖外部服务

## Blocked by

- `issues/01-ld-data-model.md`
