---
Status: ready-for-agent
---

# 06 — React 前端基础——输入框 + SVG 展示 + Monaco Editor

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现 React 前端的核心界面，完成从输入到可视化的完整用户流程。中文界面。

布局：
- **左侧**：自然语言输入框（多行）、品牌选择下拉（通用 ST / 西门子 SCL / 罗克韦尔 L5X）、LLM 选择下拉（Claude / OpenAI）、生成按钮、错误提示区
- **中间**：SVG 梯形图展示区（可缩放，支持 SVG 字符串直接渲染）
- **右侧**：Monaco Editor 显示可编辑 ST 代码（只读模式先），重新渲染按钮（调用 `/api/validate` + 重新渲染 SVG）

Monaco Editor 可编辑后，修改 ST 代码并点击"重新渲染"时，前端将修改后的 ST 文本回填到 `PLCProgram.st_code` 并重新请求 `/api/validate`，若合法则刷新 SVG。

## Acceptance criteria

- [ ] 输入描述后点击"生成"，SVG 梯形图显示在中间区域
- [ ] Monaco Editor 同步显示对应 ST 代码
- [ ] 切换 LLM 下拉后重新生成使用新模型
- [ ] 输入描述不足时，界面显示明确的中文错误提示
- [ ] 修改 Monaco Editor 内容后点击"重新渲染"，SVG 区域刷新
- [ ] 在 `http://localhost:5173` 可正常访问

## Blocked by

- `issues/05-fastapi-backend-basic.md`
