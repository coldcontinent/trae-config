#!/bin/bash
# TRAE 配置安装脚本
# 将 MCP 服务脚本、工具定义和配置模板安装到本地

set -e

TRAECN_DIR="$HOME/.trae-cn"
CLAUDE_DIR="$HOME/.claude"

echo "=== TRAE 配置安装 ==="

# 1. 安装 MCP 服务脚本
echo "[1/4] 安装 MCP 服务脚本..."
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
echo "[2/4] 安装 MCP 工具描述..."
# 注意：工作区 ID 需要根据实际情况调整
WORKSPACE_DIR="$TRAECN_DIR/mcps/s_work_space-2a9e2d59/solo_work_lite"
mkdir -p "$WORKSPACE_DIR"
cp -r mcps/solo_work_lite/* "$WORKSPACE_DIR/"
echo "  -> MCP 工具描述已安装到 $WORKSPACE_DIR"

# 3. 安装 Claude Code 配置
echo "[3/4] 安装 Claude Code 配置..."
mkdir -p "$CLAUDE_DIR"
if [ ! -f "$CLAUDE_DIR/settings.json" ]; then
    cp claude/settings.json.example "$CLAUDE_DIR/settings.json"
    echo "  -> 已创建 $CLAUDE_DIR/settings.json（请编辑填入 API Key）"
else
    echo "  -> $CLAUDE_DIR/settings.json 已存在，跳过（如需覆盖请手动操作）"
fi

# 4. 安装 Shell 配置
echo "[4/4] 安装 Shell 配置..."
if [ ! -f "$HOME/.zshrc" ]; then
    cp shell/zshrc.example "$HOME/.zshrc"
    echo "  -> 已创建 ~/.zshrc（请编辑填入 API Key）"
else
    echo "  -> ~/.zshrc 已存在，跳过（如需参考请查看 shell/zshrc.example）"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑 ~/.zshrc，填入你的 API Key"
echo "  2. 编辑 ~/.claude/settings.json，填入你的 ANTHROPIC_AUTH_TOKEN"
echo "  3. 调整 run.sh 中的 Python 路径（如需要）"
echo "  4. 运行 source ~/.zshrc 使环境变量生效"
