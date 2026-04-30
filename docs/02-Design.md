# 项目设计文档（Design Document）

## 1. 设计目标
基于 `fastmcp` 打造一个**零侵入、自文档化**的 MCP CLI 代理，让任何 MCP 服务即刻获得完整的命令行交互界面和自动生成的参考手册。

## 2. 系统架构

```
+----------------+       +-------------------+       +------------------+
|   用户 / 脚本  | ----> |    mcp-cli 程序    | ----> |  MCP 服务器集群  |
+----------------+       +-------------------+       +------------------+
                               |
                               +--- 配置文件 (mcp.json)
                               +--- 输出 Markdown 指南
```

**内部模块划分**：

```
src/
  └── mcp_cli/
      ├── main.py               # 入口，参数解析总调度
      ├── config.py             # 配置文件读取与模型定义
      ├── client_factory.py     # 根据配置创建 fastmcp.Client
      ├── schema_to_argparse.py # JSON Schema → argparse 参数转换器
      ├── dynamic_parser.py     # 动态子命令构建器
      ├── guide_generator.py    # Markdown 指南生成器
      ├── output.py             # 输出格式化（JSON/表格/文本）
      └── exceptions.py         # 自定义异常
```

## 3. 主要功能模块设计

### 3.1 配置模块 (`config.py`)
**数据模型**：

```python
class ServerConfig(BaseModel):
    transport: Literal["stdio", "sse", "http"] = "stdio"
    command: Optional[str] = None       # stdio 模式必填
    args: List[str] = []                # stdio 附加参数
    env: Dict[str, str] = {}            # stdio 环境变量
    url: Optional[str] = None           # sse/http 模式必填
    headers: Dict[str, str] = {}        # sse/http 自定义头

class MCPConfig(BaseModel):
    mcpServers: Dict[str, ServerConfig]
```
**功能**：读取 JSON 文件，进行字段校验和填充默认值，提供 `get_server(name)` 方法。



**mcp.json配置实例：**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "transport": "stdio",
      "env": {
        "API_KEY": "sk-xxxx"
      }
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



### 3.2 客户端工厂 (`client_factory.py`)
根据 `ServerConfig` 生成 `fastmcp.Client` 实例：
- `stdio`：`Client(transport="stdio", command=[command]+args, env=env)`
- `sse`：`Client(transport="sse", url=url, headers=headers)` （如 fastmcp 版本不支持 headers，可暂忽略，记录警告）
- `http`：`Client(transport="http", url=url, headers=headers)` （如 fastmcp 版本不支持 headers，可暂忽略，记录警告）

处理异常：命令不存在、URL 不可达等，给出明确错误消息。

### 3.3 动态解析器 (`dynamic_parser.py`)
核心流程：
1. 在 `async with client` 上下文中调用 `tools = await client.list_tools()`。
2. 创建一个带有子命令的 `ArgumentParser`。
3. 遍历 `tools`：
   - `sub.add_parser(tool.name, help=tool.description)`
   - 调用 `schema_to_argparse.convert(tool_parser, tool.input_schema)`
4. 同时添加 `list` 和 `guide` 命令。
5. 解析剩余命令行参数。

**参数命名规范**：将 schema 中的属性名 `camelCase` 转为 `--kebab-case`，保留原始名称作为接收时的 key。

### 3.4 JSON Schema 到 argparse 转换 (`schema_to_argparse.py`)
**映射规则详述**：

| JSON Schema 特性 | argparse 实现 |
|-----------------|---------------|
| `type: "string"`                     | `add_argument(option, type=str)` |
| `type: "integer"`                    | `type=int` |
| `type: "number"`                     | `type=float` |
| `type: "boolean"`                    | `action='store_true'` 或 `'store_false'`，根据默认值 |
| `enum`                               | `choices=[...]` |
| `required` 列表                      | `required=True` |
| `default` 值                         | `default=...` |
| `description`                        | `help=description` |
| `type: "object"` 或 `"array"`        | 添加 `--param` 选项，接收 JSON 字符串，用 `json.loads` 解析。同时可选实现扁平化展开（递归深度限制为 2 层） |
| 简单类型数组 (`items: {type: str}`) | `nargs='*'` 或 `action='append'` |
| 组合（`anyOf`/`oneOf`）              | 暂不支持，退化为 JSON 字符串输入 |

**递归扁平化策略**（增强功能）：
对于 `object` 属性 `address` 有属性 `city`, `street`，生成 `--address-city` 和 `--address-street`。转换后的参数收集时再合并为嵌套字典。

