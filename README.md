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
│   ├── main.py                         # FastAPI 应用入口，注册路由和初始化数据库
│   ├── config.py                       # 环境变量、模型、数据库、上传目录等配置
│   ├── schemas.py                      # Pydantic 请求和响应模型
│   ├── agent/
│   │   ├── contract_agent.py           # 合同审查 Agent 主流程，支持普通问答和流式问答
│   │   └── tools.py                    # Agent 工具封装，串联检索和风险分析
│   ├── db/
│   │   ├── models.py                   # 用户、合同文件、聊天会话、聊天消息 ORM 模型
│   │   └── session.py                  # SQLAlchemy 数据库连接和 Session 管理
│   ├── routers/
│   │   ├── auth_router.py              # 注册、登录接口
│   │   ├── chat_router.py              # 问答、流式问答、会话历史、历史删除接口
│   │   ├── contract_router.py          # 合同上传、合同列表、合同删除接口
│   │   └── health_router.py            # 服务健康检查接口
│   ├── security/
│   │   ├── dependencies.py             # 当前登录用户解析和接口鉴权依赖
│   │   ├── password.py                 # 密码哈希与校验
│   │   └── token.py                    # access token 生成与解析
│   └── services/
│       ├── auth_service.py             # 用户注册、登录业务逻辑
│       ├── upload_service.py           # 上传文件保存、文件名处理、大小统计
│       ├── document_loader.py          # PDF、DOCX、PPTX、TXT、MD 文档解析
│       ├── contract_splitter.py        # 合同条款规则切分、长文本 chunk 切分
│       ├── embedding_service.py        # 调用 Qwen / DashScope embedding 接口生成向量
│       ├── vector_store.py             # ChromaDB 写入、检索、删除和相似度分数计算
│       ├── retriever_service.py        # 面向问答流程的合同片段检索封装
│       ├── risk_analyzer.py            # 构造审查 prompt，生成风险分析回答
│       ├── qwen_client.py              # Qwen 聊天模型同步/流式调用封装
│       ├── memory_service.py           # 聊天会话、消息、引用来源的保存和读取
│       └── contract_service.py         # 合同上传后的解析、切分、入库和删除编排
├── frontend/
│   ├── src/
│   │   ├── App.vue                    # 主页面，包含登录、合同栏、聊天区、引用展示
│   │   ├── main.js                    # Vue 应用入口
│   │   ├── styles.css                 # 页面布局、聊天气泡、侧边栏和响应式样式
│   │   └── api/
│   │       └── client.js              # 前端 API 封装，含登录、上传、流式问答、删除操作
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
├── data/
│   ├── app.db                         # 本地 SQLite 数据库，GitHub 上传时忽略
│   ├── uploads/                       # 用户上传合同文件，GitHub 上传时忽略
│   └── vector_db/                     # ChromaDB 向量库，GitHub 上传时忽略
├── logs/                              # 本地运行日志，GitHub 上传时忽略
├── test_files/                        # 本地测试文件，GitHub 上传时忽略
├── .env.example                       # 环境变量模板，只保留占位符
├── .gitignore                         # Git 忽略规则
├── requirements.txt                   # 后端依赖
├── run_backend.ps1                    # Windows 后端启动脚本
└── run_frontend.ps1                   # Windows 前端启动脚本
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
