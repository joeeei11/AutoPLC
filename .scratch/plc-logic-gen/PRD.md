---
Status: ready-for-agent
---

# PRD：PLCLogicGen — 自然语言驱动的 PLC 逻辑生成工具

## Problem Statement

PLC（可编程逻辑控制器）工程师在编写控制逻辑时，需要熟悉特定品牌的编程语言（西门子 SCL、罗克韦尔 L5X、标准 IEC 61131-3 ST）及梯形图（Ladder Diagram）规范。这对于初学者或跨品牌切换的工程师门槛极高，且重复性的逻辑编写耗时耗力。工程师无法直接用自然语言描述控制意图并立即得到可验证、可导出的 PLC 代码。

## Solution

PLCLogicGen 是一个 Web 工具（同时暴露 MCP Server 接口），用户用中文自然语言描述控制逻辑，系统通过 LLM 生成结构化的梯形图（LD）数据模型，实时渲染为 SVG 可视化图形，同时输出对应的 ST 结构化文本副本。用户可在 Monaco Editor 中微调 ST 代码，选择目标品牌后导出相应格式文件，并可一键上传至 OpenPLC 仿真器验证逻辑正确性。MCP Server 让 Claude Code 用户可以在对话中直接完成生成 → 验证 → 仿真 → 导出的完整闭环。

## User Stories

1. 作为 PLC 工程师，我想输入"电机在温度超过 80°C 时停止，延时 5 秒后重启"，立即看到对应的梯形图 SVG，以便快速理解生成的控制逻辑。
2. 作为 PLC 工程师，我想在不懂编程语言语法的情况下，用中文描述控制需求就能得到合法的 PLC 代码，以便降低编程门槛。
3. 作为 PLC 工程师，我想看到生成的梯形图包含常开触点、常闭触点、线圈、定时器、计数器等完整元素，以便覆盖真实工控场景。
4. 作为 PLC 工程师，我想看到并联分支逻辑在 SVG 中正确渲染，以便验证多条件 OR 逻辑的正确性。
5. 作为 PLC 工程师，我想同时看到梯形图 SVG 和对应的 ST 文本代码，以便在两种视图间对照理解逻辑。
6. 作为 PLC 工程师，我想在 Monaco Editor 中手动修改 ST 代码后触发重新渲染，以便对生成结果进行微调。
7. 作为 PLC 工程师，我想选择目标品牌（通用 ST / 西门子 SCL / 罗克韦尔 L5X）后一键下载对应格式的文件，以便直接导入目标 PLC 开发环境。
8. 作为 PLC 工程师，我想点击"仿真"按钮后看到 OpenPLC 的变量状态实时刷新，以便验证逻辑在运行时的行为是否符合预期。
9. 作为 PLC 工程师，我想在输入描述不够清晰时收到明确的错误提示而不是乱生成，以便知道需要补充哪些信息。
10. 作为 PLC 工程师，我想切换 LLM（Claude / OpenAI），以便对比不同模型的生成质量。
11. 作为 Claude Code 用户，我想通过 MCP 工具 `generate_plc_logic` 直接在对话中生成 PLC 逻辑，以便在不打开浏览器的情况下完成代码生成。
12. 作为 Claude Code 用户，我想通过 MCP 工具 `validate_plc_logic` 验证 LD 数据结构的合法性，以便在集成流程中做自动化检查。
13. 作为 Claude Code 用户，我想通过 MCP 工具 `simulate_and_read` 上传 ST 代码并读取仿真变量状态，以便在对话中完成仿真验证。
14. 作为 Claude Code 用户，我想通过 MCP 工具 `export_plc_file` 导出指定品牌的 PLC 文件，以便在对话中完成完整的生成到导出闭环。
15. 作为运维工程师，我想通过 `docker compose up` 一键启动前端、后端和 OpenPLC 仿真器，以便在任意环境快速部署演示。
16. 作为 PLC 初学者，我想从预置的 5 个典型 Demo 场景（电机控制、传送带计数、PID 温控、急停联锁、液位控制）中选择加载，以便学习梯形图结构。
17. 作为 PLC 工程师，我想看到生成的 ST 代码符合 IEC 61131-3 规范，以便确保跨平台兼容性。
18. 作为 PLC 工程师，我想看到生成的西门子 SCL 文件符合 TIA Portal 导入格式，以便直接用于项目。
19. 作为 PLC 工程师，我想看到生成的罗克韦尔 L5X 文件中 `<Rung>` 元素格式正确，以便导入 Studio 5000。
20. 作为开发者，我想通过环境变量配置 Anthropic API Key 和 OpenAI API Key，以便在不修改代码的情况下切换模型。

