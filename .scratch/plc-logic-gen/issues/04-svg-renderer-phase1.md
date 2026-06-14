---
Status: ready-for-agent
---

# 04 — SVG 渲染器阶段一——串联 Rung（纯串联布局 + 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现 SVG 渲染器的第一阶段：将只含串联元素的 `PLCProgram`（无 `Branch`、无 `FunctionBlock`）渲染为标准梯形图 SVG 字符串。

布局规则：
- 左右两条垂直母线（Power Rails）
- 每个 Rung 独占一行，从左母线水平延伸到右母线
- 元素固定宽度，从左到右依次排列
- 常开触点符号：`--| |--`，常闭触点：`--|/|--`，线圈：`--( )--`
- 每个元素下方显示变量名标签
- 纯 SVG 字符串输出，不依赖外部图形库

测试：输入已知 `PLCProgram`，断言输出 SVG 包含预期元素数量和符号字符（不测像素坐标）。

## Acceptance criteria

- [ ] 单个 Rung 含两个常开触点 + 一个线圈时，SVG 包含对应符号
- [ ] 多个 Rung 时，每行独立渲染，垂直堆叠
- [ ] 每个元素下方显示变量名
- [ ] 输出是合法的 SVG 字符串（可直接嵌入 HTML）
- [ ] 测试全部通过，不依赖外部服务

## Blocked by

- `issues/01-ld-data-model.md`
