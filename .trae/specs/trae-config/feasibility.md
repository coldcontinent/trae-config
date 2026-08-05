# 可行性分析 —— trae-config 项目

> 项目:trae-config（TRAE 配置同步仓库）
> 阶段:立项(已有项目补建,简化版)
> 日期:2026-07-30

## 1. 项目背景

trae-config 是 TRAE IDE 的配置同步仓库,用于版本化管理:
- MCP 服务器脚本(cli-agent / mac-computer-use)
- MCP 工具描述(JSON)
- Claude Code CLI 配置(settings.json / .claude.json)
- Shell 环境变量(zshrc)
- 协作规程(TRAE 全局规则 v2.5 / CLAUDE.md v2.5)

## 2. 技术可行性

### 2.1 技术栈
- Python 3.10+(MCP 服务端脚本)
- Bash(安装脚本 / 启动脚本)
- JSON(MCP 工具描述 / 配置模板)
- Markdown(协作规程 / 项目文档)

### 2.2 依赖项
- `mcp` Python 包(Server, stdio_server, types)
- `Quartz` Python 包(mac-computer-use 截图/显示)
- Claude Code CLI(`claude` 命令,cli-agent 封装)
- Codex CLI(`codex` 命令,cli-agent 封装)

### 2.3 运行环境
- macOS(TRAE SOLO CN 内置 Python 3.10.20)
- TRAE SOLO CN 提供的沙箱环境
- 路径:`/Users/houtao/Library/Application Support/TRAE SOLO CN/ModularData/ai-agent/vm/tools/opt/python@3.10/3.10.20_3/libexec/bin/python3`

## 3. 资源可行性

| 资源 | 状态 | 说明 |
|------|------|------|
| 代码库 | 已有 | 2 个 MCP 服务端 + 20+ 工具定义 + 配置模板 |
| 协作规程 | 已补建 | v2.5(本次新增) |
| 项目文档 | 待补建 | 本文档套件 |
| 项目级规则 | 待补建 | project-rules.md / git-workflow-guidelines.md |

## 4. 风险评估

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| Python 路径硬编码 | 中 | run.sh 中需按实际安装位置调整 |
| 敏感信息泄露 | 高 | .gitignore 排除含密钥的文件,使用 .example 模板 |
| MCP 工具描述路径不一致 | 中 | install.sh 中工作区 ID 需按实际调整 |
| 规程版本不同步 | 中 | 两处配置(TRAE 全局/CLAUDE.md)版本号必须一致 |

## 5. 结论

项目已在运行中,技术成熟,无阻断风险。本次补建项目文档套件和项目级规则文件,使项目符合 v2.5 规程标准。
