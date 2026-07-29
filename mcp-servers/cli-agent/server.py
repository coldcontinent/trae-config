#!/usr/bin/env python3
"""
CLI Agent MCP Server
- Wraps Claude Code CLI (claude -p) and OpenAI Codex CLI (codex exec) as MCP tools
- Runs them in non-interactive / headless mode
- Provides a status-check tool to detect installed CLIs and versions
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any

from mcp.server import Server, ServerRequestContext, NotificationOptions, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types


# ============================================================
# Helpers: CLI detection
# ============================================================

def _find_cli(name: str) -> str | None:
    """Find a CLI executable on PATH. Returns full path or None."""
    return shutil.which(name)


def _get_cli_version(name: str) -> str:
    """Get CLI version string. Returns version or empty string."""
    try:
        result = subprocess.run(
            [name, "--version"],
            capture_output=True, text=True, timeout=15
        )
        out = (result.stdout + result.stderr).strip()
        for line in out.splitlines():
            line = line.strip()
            if line:
                return line
        return out
    except Exception:
        return ""


def _detect_clis() -> dict:
    """Detect installed CLI agents and their versions."""
    clis = {}
    for name in ("claude", "codex"):
        path = _find_cli(name)
        if path:
            version = _get_cli_version(name)
            clis[name] = {"installed": True, "path": path, "version": version}
        else:
            clis[name] = {"installed": False, "path": None, "version": ""}
    return clis


# ============================================================
# Helpers: Run subprocess with timeout
# ============================================================

def _run_command(cmd: list[str], cwd: str | None, env: dict | None,
                 timeout: int) -> dict:
    """Run a command and capture output. Returns result dict."""
    start = time.time()
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd if cwd else None,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "elapsed_seconds": elapsed,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        elapsed = round(time.time() - start, 2)
        return {
            "success": False,
            "error": f"Command timed out after {timeout}s",
            "elapsed_seconds": elapsed,
            "command": " ".join(cmd),
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"Executable not found: {e}",
            "command": " ".join(cmd),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": " ".join(cmd),
        }


# ============================================================
# Tool: run_claude_code
# ============================================================

def _run_claude_code(args: dict) -> dict:
    """Run Claude Code CLI in headless (print) mode."""
    claude_path = _find_cli("claude")
    if not claude_path:
        return {
            "success": False,
            "error": "claude CLI not found on PATH. Install with: npm install -g @anthropic-ai/claude-code",
        }

    prompt = args.get("prompt", "").strip()
    if not prompt:
        return {"success": False, "error": "prompt is required"}

    timeout = int(args.get("timeout", 600))
    cwd = args.get("cwd") or None
    model = args.get("model")
    max_turns = args.get("max_turns")
    output_format = args.get("output_format", "text")
    system_prompt = args.get("system_prompt")
    allowed_tools = args.get("allowed_tools")
    add_dirs = args.get("add_dirs")
    verbose = args.get("verbose", False)
    extra_args = args.get("extra_args", [])

    cmd = [claude_path, "-p", prompt]

    if model:
        cmd.extend(["--model", model])
    if max_turns is not None:
        cmd.extend(["--max-turns", str(int(max_turns))])
    if output_format and output_format != "text":
        cmd.extend(["--output-format", output_format])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])
    if add_dirs:
        for d in add_dirs.split(","):
            d = d.strip()
            if d:
                cmd.extend(["--add-dir", d])
    if verbose:
        cmd.append("--verbose")
    if extra_args:
        cmd.extend(extra_args)

    return _run_command(cmd, cwd, None, timeout)


# ============================================================
# Tool: run_codex
# ============================================================

def _run_codex(args: dict) -> dict:
    """Run Codex CLI in non-interactive (exec) mode."""
    codex_path = _find_cli("codex")
    if not codex_path:
        return {
            "success": False,
            "error": "codex CLI not found on PATH. Install with: npm install -g @openai/codex",
        }

    prompt = args.get("prompt", "").strip()
    if not prompt:
        return {"success": False, "error": "prompt is required"}

    timeout = int(args.get("timeout", 600))
    cwd = args.get("cwd") or None
    model = args.get("model")
    full_auto = args.get("full_auto", False)
    json_output = args.get("json_output", False)
    sandbox = args.get("sandbox")
    approval_policy = args.get("approval_policy")
    base_instructions = args.get("base_instructions")
    image = args.get("image")
    extra_args = args.get("extra_args", [])

    cmd = [codex_path, "exec", prompt]

    if model:
        cmd.extend(["--model", model])
    if full_auto:
        cmd.append("--full-auto")
    if json_output:
        cmd.append("--json")
    if sandbox:
        cmd.extend(["--sandbox", sandbox])
    if approval_policy:
        cmd.extend(["--approval-policy", approval_policy])
    if base_instructions:
        cmd.extend(["--base-instructions", base_instructions])
    if image:
        for img in image.split(","):
            img = img.strip()
            if img:
                cmd.extend(["--image", img])
    if extra_args:
        cmd.extend(extra_args)

    return _run_command(cmd, cwd, None, timeout)


# ============================================================
# Tool: check_cli_status
# ============================================================

def _check_cli_status(args: dict) -> dict:
    """Detect installed CLI agents and their versions."""
    result = _detect_clis()
    result["success"] = True
    return result


# ============================================================
# Tool dispatch
# ============================================================

_TOOL_HANDLERS = {
    "run_claude_code": _run_claude_code,
    "run_codex": _run_codex,
    "check_cli_status": _check_cli_status,
}


# ============================================================
# Tool definitions
# ============================================================

TOOL_DEFS = [
    types.Tool(
        name="run_claude_code",
        description=(
            "在非交互（headless）模式下运行 Claude Code CLI，将一个编码任务交给 Claude Code 执行并返回结果。"
            "适用于代码生成、重构、调试、审查等场景。"
            "需要已安装 claude CLI（npm install -g @anthropic-ai/claude-code）。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "要执行的任务/提示词（必填）",
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（可选）。Claude Code 将在此目录下操作文件",
                },
                "model": {
                    "type": "string",
                    "description": "使用的模型（可选），如 sonnet、opus",
                },
                "max_turns": {
                    "type": "integer",
                    "description": "最大 agentic 轮次（可选）",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["text", "json", "stream-json"],
                    "description": "输出格式，默认 text",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "自定义系统提示词（可选）",
                },
                "allowed_tools": {
                    "type": "string",
                    "description": "允许的工具列表，逗号分隔（可选），如 'Read,Write,Bash'",
                },
                "add_dirs": {
                    "type": "string",
                    "description": "额外可读目录，逗号分隔（可选）",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "是否输出详细日志，默认 false",
                },
                "extra_args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "传递给 claude 的额外命令行参数（高级用法）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 600",
                },
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="run_codex",
        description=(
            "在非交互（exec）模式下运行 OpenAI Codex CLI，将一个编码任务交给 Codex 执行并返回结果。"
            "适用于代码生成、重构、调试等场景。"
            "需要已安装 codex CLI（npm install -g @openai/codex）。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "要执行的任务/提示词（必填）",
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（可选）",
                },
                "model": {
                    "type": "string",
                    "description": "使用的模型（可选），如 o3、o4-mini",
                },
                "full_auto": {
                    "type": "boolean",
                    "description": "是否自动批准所有操作（全自动模式），默认 false",
                },
                "json_output": {
                    "type": "boolean",
                    "description": "是否以 JSON 格式输出，默认 false",
                },
                "sandbox": {
                    "type": "string",
                    "enum": ["read-only", "workspace-write", "danger-full-access"],
                    "description": "沙箱模式（可选）",
                },
                "approval_policy": {
                    "type": "string",
                    "enum": ["untrusted", "on-failure", "on-request", "never"],
                    "description": "审批策略（可选）",
                },
                "base_instructions": {
                    "type": "string",
                    "description": "基础指令，替代默认指令（可选）",
                },
                "image": {
                    "type": "string",
                    "description": "附加图片路径，逗号分隔（可选）",
                },
                "extra_args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "传递给 codex 的额外命令行参数（高级用法）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 600",
                },
            },
            "required": ["prompt"],
        },
    ),
    types.Tool(
        name="check_cli_status",
        description=(
            "检测本地已安装的 CLI 编码代理（claude、codex）及其版本。"
            "在调用 run_claude_code 或 run_codex 之前，可先用此工具确认 CLI 是否可用。"
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


# ============================================================
# MCP Server handlers
# ============================================================

async def _on_list_tools(
    ctx: ServerRequestContext, params: types.PaginatedRequestParams | None
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOL_DEFS)


async def _on_call_tool(
    ctx: ServerRequestContext, params: types.CallToolRequestParams
) -> types.CallToolResult:
    name = params.name
    arguments = params.arguments or {}

    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(
                {"success": False, "error": f"Unknown tool: {name}"}, ensure_ascii=False
            ))],
            is_error=True,
        )

    try:
        result = handler(arguments)
        is_error = not result.get("success", False)
        return types.CallToolResult(
            content=[types.TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )],
            is_error=is_error,
        )
    except Exception as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(
                {"success": False, "error": str(e)}, ensure_ascii=False
            ))],
            is_error=True,
        )


# ============================================================
# Server entry point
# ============================================================

app = Server(
    "cli-agent",
    version="1.0.0",
    description="CLI Agent MCP - 封装 Claude Code CLI 和 Codex CLI 的非交互调用",
    on_list_tools=_on_list_tools,
    on_call_tool=_on_call_tool,
)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    import signal

    def _handle_sigterm(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        with open("/tmp/mcp_cli_agent_error.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} FATAL: {e}\n")
        sys.exit(1)
