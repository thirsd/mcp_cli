# MCP-CLI 测试操作指南

本文档介绍如何使用 `mcp_test` 测试服务验证 `mcp-cli` 的各项功能。

## 1. 前置条件

项目已通过 `uv sync` 安装依赖，目录结构如下：

```
mcp-cli/
├── mcp.json                    # MCP 服务配置文件
├── src/
│   ├── mcp_cli/                # CLI 工具源码
│   └── mcp_test/               # 测试 MCP 服务
│       ├── __init__.py
│       └── server.py           # HTTP 测试服务（天气查询 + 计算器）
└── docs/
```

## 2. 启动测试服务

在项目根目录打开终端，启动 `mcp_test` 服务：

```bash
uv run python src/mcp_test/server.py
```

服务启动后会在 `http://127.0.0.1:9000/mcp` 监听，终端显示如下信息表示启动成功：

```
FastMCP 3.x

  Server:      mcp-test-server

Starting MCP server 'mcp-test-server' with transport 'streamable-http'
  on http://127.0.0.1:9000/mcp
```

> 保持该终端运行，在另一个终端窗口执行后续测试命令。

## 3. 测试用例

以下所有命令在项目根目录执行。

### 3.1 查看版本

```bash
uv run mcp-cli --version
```

预期输出：

```
mcp-cli 0.1.0
```

### 3.2 列出所有已配置的服务

不指定 `--server` 时，列出配置文件中的所有服务：

```bash
uv run mcp-cli
```

预期输出：

```
Available MCP servers:

  filesystem           [stdio] npx -y @modelcontextprotocol/server-filesystem
  http-api             [http] http://localhost:8000/mcp
  mcp-test             [http] http://127.0.0.1:9000/mcp
  sse-api              [sse] http://localhost:8000/sse

Use --server <name> to select a server.
Example: mcp-cli --server <name> list
```

### 3.3 列出服务端工具

```bash
uv run mcp-cli --server mcp-test list
```

预期输出：

```
Available tools:

  get_weather           查询指定城市的天气信息。
  list_cities           列出所有支持查询天气的城市。
  add                   计算两个数的和。
  subtract              计算两个数的差。
  multiply              计算两个数的积。
  divide                计算两个数的商。
```

### 3.4 调用天气查询工具

查询指定城市天气：

```bash
uv run mcp-cli --server mcp-test get_weather --city 北京
```

预期输出：

```
北京天气：晴，气温 22°C，湿度 45%，北风 3级
```

查询不存在的城市：

```bash
uv run mcp-cli --server mcp-test get_weather --city 东京
```

预期输出：

```
未找到城市「东京」的天气数据。支持的城市：北京、上海、广州、...
```

列出所有支持的城市：

```bash
uv run mcp-cli --server mcp-test list_cities
```

### 3.5 调用计算器工具

加法：

```bash
uv run mcp-cli --server mcp-test add --a 10 --b 3.5
```

预期输出：

```
10.0 + 3.5 = 13.5
```

减法：

```bash
uv run mcp-cli --server mcp-test subtract --a 100 --b 37
```

预期输出：

```
100.0 - 37.0 = 63.0
```

乘法：

```bash
uv run mcp-cli --server mcp-test multiply --a 7 --b 8
```

预期输出：

```
7.0 × 8.0 = 56.0
```

除法：

```bash
uv run mcp-cli --server mcp-test divide --a 10 --b 3
```

预期输出：

```
10.0 ÷ 3.0 = 3.3333333333333335
```

除零测试：

```bash
uv run mcp-cli --server mcp-test divide --a 10 --b 0
```

预期输出：

```
错误：除数不能为 0
```

### 3.6 查看工具帮助

查看某个工具的参数说明：

```bash
uv run mcp-cli --server mcp-test get_weather --help
```

预期输出：

```
usage: mcp-cli --server mcp-test get_weather [-h] [--city CITY]

options:
  -h, --help   show this help message and exit
  --city CITY  城市名称，如：北京、上海、广州
```

### 3.7 生成 Markdown 使用指南

```bash
uv run mcp-cli --server mcp-test guide
```

预期输出：

```
Guide generated: mcp-docs\mcp-test.md
```

生成的文件位于 `mcp-docs/mcp-test.md`，包含所有工具的参数表格和使用示例。

### 3.8 JSON 格式输出

使用 `--json` 参数以 JSON 格式输出工具列表：

```bash
uv run mcp-cli --server mcp-test list --json
```

预期输出：

```json
[
  {"name": "get_weather", "description": "查询指定城市的天气信息。"},
  {"name": "list_cities", "description": "列出所有支持查询天气的城市。"},
  {"name": "add", "description": "计算两个数的和。"},
  {"name": "subtract", "description": "计算两个数的差。"},
  {"name": "multiply", "description": "计算两个数的积。"},
  {"name": "divide", "description": "计算两个数的商。"}
]
```

### 3.9 错误处理测试

指定不存在的服务名：

```bash
uv run mcp-cli --server nonexistent list
```

预期输出（stderr）：

```
Error: Server 'nonexistent' not found. Available servers: filesystem, http-api, mcp-test, sse-api
```

退出码为 1。

指定不存在的配置文件：

```bash
uv run mcp-cli --config not_found.json --server mcp-test list
```

预期输出（stderr）：

```
Error: Configuration file not found: not_found.json
```

### 3.10 自定义配置文件路径

使用 `-c` 指定其他配置文件：

```bash
uv run mcp-cli -c /path/to/custom.json --server my-service list
```

### 3.11 自定义连接超时

默认超时为 30 秒，可通过 `--timeout` 调整：

```bash
uv run mcp-cli --server mcp-test --timeout 10 list
```

## 4. 测试服务内置数据

### 天气数据

测试服务内置了以下城市的模拟天气数据：

| 城市 | 气温 | 湿度 | 天气 | 风力 |
|------|------|------|------|------|
| 北京 | 22°C | 45% | 晴 | 北风 3级 |
| 上海 | 26°C | 72% | 多云 | 东风 2级 |
| 广州 | 31°C | 85% | 雷阵雨 | 南风 2级 |
| 深圳 | 30°C | 80% | 阵雨 | 东南风 3级 |
| 成都 | 24°C | 65% | 阴 | 微风 |
| 杭州 | 25°C | 70% | 多云转晴 | 东风 2级 |
| 武汉 | 28°C | 60% | 晴 | 南风 3级 |
| 西安 | 20°C | 40% | 晴 | 西北风 2级 |
| 重庆 | 27°C | 75% | 多云 | 微风 |
| 南京 | 25°C | 68% | 晴转多云 | 东风 2级 |

### 计算器

支持两个 `float` 类型参数的四则运算，除法包含除零校验。

## 5. 清理

测试完成后，在运行服务的终端按 `Ctrl+C` 停止测试服务。生成的指南文件位于 `mcp-docs/` 目录，可手动删除。
