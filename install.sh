#!/bin/bash
# TRAE 配置安装脚本
# 将 MCP 服务脚本、工具定义、配置模板和协作规程安装到本地

set -e

TRAECN_DIR="$HOME/.trae-cn"
CLAUDE_DIR="$HOME/.claude"

echo "=== TRAE 配置安装 ==="

# 1. 安装 MCP 服务脚本
echo "[1/5] 安装 MCP 服务脚本..."
mkdir -p "$TRAECN_DIR/mcp-servers/cli-agent"
mkdir -p "$TRAECN_DIR/mcp-servers/mac-computer-use"
cp mcp-servers/cli-agent/run.sh "$TRAECN_DIR/mcp-servers/cli-agent/"
cp mcp-servers/cli-agent/server.py "$TRAECN_DIR/mcp-servers/cli-agent/"
cp mcp-servers/mac-computer-use/run.sh "$TRAECN_DIR/mcp-servers/mac-computer-use/"
cp mcp-servers/mac-computer-use/server.py "$TRAECN_DIR/mcp-servers/mac-computer-use/"
chmod +x "$TRAECN_DIR/mcp-servers/cli-agent/run.sh"
chmod +x "$TRAECN_DIR/mcp-servers/mac-computer-use/run.sh"
echo "  -> MCP 服务脚本已安装到 $TRAECN_DIR/mcp-servers/"

# 2. 安装 MCP 工具描述
echo "[2/5] 安装 MCP 工具描述..."
# 注意：工作区 ID 需要根据实际情况调整
WORKSPACE_DIR="$TRAECN_DIR/mcps/s_work_space-2a9e2d59/solo_work_lite"
mkdir -p "$WORKSPACE_DIR"
cp -r mcps/solo_work_lite/* "$WORKSPACE_DIR/"
echo "  -> MCP 工具描述已安装到 $WORKSPACE_DIR"

# 3. 安装 Claude Code 配置
echo "[3/5] 安装 Claude Code 配置..."
mkdir -p "$CLAUDE_DIR"
if [ ! -f "$CLAUDE_DIR/settings.json" ]; then
    cp claude/settings.json.example "$CLAUDE_DIR/settings.json"
    echo "  -> 已创建 $CLAUDE_DIR/settings.json（请编辑填入 API Key）"
else
    echo "  -> $CLAUDE_DIR/settings.json 已存在，跳过（如需覆盖请手动操作）"
fi

# 4. 安装 Shell 配置
echo "[4/5] 安装 Shell 配置..."
if [ ! -f "$HOME/.zshrc" ]; then
    cp shell/zshrc.example "$HOME/.zshrc"
    echo "  -> 已创建 ~/.zshrc（请编辑填入 API Key）"
else
    echo "  -> ~/.zshrc 已存在，跳过（如需参考请查看 shell/zshrc.example）"
fi

# 5. 安装协作规程（CLAUDE.md）
echo "[5/5] 安装协作规程..."
# 手脚侧：CLAUDE.md 安装到 ~/.claude/CLAUDE.md（已存在则备份后覆盖）
mkdir -p "$CLAUDE_DIR/backups"
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
    BACKUP_TIME=$(date +%s)
    cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/backups/CLAUDE.md.backup.$BACKUP_TIME"
    echo "  -> 已备份旧版 CLAUDE.md 到 $CLAUDE_DIR/backups/"
fi
cp claude/CLAUDE.md "$CLAUDE_DIR/CLAUDE.md"
echo "  -> CLAUDE.md 已安装到 $CLAUDE_DIR/CLAUDE.md（v2.5）"

echo ""
echo "=== 安装完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑 ~/.zshrc，填入你的 API Key"
echo "  2. 编辑 ~/.claude/settings.json，填入你的 ANTHROPIC_AUTH_TOKEN"
echo "  3. 调整 run.sh 中的 Python 路径（如需要）"
echo "  4. 运行 source ~/.zshrc 使环境变量生效"
echo "  5. 手动配置 TRAE 全局规则："
echo "     - 打开 TRAE 设置中心 > 规则 > 全局规则"
echo "     - 将 rules/trae-global-rules.md 的内容粘贴进去"
echo "     - 保存生效"