## Implementation Decisions

### LD 数据模型（核心）

所有模块共用一套 Pydantic 数据模型，是整个系统的数据契约：

- `ContactType`：枚举，`NO`（常开）/ `NC`（常闭）
- `Contact`：触点，包含 `type`、`variable` 字段
- `Coil`：线圈，包含 `variable`、`negated` 字段
- `FunctionBlock`：功能块，包含 `block_type`（TON/TOF/CTU/CTD/CMP 等）、`instance_name`、`inputs`、`outputs` 字段
- `Branch`：并联分支，包含多条串联路径（`list[list[Element]]`）
- `Rung`：一行梯形图，包含串联元素序列（`list[Element | Branch]`），每个 Rung 有一个线圈作为输出
- `PLCProgram`：顶层模型，包含 `title`、`description`、`variables`（变量声明列表）、`rungs`（Rung 列表）、`st_code`（ST 文本副本）

### LLM 生成器

- 使用 litellm 统一调用接口，模型通过配置切换（默认 `claude-sonnet-4-6`）
- 使用 PydanticAI 强制 LLM 输出符合 `PLCProgram` schema 的结构化 JSON
- System Prompt 注入 IEC 61131-3 语法规范、安全约束（急停不可绕过）、变量命名规范
- LLM 一次请求同时生成 LD 结构和 ST 文本副本，保证两者语义一致
- 描述不足时 LLM 返回结构化错误，不产出无效的 `PLCProgram`

### LD 验证器

- 验证所有 `Contact` 和 `Coil` 引用的变量已在 `variables` 中声明
- 验证每个 `Rung` 有且仅有一个线圈输出
- 验证 `Branch` 内每条路径至少有一个元素
- 验证 `FunctionBlock` 的 `block_type` 属于已知类型

### SVG 渲染器

- 分两阶段交付：
  - **阶段一（Week 1）**：纯串联 Rung，从左到右布局，每个元素固定宽度，母线固定宽度
  - **阶段二（Week 3）**：支持 `Branch` 并联分支的垂直展开布局，支持 `FunctionBlock` 图形元素
- SVG 使用标准符号：常开触点 `--| |--`，常闭触点 `--|/|--`，线圈 `--( )--`
- 输出为纯 SVG 字符串，不依赖外部图形库

### 导出器

- 三个导出器共用同一份 `PLCProgram`，只在序列化逻辑上有差异
- **通用 ST**：直接使用 `PLCProgram.st_code` 字段内容
- **西门子 SCL**：对 ST 副本做关键字替换（`IF→IF`，添加 TIA Portal 头部注释和 FUNCTION_BLOCK 封装）
- **罗克韦尔 L5X**：将 `PLCProgram` 序列化为 XML，`<Rung>` 元素内嵌 ST 文本（L5X 的 Textual Rung 格式）

### OpenPLC 仿真客户端

- 通过 HTTP REST API 与 OpenPLC Runtime（Docker，端口 8080）交互
- 流程：上传 `.st` 文件 → 触发编译 → 启动 PLC → 轮询读取变量状态
- 变量状态以键值对返回：`{variable_name: current_value}`

### FastAPI 后端 API 契约

