# MCP-CLI

通用的 MCP（Model Context Protocol）服务 CLI 代理工具。提供统一的命令行接口，用于发现、调用和文档化任意 MCP 服务端工具。

## 特性

- **统一 CLI** - 通过单一命令行工具与任意 MCP 服务交互
- **多传输支持** - 支持 `stdio`、`sse`、`http` 三种传输模式
- **动态工具发现** - 自动获取服务端工具并暴露为 CLI 子命令
- **自动参数解析** - 将 JSON Schema 转换为 CLI 参数，支持类型检查、枚举和默认值
- **Markdown 指南生成** - 自动生成结构化工具文档，供 AI Skill 上下文引用
- **Claude Code 兼容** - 100% 兼容 Claude Code 现有 MCP 服务配置格式

## 环境要求

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)（推荐的包管理器）

## 安装

克隆仓库并使用 uv 安装：

```bash
git clone <repo-url>
cd mcp-cli
uv sync
```

## 快速上手

### 1. 创建配置文件

在项目根目录创建 `mcp.json`（兼容 Claude Code 格式）：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "transport": "stdio",
      "env": {}
    },
    "sse-api": {
      "transport": "sse",
      "url": "http://localhost:8000/sse",
      "headers": {
        "Authorization": "Bearer token"
      }
    },
    "http-api": {
      "transport": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

### 2. 列出可用服务

```bash
uv run mcp-cli
```

输出：

```
Available MCP servers:

  filesystem           [stdio] npx -y @modelcontextprotocol/server-filesystem
  http-api             [http] http://localhost:8000/mcp
  sse-api              [sse] http://localhost:8000/sse

Use --server <name> to select a server.
```

### 3. 列出服务端工具

```bash
uv run mcp-cli --server filesystem list
```

### 4. 调用工具

```bash
uv run mcp-cli --server filesystem read_file --path /tmp/hello.txt
```

### 5. 生成 Markdown 使用指南

```bash
uv run mcp-cli --server filesystem guide
# 输出：Guide generated: ./mcp-docs/filesystem.md
```

## 使用说明

```
usage: mcp-cli [-h] [--version] [--config CONFIG] [--server SERVER] [--timeout TIMEOUT]

MCP-CLI: 通用的 MCP 服务 CLI 代理工具。

选项：
  -h, --help                显示帮助信息并退出
  --version                 显示版本号
  --config, -c CONFIG       配置文件路径（默认：mcp.json）
  --server, -s SERVER       配置中的 MCP 服务名
  --timeout, -t TIMEOUT     连接超时秒数（默认：30）
```

通过 `--server` 选择服务后，可使用以下子命令：

| 命令 | 说明 |
|------|------|
| `list` | 列出服务端所有工具 |
| `guide` | 生成 Markdown 使用指南 |
| `<工具名>` | 调用指定工具并传入参数 |

工具参数根据服务端的 JSON Schema 自动生成。运行 `mcp-cli --server <名称> <工具名> --help` 可查看该工具支持的参数。

## 配置说明

### 配置文件搜索顺序

1. 通过 `--config` / `-c` 显式指定路径
2. `MCP_CLI_CONFIG` 环境变量
3. 当前目录下的 `mcp.json`
4. 当前目录下的 `mcp_config.json`

### 服务配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `transport` | `"stdio"` / `"sse"` / `"http"` | 否（默认：`stdio`） | 传输协议类型 |
| `command` | string | stdio 模式必填 | stdio 模式的可执行命令 |
| `args` | string[] | 否 | 命令附加参数 |
| `env` | object | 否 | 子进程环境变量 |
| `url` | string | sse/http 模式必填 | 服务端 URL |
| `headers` | object | 否 | 自定义 HTTP 请求头（sse/http） |

## 项目结构

```
src/mcp_cli/
  __init__.py               # 包入口
  main.py                   # CLI 入口与总调度
  config.py                 # 配置文件读取与模型定义
  client_factory.py         # 根据 ServerConfig 创建 fastmcp.Client
  schema_to_argparse.py     # JSON Schema 转 argparse 参数
  dynamic_parser.py         # 动态子命令构建器
  guide_generator.py        # Markdown 指南生成器
  output.py                 # 输出格式化（JSON/文本）
  exceptions.py             # 自定义异常
```

## 许可证

MIT
