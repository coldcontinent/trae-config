# 实现方案 —— trae-config 项目

> 项目:trae-config（TRAE 配置同步仓库）
> 阶段:方案(已有项目架构描述)
> 日期:2026-07-30

## 1. 架构概览

trae-config 是一个配置同步仓库,不含运行时业务逻辑。架构分为三层:

```
配置源(本仓库)
  ├── MCP 服务层(Python 脚本) → 被 TRAE SOLO CN 沙箱调用
  ├── 工具描述层(JSON) → 被 TRAE MCP 文件系统加载
  └── 配置模板层(Shell/JSON) → 被 Claude Code CLI 加载
```

## 2. 模块划分

### 2.1 MCP 服务端模块

| 服务 | 文件 | 职责 |
|------|------|------|
| cli-agent | `mcp-servers/cli-agent/server.py` | 封装 Claude Code CLI 和 Codex CLI 的非交互调用 |
| mac-computer-use | `mcp-servers/mac-computer-use/server.py` | macOS 屏幕截图、鼠标键盘控制、UI 交互 |

### 2.2 工具描述模块

存放在 `mcps/solo_work_lite/` 下,按 MCP 服务器组织:

| 目录 | 工具数 | 说明 |
|------|--------|------|
| `integrated_browser/` | 20 | 浏览器自动化(导航/点击/输入/截图等) |
| `mcp_cli-agent/` | 3 | CLI 代理(run_claude_code / run_codex / check_cli_status) |
| `mcp_mac-computer-use/` | 20 | macOS 控制(鼠标/键盘/截图/UI 元素等) |

### 2.3 配置模板模块

| 文件 | 安装目标 | 说明 |
|------|----------|------|
| `claude/settings.json.example` | `~/.claude/settings.json` | Claude Code CLI 配置(API Key / Model / PATH) |
| `claude/.claude.json.example` | `~/.claude/.claude.json` | MCP 服务器配置 |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | 手脚侧全局行为准则 v2.5 |
| `shell/zshrc.example` | `~/.zshrc` | Shell 环境变量 |

### 2.4 规程同步模块

| 文件 | 安装目标 | 说明 |
|------|----------|------|
| `rules/trae-global-rules.md` | TRAE 设置中心 > 全局规则 | 大脑侧全局规则 v2.5 |
| `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | 手脚侧全局行为准则 v2.5 |

## 3. 技术选型

| 维度 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10 | TRAE SOLO CN 内置,兼容 MCP SDK |
| MCP SDK | `mcp` 包 | 官方 Python SDK,支持 stdio 传输 |
| 截图方案 | Quartz CGDisplayCreateImage | 原生 API,无依赖,高质量 |
| 中文输入 | 剪贴板粘贴 | 绕过 AppleScript Unicode 编码问题 |
| 鼠标操作 | CGEvent(独立子进程) | 主进程不加载 CGEvent,避免崩溃 |
| 配置管理 | .example 模板 + .gitignore | 敏感信息不入库 |

## 4. 接口约定

### 4.1 MCP 工具调用约定

所有 MCP 工具遵循统一返回格式:
```json
{
  "success": true/false,
  "error": "错误信息(失败时)",
  ...其他字段
}
```

### 4.2 CLI 代理调用约定

cli-agent 封装的 CLI 调用返回:
```json
{
  "success": true/false,
  "exit_code": 0,
  "stdout": "标准输出",
  "stderr": "标准错误",
  "elapsed_seconds": 1.23,
  "command": "claude -p ..."
}
```

## 5. 安装流程

`install.sh` 执行 5 步:
1. 安装 MCP 服务脚本到 `~/.trae-cn/mcp-servers/`
2. 安装 MCP 工具描述到 `~/.trae-cn/mcps/<workspace>/solo_work_lite/`
3. 安装 Claude Code 配置到 `~/.claude/`(含 CLAUDE.md 备份)
4. 安装 Shell 配置到 `~/.zshrc`
5. 提示手动配置 TRAE 全局规则

## 6. 安全边界

- `.gitignore` 排除:含密钥的文件(zshrc / settings.json / .claude.json)
- `.example` 文件:脱敏模板,用户复制后填入密钥
- MCP 脚本:只操作 cwd 内文件,不越界访问
- cli-agent:封装的 CLI 在沙箱内执行,超时可控