- `POST /api/generate`：接收自然语言描述 + 品牌 + LLM 选择，返回 `PLCProgram` JSON + SVG 字符串
- `POST /api/validate`：接收 `PLCProgram` JSON，返回验证结果列表
- `POST /api/simulate`：接收 ST 代码字符串，返回任务 ID
- `GET /api/simulate/{task_id}/status`：返回仿真状态和变量值
- `POST /api/export`：接收 `PLCProgram` JSON + 品牌，返回文件下载流

### MCP Server 四个工具

- `generate_plc_logic(description, brand, llm)` → 返回 `PLCProgram` JSON + SVG
- `validate_plc_logic(plc_program_json)` → 返回验证错误列表
- `simulate_and_read(st_code)` → 返回变量状态键值对
- `export_plc_file(plc_program_json, brand)` → 返回文件内容（base64）+ 文件名

### 前端

- React + Vite，中文界面
- 左侧：自然语言输入框 + 品牌选择下拉 + LLM 选择下拉 + 生成按钮 + Demo 场景快速加载
- 中间：SVG 梯形图展示区（可缩放）
- 右侧：Monaco Editor 显示可编辑 ST 代码 + 重新渲染按钮
- 底部：仿真状态面板（变量状态表格，轮询刷新）+ 导出按钮组

### 基础设施

- Docker Compose 编排：前端（Nginx）+ 后端（FastAPI）+ OpenPLC Runtime
- 环境变量：`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`DEFAULT_LLM`、`OPENPLC_URL`

## Testing Decisions

**好测试的标准：** 只测模块的外部行为（输入 → 输出），不测内部实现细节。测试应在不依赖外部服务（LLM API、OpenPLC）的情况下可以独立运行。

**需要测试的模块：**

- **LD 数据模型**：测试合法和非法的 Pydantic 模型实例化，确认 schema 约束有效
- **LD 验证器**：针对每种验证规则（未声明变量、缺少线圈、空分支路径等）各有一个测试用例，输入 `PLCProgram` 对象，断言返回的错误列表
- **SVG 渲染器**：输入已知 `PLCProgram`，断言输出 SVG 中包含预期的元素数量和符号字符串（不测像素坐标）
- **导出器（三个）**：输入相同 `PLCProgram`，断言输出字符串包含各格式的关键结构标志（ST 的 `VAR` 块，SCL 的 `FUNCTION_BLOCK` 头，L5X 的 `<Rung>` 标签）
- **LLM 生成器**：用 mock LLM 响应测试 PydanticAI 解析和错误处理路径，不调用真实 API

**暂不测试：** FastAPI 路由层（集成测试复杂度高，优先级低）、MCP Server（无测试先例）、前端组件、OpenPLC 客户端（依赖 Docker 环境）

## Out of Scope

- 梯形图（LD）图形化编辑器（用户只能通过自然语言生成或编辑 ST，不能拖拽元素）
- 功能图（FBD）、指令表（IL）、顺序功能图（SFC）等其他 IEC 编程语言
- 真实 PLC 硬件连接和下载
- 用户账号系统、历史记录云存储
- 罗克韦尔 L5X 的完整图形 LD 格式（仅支持 Textual Rung 变体）
- 多用户协作

## Further Notes

- OpenPLC Runtime 在 Windows Docker Desktop 上可直接运行，无需真实硬件
- 罗克韦尔 Studio 5000 有 30 天试用期，L5X 格式验证做一次即可
- Demo 场景：电机启停控制、传送带物料计数、PID 温控回路、急停安全联锁、液位控制
- 简历描述方向：基于 PydanticAI + litellm 构建 PLC 逻辑生成 Agent，支持 IEC 61131-3 LD 梯形图结构化输出与 SVG 可视化，适配西门子 SCL / 罗克韦尔 L5X 导出格式，通过 MCP Server 接入 Claude Code 完成生成→验证→仿真→导出完整闭环
