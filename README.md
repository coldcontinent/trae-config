# TRAE 配置同步

本仓库用于同步 TRAE IDE 的 MCP 服务器脚本、工具定义、Claude Code CLI 配置、Shell 环境变量和**协作规程**。

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
│   ├── .claude.json.example  # MCP 服务器配置模板
│   └── CLAUDE.md            # 手脚侧全局行为准则 v2.5
├── rules/                    # TRAE 全局规则
│   └── trae-global-rules.md  # 大脑侧全局规则 v2.5（复制到 TRAE 设置中心）
├── shell/
│   └── zshrc.example         # Shell 环境变量模板（脱敏）
└── install.sh                # 安装脚本
```

## 协作规程（v2.5）

TRAE + Claude Code 采用"大脑-手脚"协作模式,规程分两处配置,**版本号必须一致**:

| 配置 | 文件 | 安装位置 | 说明 |
|------|------|----------|------|
| TRAE 全局规则（大脑） | `rules/trae-global-rules.md` | TRAE 设置中心 > 规则 > 全局规则 | 大脑行为准则:规划/决策/验收/复盘/汇报 |
| CLAUDE.md（手脚） | `claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | Claude Code 全局记忆:执行/返回/反推机制 |

### v2.5 核心特性

- **项目级工作流**:立项→可行性→方案→文档套件→落地→结项
- **项目管理文档套件**:存放在项目根目录 `.trae/specs/<项目名>/`
  - `feasibility.md` - 可行性分析
  - `solution.md` - 实现方案
  - `spec.md` - 需求规格
  - `tasks.md` - 任务分解
  - `checklist.md` - 验收清单
  - `dispatch-log.md` - 派发日志
- **任务级五段闭环**:规划→派发→执行→验收→复盘(嵌套在项目级"落地"阶段内)
- **4 种协作模式**:A-代码改动 / B-调研审阅 / C-规划设计 / D-审计回溯
- **3 级反推机制**:L1 标注疑点 / L2 阻断重规划 / L3 升级规程

### 版本同步规则

改内容必改头部版本号,两处配置版本号必须一致。更新规程时:

1. 修改 `rules/trae-global-rules.md`（大脑侧）
2. 同步修改 `claude/CLAUDE.md`（手脚侧）
3. 更新两处文件的头部版本号和变更说明
4. 提交 git 时在 commit message 中注明版本号

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

4. 手动配置 TRAE 全局规则：
   - 打开 TRAE 设置中心 > 规则 > 全局规则
   - 将 `rules/trae-global-rules.md` 的内容粘贴进去
   - 保存生效

## 包含的配置

| 组件 | 说明 |
|------|------|
| MCP cli-agent | 通过 Claude Code CLI / Codex CLI 执行编码任务 |
| MCP mac-computer-use | 控制 macOS 鼠标、键盘、截图等 |
| MCP integrated_browser | 浏览器自动化 |
| Claude Code CLI | 使用阿里云百炼 Token Plan（GLM-5.2）|
| KiCad CLI | 电路设计工具命令行 |
| TRAE 全局规则 | 大脑行为准则 v2.5(规划/派发/验收/复盘) |
| CLAUDE.md | 手脚行为准则 v2.5(执行/返回/反推) |

## 注意事项

- `shell/zshrc` 和 `claude/settings.json` 含敏感信息（API Key），已在 `.gitignore` 中排除
- 使用 `.example` 文件作为模板，填入自己的密钥后重命名
- MCP 脚本中的 Python 路径需要根据实际安装位置调整
- 协作规程文件（`rules/` 和 `claude/CLAUDE.md`）纳入版本控制,用于团队同步规程版本
