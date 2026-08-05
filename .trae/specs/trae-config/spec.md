# 需求规格 —— trae-config 项目

> 项目:trae-config（TRAE 配置同步仓库）
> 阶段:落地
> 日期:2026-07-30

## 1. 功能需求

### FR-1:MCP 服务端(cli-agent)

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| FR-1.1 | 封装 Claude Code CLI 非交互调用 | `run_claude_code` 工具可接收 prompt/cwd/model 参数,返回 stdout/stderr/exit_code |
| FR-1.2 | 封装 Codex CLI 非交互调用 | `run_codex` 工具可接收 prompt/cwd/model 参数,返回 stdout/stderr/exit_code |
| FR-1.3 | CLI 状态检测 | `check_cli_status` 工具返回 claude/codex 的安装状态、路径、版本 |
| FR-1.4 | 超时控制 | 所有 CLI 调用支持 timeout 参数,默认 600 秒 |
| FR-1.5 | 错误处理 | CLI 未安装时返回明确错误信息;超时/异常返回结构化错误 |

### FR-2:MCP 服务端(mac-computer-use)

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| FR-2.1 | 屏幕截图 | 支持全屏/区域截图,返回 ImageContent |
| FR-2.2 | 鼠标控制 | 支持点击/拖拽/滚动/移动 |
| FR-2.3 | 键盘控制 | 支持按键/热键/中文输入(剪贴板方式) |
| FR-2.4 | UI 交互 | 支持列举 UI 元素、点击 UI 元素、选择菜单项 |
| FR-2.5 | 窗口管理 | 支持列举窗口、激活应用 |
| FR-2.6 | 剪贴板 | 支持读取/设置剪贴板内容 |

### FR-3:配置同步

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| FR-3.1 | 安装脚本 | `install.sh` 一键安装全部配置,5 步完成 |
| FR-3.2 | 配置模板 | settings.json/zshrc 提供 .example 脱敏模板 |
| FR-3.3 | 敏感信息保护 | 含密钥的文件被 .gitignore 排除 |
| FR-3.4 | CLAUDE.md 安装 | install.sh 自动安装到 ~/.claude/CLAUDE.md,含备份 |
| FR-3.5 | 规程版本同步 | rules/trae-global-rules.md 和 claude/CLAUDE.md 版本号一致 |

### FR-4:协作规程

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| FR-4.1 | 大脑侧规程 | rules/trae-global-rules.md 包含 v2.5 全部章节 |
| FR-4.2 | 手脚侧规程 | claude/CLAUDE.md 包含 v2.5 全部章节 |
| FR-4.3 | 项目级工作流 | 规程包含项目生命周期管理(立项→结项) |
| FR-4.4 | 五段闭环 | 规程包含规划→派发→执行→验收→复盘 |
| FR-4.5 | 4 种协作模式 | 规程包含模式 A/B/C/D 判定流程和差异表 |

## 2. 非功能需求

| 编号 | 需求 | 验收标准 |
|------|------|----------|
| NFR-1 | 可维护性 | 所有 Python 代码注释用中文,解释"为什么" |
| NFR-2 | 可移植性 | run.sh 中 Python 路径可按实际安装位置调整 |
| NFR-3 | 安全性 | API Key 不入库,使用 .example 模板 |
| NFR-4 | 可追溯性 | 每次规程变更更新头部版本号和变更说明 |
| NFR-5 | 文档完整性 | README 包含安装步骤、目录结构、规程说明 |

## 3. 验收标准汇总

详见 [checklist.md](./checklist.md)。
