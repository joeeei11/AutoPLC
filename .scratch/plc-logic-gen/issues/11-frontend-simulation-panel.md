---
Status: ready-for-agent
---

# 11 — 前端仿真面板（仿真按钮 + 变量状态轮询）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

在前端添加仿真功能区，让用户点击"仿真"后能实时看到 OpenPLC 中的变量状态。

界面：
- "开始仿真"按钮（未生成内容时禁用）
- 仿真状态指示（编译中 / 运行中 / 错误）
- 变量状态表格：两列（变量名 / 当前值），每 2 秒轮询一次 `/api/simulate/{task_id}/status` 刷新
- 仿真出错时显示中文错误信息

## Acceptance criteria

- [ ] 点击"开始仿真"后显示"编译中"状态
- [ ] 编译成功后状态变为"运行中"，变量状态表格开始显示数据
- [ ] 变量状态每 2 秒自动刷新一次
- [ ] OpenPLC 不可达时显示"仿真器无法连接，请确认 Docker 已启动"
- [ ] 未生成内容时"开始仿真"按钮禁用

## Blocked by

- `issues/10-openplc-simulator.md`
