# PLCLogicGen 开发计划

> 创建于 2026-06-13，3-4 周完成，目标：写进简历 + 嘉立创 AI 编程岗面试亮点

---

## 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| LLM 调用 | **litellm** | 统一接口同时调 Claude + OpenAI，一行切换 |
| 结构化输出 | **PydanticAI** | 类型安全保证生成的 IEC 代码结构合法 |
| 后端 | **FastAPI** | |
| 前端 | **React + Monaco Editor** | 代码高亮编辑，ST/SCL/L5X 语法 |
| MCP Server | **mcp Python SDK** | 暴露工具给 Claude Code 直接调用 |
| PLC 仿真 | **OpenPLC Runtime（Docker）** | 唯一免费开源方案，支持标准 ST，有 REST API |
| 导出格式 | 西门子 `.scl` + 罗克韦尔 `.L5X`（XML）+ 通用 `.st` | |

---

## Week 1 — 核心生成引擎

**目标：** 自然语言 → 结构化 ST 代码，能跑通

关键任务：
- 定义 `PLCProgram` Pydantic 模型（变量声明 / 逻辑体 / 安全注释）
- litellm 封装层，支持 `claude-sonnet-4-6` 和 `gpt-4o` 可配置切换
- 提示词工程：System Prompt 注入 IEC 61131-3 语法规范 + 西门子 SCL 约束
- 生成结果验证：正则检查变量声明格式、关键字合法性
- CLI 可用：`python generate.py "电机在温度超过80°C时停止，延时5秒重启"`

**交付物：** 能稳定生成 ST 代码的 Python 包，有 10 个测试用例

---

## Week 2 — 多品牌导出 + 仿真器对接

**目标：** 生成的代码能导入仿真器运行

关键任务：
- `exporters/siemens.py`：输出 `.scl`，符合 TIA Portal 导入格式
- `exporters/rockwell.py`：输出 `.L5X` XML，符合 Studio 5000 格式
- OpenPLC Runtime 用 Docker Compose 跑起来（端口 8080）
- `simulator/openplc_client.py`：调 OpenPLC REST API 上传 `.st` → 编译 → 启动 → 读变量状态
- FastAPI 后端：`POST /generate`，`POST /simulate`，`GET /simulate/status`

**交付物：** API 跑通，生成的代码在 OpenPLC 里编译通过并能看到变量状态变化

---

## Week 3 — Web 前端

**目标：** 有界面可以演示、可以截图放简历

关键任务：
- 自然语言输入框 + 品牌选择（西门子 / 罗克韦尔 / 通用 ST）+ LLM 选择
- Monaco Editor 显示生成代码（ST 语法高亮）
- 仿真状态面板：变量实时刷新（轮询 OpenPLC）
- 导出按钮：直接下载 `.scl` / `.L5X` / `.st`
- Docker Compose 把前后端和 OpenPLC 一起编排

**交付物：** `docker compose up` 一键启动完整产品，录屏 Demo 可用

---

## Week 4 — MCP Server + 收尾

**目标：** 接入 Claude Code，简历亮点完整

关键任务：
- MCP Server 实现三个工具：
  - `generate_plc_code(description, brand, llm)` → 返回代码
  - `validate_plc_code(code)` → 返回验证结果
  - `simulate_and_read(code)` → 上传 OpenPLC 并返回变量状态
- 写 `mcp_config.json`，让 Claude Code 识别这个 MCP Server
- README 写清楚：安装 / 使用 / Claude Code 接入方式
- 收集 5-10 个典型案例（电机控制 / 传送带 / 温控逻辑）写进 Demo

**交付物：** 在 Claude Code 里直接对话生成 PLC 代码，MCP 工具可调用

---

## 目录结构

```
plc-logic-gen/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                # FastAPI 路由
│   │   ├── core/
│   │   │   ├── generator.py    # LLM 生成主逻辑
│   │   │   ├── models.py       # Pydantic IEC 数据模型
│   │   │   └── llm.py          # litellm 封装
│   │   ├── exporters/
│   │   │   ├── siemens.py      # → .scl
│   │   │   ├── rockwell.py     # → .L5X
│   │   │   └── openplc.py      # → .st
│   │   └── simulator/
│   │       └── client.py       # OpenPLC REST 客户端
│   └── requirements.txt
├── frontend/                   # React + Vite
├── mcp_server/
│   └── server.py               # MCP Server
├── tests/
│   └── test_cases/             # 10 个典型控制逻辑测试
└── docker-compose.yml
```

---

## 注意事项

- **OpenPLC 仿真**：纯软件仿真，不需要真实硬件，Docker 跑 OpenPLC Runtime 即可，Windows 上 Docker Desktop 能直接跑
- **罗克韦尔 L5X 验证**：Studio 5000 有 30 天试用，导入验证用一次就行，不需要持续授权
- **简历描述方向**：基于 PydanticAI + litellm 构建 PLC 逻辑生成 Agent，支持 IEC 61131-3 结构化文本输出，适配西门子 SCL / 罗克韦尔 L5X 导出格式，通过 MCP Server 接入 Claude Code 调用，集成 OpenPLC 仿真验证闭环
