---
Status: done
---

# 10 — OpenPLC 仿真客户端 + FastAPI `/simulate` 端点

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现 OpenPLC REST 客户端，并在 FastAPI 中暴露仿真端点。OpenPLC Runtime 通过 Docker 运行在本地 8080 端口。

客户端流程：上传 `.st` 文件 → 触发编译 → 等待编译完成 → 启动 PLC → 轮询读取变量状态。

后端端点：

`POST /api/simulate`
- 请求体：`{ st_code: string }`
- 响应：`{ task_id: string }`（异步任务）

`GET /api/simulate/{task_id}/status`
- 响应：`{ status: "compiling"|"running"|"error", variables: { [name]: value }, error_message?: string }`

OpenPLC 地址通过环境变量 `OPENPLC_URL` 配置（默认 `http://localhost:8080`）。

## Acceptance criteria

- [ ] `POST /api/simulate` 返回 `task_id`
- [ ] 轮询 `GET /api/simulate/{task_id}/status` 直到 `status` 变为 `running`
- [ ] `running` 状态时 `variables` 字段包含 PLC 变量键值对
- [ ] OpenPLC 不可达时返回 `status: "error"` 和明确的 `error_message`
- [ ] `OPENPLC_URL` 环境变量可覆盖默认地址

## Blocked by

- `issues/05-fastapi-backend-basic.md`
