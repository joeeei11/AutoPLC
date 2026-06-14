---
Status: ready-for-agent
---

# 16 — Docker Compose 编排（前端 + 后端 + OpenPLC）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

编写 `docker-compose.yml`，将前端、FastAPI 后端和 OpenPLC Runtime 三个服务编排在一起，实现 `docker compose up` 一键启动完整产品。

服务：
- **frontend**：Nginx 静态服务器，服务 React 构建产物，监听 80 端口
- **backend**：FastAPI 应用，监听 8000 端口，通过环境变量注入 API Key 和 OpenPLC 地址
- **openplc**：OpenPLC Runtime 官方 Docker 镜像，监听 8080 端口

网络：三个服务在同一 Docker 网络内，backend 通过服务名 `openplc:8080` 访问仿真器。

同时提供 `.env.example` 文件，列出所有需要配置的环境变量（`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`DEFAULT_LLM`）。

## Acceptance criteria

- [ ] `docker compose up` 后，`http://localhost` 可访问前端界面
- [ ] 前端可正常调用后端 API（`http://localhost/api/...` 通过 Nginx 反代到后端）
- [ ] 后端可访问 OpenPLC（`http://openplc:8080`）
- [ ] `.env.example` 文件列出所有必需环境变量及说明
- [ ] 复制 `.env.example` 为 `.env` 并填入 API Key 后，完整功能可用

## Blocked by

- `issues/06-react-frontend-basic.md`
- `issues/11-frontend-simulation-panel.md`
- `issues/15-mcp-server.md`
