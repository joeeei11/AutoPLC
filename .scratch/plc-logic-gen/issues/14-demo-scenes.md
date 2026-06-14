---
Status: ready-for-agent
---

# 14 — 5 个 Demo 场景预置数据 + 前端快速加载

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

准备 5 个典型工控场景的预置 `PLCProgram` JSON 数据，并在前端添加快速加载入口。

5 个 Demo 场景：
1. **电机启停控制**：启动按钮（NO）+ 自保持 + 停止按钮（NC）+ 电机线圈
2. **传送带物料计数**：光电传感器触发 CTU 计数器，满载（计数 ≥ 10）时停止传送带
3. **PID 温控回路**（简化版）：温度传感器比较块 + 加热线圈开关逻辑
4. **急停安全联锁**：多点急停（NC）串联 + 运行使能线圈，急停优先于启动
5. **液位控制**：高位传感器（NC）+ 低位传感器（NO）控制水泵启停

每个场景预置：描述文本（中文）+ 对应 `PLCProgram` JSON。

前端：在输入区上方添加"Demo 场景"下拉或按钮组，选择后自动填入描述文本并加载对应 `PLCProgram`，渲染 SVG。

## Acceptance criteria

- [ ] 前端展示 5 个可选 Demo 场景入口
- [ ] 选择任意 Demo 后，SVG 区域立即显示对应梯形图（不需要调用 LLM）
- [ ] Monaco Editor 同步显示对应 ST 代码
- [ ] 5 个预置 `PLCProgram` 均通过 LD 验证器检验
- [ ] 急停场景中急停触点为 NC（常闭）类型

## Blocked by

- `issues/06-react-frontend-basic.md`
- `issues/13-llm-generator-upgrade.md`
