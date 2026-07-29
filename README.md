# TRAE 配置同步

本仓库用于同步 TRAE IDE 的 MCP 服务器脚本、工具定义、Claude Code CLI 配置和 Shell 环境变量。

## 目录结构

```
trae-config/
├── mcp-servers/              # MCP 服务端脚本
│   ├── cli-agent/            # Claude Code / Codex CLI 代理
│   │   ├── run.sh            # 启动脚本
│   │   └── server.py         # MCP 服务端
│   └── mac-computer-use/     # macOS 电脑控制
│       ├── run.sh
│       └── server.py
├── mcps/                     # MCP 工具描述（JSON）
│   └── solo_work_lite/
│       ├── integrated_browser/
│       ├── mcp_cli-agent/
│       └── mcp_mac-computer-use/
├── claude/                   # Claude Code CLI 配置
│   ├── settings.json.example # 配置模板（脱敏）
│   └── .claude.json.example  # MCP 服务器配置模板
├── shell/
│   └── zshrc.example         # Shell 环境变量模板（脱敏）
└── install.sh                # 安装脚本
```

## 快速安装

1. 克隆仓库：
```bash
git clone git@github.com:coldcontinent/trae-config.git ~/trae-config
cd ~/trae-config
```

2. 运行安装脚本：
```bash
./install.sh
```

3. 根据模板填写真实密钥：
```bash
cp shell/zshrc.example ~/.zshrc
cp claude/settings.json.example ~/.claude/settings.json
# 编辑文件，填入你的 API Key
```

## 包含的配置

| 组件 | 说明 |
|------|------|
| MCP cli-agent | 通过 Claude Code CLI / Codex CLI 执行编码任务 |
| MCP mac-computer-use | 控制 macOS 鼠标、键盘、截图等 |
| MCP integrated_browser | 浏览器自动化 |
| Claude Code CLI | 使用阿里云百炼 Token Plan（GLM-5.2）|
| KiCad CLI | 电路设计工具命令行 |

## 注意事项

- `shell/zshrc` 和 `claude/settings.json` 含敏感信息（API Key），已在 `.gitignore` 中排除
- 使用 `.example` 文件作为模板，填入自己的密钥后重命名
- MCP 脚本中的 Python 路径需要根据实际安装位置调整
