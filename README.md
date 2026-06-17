# Contract Review RAG Agent

基于 FastAPI + Vue 构建的合同审查 RAG 应用，支持合同上传、条款检索、风险分析、引用溯源和聊天历史管理。

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [核心流程](#核心流程)
- [项目结构](#项目结构)
- [GitHub 注意事项](#github-注意事项)

## 项目简介

本项目面向合同审查场景，使用 RAG 技术将用户上传的合同文件解析、切分并写入向量数据库。用户提问时，系统会在当前用户可访问的合同片段中检索相关条款，并结合大模型生成带引用依据的风险分析结果。

系统支持用户登录、合同文件管理、流式问答、会话历史和多用户数据隔离，适合作为合同审查、企业知识库问答或 RAG Agent 项目的学习与展示案例。

## 核心特性

- 合同管理：支持 PDF、DOCX、PPTX、TXT、MD 文件上传、解析、切分和删除
- RAG 检索：基于 ChromaDB 存储合同向量，按 `user_id` 和 `contract_id` 过滤检索范围
- 风险分析：围绕结论、风险点、原文依据和修改建议生成合同审查意见
- 引用溯源：返回命中的合同片段、页码、段落、切片编号和相似度分数
- 流式输出：用户提问后实时展示检索状态、思考过程和模型回答
- 会话管理：支持聊天记录保存、历史会话查看和删除
- 用户隔离：基于 token 鉴权，确保用户只能访问自己的合同和会话

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端服务 | FastAPI, SQLAlchemy, Pydantic |
| 前端界面 | Vue 3, Vite, lucide-vue-next |
| 向量数据库 | ChromaDB |
| 文档解析 | PyMuPDF, python-docx, python-pptx |
| 大模型服务 | Qwen / DashScope compatible-mode API |
| 数据存储 | SQLite 默认，可切换 MySQL |

## 快速开始

### 后端启动

```powershell
cd contract-rag-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8001
```

后端接口文档：

```text
http://127.0.0.1:8001/docs
```

### 前端启动

```powershell
cd contract-rag-agent
.\run_frontend.ps1
```

前端页面：

```text
http://127.0.0.1:5173
```

## 配置说明

复制 `.env.example` 为 `.env`，并填写自己的 Qwen / DashScope API Key：

```text
DASHSCOPE_API_KEY=your-api-key
SECRET_KEY=replace-with-a-random-string
```

本仓库只提供代码，不提供可公开调用的模型额度。运行者需要配置自己的 API Key，模型调用产生的费用由该 API Key 所属账号承担。请不要将 `.env` 提交到 GitHub。

本地默认使用 SQLite：

```text
DATABASE_URL=sqlite:///./data/app.db
```

如需切换到 MySQL：

```text
DATABASE_URL=mysql+pymysql://user:password@host:3306/contract_rag?charset=utf8mb4
```

## 核心流程

```text
注册 / 登录
  -> 上传合同
  -> 解析为 Document
  -> 按合同规则切分 chunk
  -> 调用 embedding 模型生成向量
  -> 写入 ChromaDB
  -> 用户提问
  -> 检索当前用户的相关合同片段
  -> 结合历史对话和引用片段构造 prompt
  -> 流式生成合同审查结果
  -> 保存聊天历史
```

## 项目结构

```text
contract-rag-agent/
├── backend/
│   ├── agent/              # 合同审查 Agent 流程
│   ├── db/                 # 数据库连接与 ORM 模型
│   ├── routers/            # FastAPI 路由
│   ├── security/           # 登录鉴权与 token
│   └── services/           # 文档解析、切分、检索、向量库、模型调用
├── frontend/
│   ├── src/                # Vue 页面与接口调用
│   ├── package.json
│   └── vite.config.js
├── data/                   # 本地运行数据，上传 GitHub 时忽略
├── logs/                   # 本地日志，上传 GitHub 时忽略
├── .env.example            # 环境变量模板
├── requirements.txt        # 后端依赖
├── run_backend.ps1
└── run_frontend.ps1
```

## GitHub 注意事项

以下内容不应提交到 GitHub：

- `.env`
- `.venv/`
- `data/`
- `logs/`
- `test_files/`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `*.pyc`
- `*.db`
- `*.sqlite`
- `*.sqlite3`

上传前建议执行：

```powershell
git status --short
```

确认只提交源码、配置模板和项目文档。