### 3.5 指南生成器 (`guide_generator.py`)
**输入**：服务名称，`Tool` 对象列表。
**输出**：Markdown 字符串。

**模板结构**：
```markdown
# <server_name> MCP 服务命令指南

## 工具列表

### <tool_name>
**描述**：<description>

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| ... | ... | ... | ... | ... |

**使用示例**：
​```bash
mcp-cli --server <server_name> <tool_name> --param1 value1 --param2 value2
```

**文件输出**：默认写入 `./mcp-docs/<server_name>.md`，自动创建目录，支持 `--guide-dir` 修改。

`--all` 选项：遍历配置中所有服务，逐个连接生成文件并汇总报告。

### 3.6 输出模块 (`output.py`)
- JSON 模式：直接 `json.dumps(result, indent=2, ensure_ascii=False)`。
- 文本模式：对常见返回结构（如 `list[TextContent]`）进行友好格式化。
- 错误输出：写入 stderr，包含异常类型和消息。

## 4. 数据流与调用流程

1. **参数预解析**：提取 `--config`, `--server`, `--transport` 等顶层选项。
2. **加载配置**：确定服务器连接参数。
3. **能力获取**：异步连接，调用 `list_tools()`，若失败则报错退出。
4. **动态解析器构建**：注入子命令，重新解析完整命令行。
5. **动作执行**：
   - `list`：打印工具摘要。
   - `tool_name`：收集参数，调用 `call_tool`，格式化输出。
   - `guide`：生成 Markdown 文件。
6. **资源释放**：退出 `async with client` 上下文，自动关闭连接。

**时序图（工具调用示例）**：
```
用户 -> CLI: mcp-cli --server weather get_weather --city London
CLI -> Config: 读取 mcp.json, 获取 weather 配置
CLI -> fastmcp.Client: Client(transport="stdio", command=["python","weather_server.py"])
Client -> MCP Server: stdio 连接 & 握手
CLI -> Client: list_tools()
Client -> MCP Server: tools/list
MCP Server --> Client: [Tool(name="get_weather", inputSchema={...})]
CLI -> dynamic_parser: 注册 get_weather 子命令，参数 --city
CLI -> 解析: 得到 tool_name="get_weather", city="London"
CLI -> Client: call_tool("get_weather", {"city": "London"})
Client -> MCP Server: tools/call
MCP Server --> Client: [TextContent(text="...")]
CLI -> 输出: 打印结果
```

## 5. 异常处理与日志

- 配置文件不存在或格式错误 → 立即退出，提示正确格式。
- 服务名不存在 → 列出可用服务。
- 连接失败（如命令未找到、端口拒绝）→ 输出详细错误，退出码 1。
- 工具调用错误（如参数验证失败）→ 将服务端错误内容转为 stderr 输出，退出码 1。
- 网络超时 → 设置合理的超时（如 30s），可配置。

## 6. 部署与安装

**安装方式**：
```bash
pip install mcp-cli   # 或者从本地安装
```
**或使用虚拟环境**：推荐，与 `fastmcp` 共存。

**依赖项**：
- Python >= 3.10
- fastmcp（版本跟踪最新稳定版）
- 标准库：json, argparse, asyncio, pathlib, textwrap
- 虚拟环境管理，使用uv进行管理

**发布形式**：Python 包，可发布至 PyPI，同时提供单文件可执行版本（PyInstaller 可选）。

## 7. 测试策略

| 测试类型 | 内容 |
|----------|------|
| 单元测试 | 配置解析、schema→argparse 转换规则、指南生成模板 |
| 集成测试 | 使用模拟 MCP 服务（或 fastmcp 测试工具）验证 stdio 和 sse 模式完整流程 |
| 冒烟测试 | 给定标准 Claude Code 配置文件，运行 list/guide/tool 命令通过 |
| 文档验证 | 自动生成指南后，使用模式匹配校验表格格式和示例命令可执行性 |

## 8. 未来扩展

- **REPL 交互模式**：持续会话，可连续调用多个工具而无需重启连接。
- **输出插件**：支持 YAML、CSV 等格式。
- **配置发现**：支持从环境变量或中心注册表自动发现 MCP 服务。
- **参数环境变量注入**：允许敏感参数从 env 读取默认值。
- **Skill 模板生成器**：除 Markdown 外，直接生成 LangChain 或 Semantic Kernel 的技能定义。

---

**文档版本**：1.0  
**作者**：MCP-CLI 设计团队  
**日期**：2026-04-29