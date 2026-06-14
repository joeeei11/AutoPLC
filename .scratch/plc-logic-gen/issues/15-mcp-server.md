---
Status: ready-for-agent
---

# 15 — MCP Server 四个工具（generate/validate/simulate/export）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

基于 MCP Python SDK 实现 MCP Server，暴露四个工具，让 Claude Code 用户可在对话中完成完整闭环。

四个工具：

**`generate_plc_logic(description, brand, llm)`**
- 调用后端 `/api/generate`
- 返回：`PLCProgram` JSON 字符串 + SVG 字符串

**`validate_plc_logic(plc_program_json)`**
- 调用后端 `/api/validate`
- 返回：验证错误列表（空列表表示合法）

**`simulate_and_read(st_code)`**
- 调用后端 `/api/simulate`，轮询直到状态变为 `running` 或 `error`
- 返回：变量状态键值对 JSON 字符串

**`export_plc_file(plc_program_json, brand)`**
- 调用后端 `/api/export`
- 返回：文件内容（base64 编码）+ 推荐文件名

同时编写 `mcp_config.json`，说明 Claude Code 如何接入此 MCP Server。

## Acceptance criteria

- [ ] MCP Server 可通过 `python mcp_server/server.py` 启动
- [ ] Claude Code 通过 `mcp_config.json` 配置后可识别四个工具
- [ ] `generate_plc_logic` 返回包含 SVG 的响应
- [ ] `simulate_and_read` 在 OpenPLC 不可达时返回明确的错误信息（不挂起）
- [ ] `export_plc_file` 返回的 base64 内容解码后是合法的对应格式文件

## Blocked by

- `issues/05-fastapi-backend-basic.md`
- `issues/09-export-endpoint-ui.md`
- `issues/10-openplc-simulator.md`
