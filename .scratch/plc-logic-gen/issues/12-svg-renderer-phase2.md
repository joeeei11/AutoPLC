---
Status: ready-for-agent
---

# 12 — SVG 渲染器阶段二——并联分支 + 功能块（+ 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

在阶段一 SVG 渲染器基础上，增加对 `Branch`（并联分支）和 `FunctionBlock` 的渲染支持。

并联分支布局：
- `Branch` 内每条并联路径独占一行，垂直堆叠
- 分支左侧和右侧各有垂直连接线将各路径汇合
- 分支整体高度 = 所有路径行高之和

功能块布局：
- `FunctionBlock` 渲染为矩形框，框内显示类型名（TON/CTU 等）和实例名
- 框左侧为输入引脚，右侧为输出引脚，显示引脚名称
- 功能块宽度固定（大于普通触点），高度根据引脚数量自适应

扩展测试：含 `Branch` 的 `PLCProgram` 渲染后 SVG 包含预期的分支线元素；含 `FunctionBlock` 的 `PLCProgram` 渲染后 SVG 包含矩形和引脚标签。

## Acceptance criteria

- [ ] 含两条并联路径的 `Branch` 在 SVG 中正确显示两行，并有垂直汇合线
- [ ] `FunctionBlock`（如 TON 定时器）渲染为矩形框，显示类型名和实例名
- [ ] 阶段一的串联 Rung 渲染结果不受影响（无回归）
- [ ] 测试全部通过，不依赖外部服务

## Blocked by

- `issues/04-svg-renderer-phase1.md`
