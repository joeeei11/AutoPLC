---
Status: ready-for-agent
---

# 09 — FastAPI `/export` 端点 + 前端导出按钮

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

在后端添加导出端点，在前端添加导出按钮，完成"生成→下载文件"的完整路径。

后端端点：

`POST /api/export`
- 请求体：`{ plc_program: PLCProgram, brand: "generic"|"siemens"|"rockwell" }`
- 响应：文件下载流（`Content-Disposition: attachment`），文件名根据品牌自动生成（`.st` / `.scl` / `.L5X`）

前端：
- 在界面底部或右侧添加三个导出按钮：「下载 .st」「下载 .scl」「下载 .L5X」
- 点击后调用 `/api/export` 并触发浏览器文件下载
- 未生成内容时按钮禁用

## Acceptance criteria

- [ ] 点击「下载 .st」触发 `.st` 文件下载，内容包含 `VAR` 块
- [ ] 点击「下载 .scl」触发 `.scl` 文件下载，内容包含 `FUNCTION_BLOCK`
- [ ] 点击「下载 .L5X」触发 `.L5X` 文件下载，内容包含 `<Rung>` 标签
- [ ] 未生成内容时三个按钮禁用（不可点击）
- [ ] 文件名格式为 `<title>.<ext>`

## Blocked by

- `issues/07-exporters-st-scl.md`
- `issues/08-exporter-l5x.md`
