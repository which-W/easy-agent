# easy-agent

基于 AgentScope 的多模态 AI Agent 系统实践。

## 功能特性

- **流式传输**: 支持 SSE (Server-Sent Events) 实时流式输出
- **多模态输入**: 支持文本、图片、视频输入
- **多模态输出**: 支持文本、图片生成
- **Deep Research**: 深度研究模式，使用通义千问原生深度思考能力
- **MCP 工具集成**: 支持 Model Context Protocol (MCP) 工具，可连接外部工具服务
- **暗色系界面**: 类似 RAGflow 风格的现代化 UI

## 环境要求

- Python 3.10+
- 通义千问 API Key (DashScope)

## 快速开始

### 1. 创建 Python 虚拟环境

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/Mac:
```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置你的 DashScope API Key:

```env
DASHSCOPE_API_KEY=your_api_key_here
```

### 4. 启动后端服务

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。
API 文档: `http://localhost:8000/docs`

### 5. 打开前端页面

在浏览器中打开 `frontend/index.html`，或使用任意静态文件服务器。

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DASHSCOPE_API_KEY` | DashScope API Key (必填) | - |
| `CHAT_MODEL` | 文本对话模型 | `qwen-max` |
| `VISION_MODEL` | 多模态/深度研究模型 | `qwen-vl-max` |
| `ENABLE_DEEP_THINKING` | 启用深度思考 | `true` |
| `HOST` | 服务地址 | `0.0.0.0` |
| `PORT` | 服务端口 | `8000` |
| `MAX_UPLOAD_SIZE_MB` | 最大上传文件大小 (MB) | `50` |
| `MCP_CONFIG_PATH` | MCP 服务器配置文件路径 | `mcp_servers.json` |
| `MAX_AGENT_ITERATIONS` | Agent 最大迭代轮数 | `10` |
| `TEMPERATURE` | 模型温度参数 | `0.7` |
| `TOP_P` | 模型 top_p 参数 | `0.9` |

## API 文档

### 聊天接口

**POST** `/api/chat/stream`

流式聊天端点，支持 SSE 事件流。

请求体:
```json
{
  "session_id": "optional-session-id",
  "message": "你好",
  "files": [
    {
      "type": "image",
      "base64": "base64-encoded-content",
      "mime_type": "image/jpeg"
    }
  ],
  "deep_research": false
}
```

SSE 事件类型:
- `thinking`: 深度思考内容
- `text`: 文本输出
- `tool_use`: 工具调用
- `tool_result`: 工具结果
- `done`: 对话完成
- `error`: 错误信息

### 文件上传

**POST** `/api/upload`

上传文件或视频。

### 健康检查

- **GET** `/health` - 服务健康状态检查

## 项目结构

```
easy-agent/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── config.py           # 配置管理
│   ├── agent/              # Agent 系统
│   │   ├── factory.py      # Agent 工厂
│   │   ├── session.py      # 会话管理
│   │   └── mcp_manager.py  # MCP 工具管理器
│   ├── api/                # API 端点
│   │   ├── chat.py         # 聊天接口
│   │   └── upload.py       # 上传接口
│   └── models/             # 数据模型
│
├── frontend/               # 前端界面
│   ├── index.html          # 主页面
│   ├── css/
│   │   └── style.css       # 暗色主题样式
│   └── js/
│       ├── app.js          # 应用初始化
│       ├── chat.js         # 聊天控制
│       ├── sse.js          # SSE 客户端
│       └── upload.js       # 文件上传
│
├── skills/                 # AgentScope Skills (示例)
│   ├── code_executor/      # 代码执行技能
│   ├── file_ops/           # 文件操作技能
│   └── web_search/         # 网络搜索技能
├── mcp_servers.json        # MCP 服务器配置文件
└── .env                    # 环境变量配置文件
```

## MCP 工具配置

本项目支持通过 MCP (Model Context Protocol) 协议连接外部工具服务。

1. 编辑 `mcp_servers.json` 文件配置 MCP 服务器：

```json
{
  "mcpServers": {
    "server_name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-name"],
      "env": {
        "API_KEY": "your_api_key"
      }
    }
  }
}
```

2. 重启服务后，MCP 工具将自动加载并可供 Agent 使用

### 配置示例

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

## 常见问题

### 1. 如何获取 DashScope API Key?

访问 [DashScope 官网](https://dashscope.console.aliyun.com/) 注册并创建 API Key。

### 2. 支持哪些模型?

支持通义千问系列模型，包括:
- `qwen-max`: 文本对话
- `qwen-vl-max`: 多模态理解
- 其他 DashScope 提供的模型

### 3. 如何调试?

- 后端: 访问 `http://localhost:8000/docs` 查看 Swagger UI
- 前端: 打开浏览器开发者工具查看控制台日志

## License

Apache License 2.0
