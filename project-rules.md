# 项目代码规范 —— trae-config

> 项目:trae-config（TRAE 配置同步仓库）
> 版本:v2.5 | 2026-07-30
> 与 TRAE 全局规则「项目特定填充指引」实例化对齐

---

## 1. 项目概述

trae-config 是 TRAE IDE 的配置同步仓库,包含:
- MCP 服务器脚本(Python)
- MCP 工具描述(JSON)
- Claude Code CLI 配置(Shell/JSON)
- 协作规程(Markdown)

## 2. 语言与编码规范

### 2.1 Python(server.py)

- **注释语言**:中文,解释"为什么"(业务/历史原因)而非"做什么"
- **文档字符串**:模块级/函数级 docstring 用中文
- **类型标注**:使用 Python 3.10+ 类型语法(`str | None` 而非 `Optional[str]`)
- **命名**:函数 `_lower_snake_case`,常量 `UPPER_SNAKE_CASE`,私有函数加 `_` 前缀
- **异常处理**:捕获具体异常,不裸 `except`;错误返回结构化 dict(`{"success": False, "error": ...}`)
- **结构**:按职责分块,用 `# ===` 分隔注释块
- **依赖**:`mcp` 包(Server/stdio_server/types),`Quartz`(仅 mac-computer-use)

### 2.2 Bash(install.sh / run.sh)

- **注释**:中文,`#` 注释
- **错误处理**:`set -e` 启用错误即停
- **变量**:`UPPER_SNAKE_CASE`,引号包裹路径
- **幂等性**:install.sh 检测文件是否存在,已存在则跳过

### 2.3 JSON(工具描述 / 配置模板)

- **编码**:UTF-8,`ensure_ascii=False`(中文不转义)
- **格式**:2 空格缩进
- **description 字段**:中文描述

### 2.4 Markdown(规程 / 文档)

- **语言**:中文
- **格式**:GitHub Flavored Markdown
- **表格**:用 Markdown 表格,不用 HTML

## 3. 全局规则占位符实例化

本项目的占位符实例化如下(v2.5 「项目特定填充指引」对齐):

| 占位符 | 含义 | 本项目实例化 |
|--------|------|--------------|
| `<PROJECT>_ENABLE_XXX` | 项目裁剪宏前缀 | **N/A**(本项目无 C 代码,无裁剪宏) |
| `<Project>_<Module>_` | 项目 API 前缀 | **N/A**(本项目无 C API) |
| `<Project>_Hal_t` | HAL 结构体后缀 | **N/A** |
| `<module>_enum` / `_t` | 枚举/结构体后缀 | **N/A** |
| 项目规则文件引用 | 命名/架构规范出处 | **本文件**(project-rules.md) |
| 测试断言机制 | TEST_ASSERT 或等价物 | **N/A**(本项目无测试框架;文档验收改为 checklist.md 逐项勾对) |
| audit 溯源表 | 项目历史审计编号注脚 | 见本文末尾「项目历史审计注脚」 |

> 本项目是配置同步仓库,无 C 代码,不涉及 #if 裁剪宏、HAL 结构体、TEST_ASSERT 机制。验收方式改为 checklist.md 逐项勾对。

## 4. 防御性编程

本项目 Python 代码遵循 ~/.claude/CLAUDE.md「防御性编程(权威源)」的对称条款:
- 函数入口校验参数,提前返回错误 dict
- 不返回未定义值,NULL 返回 `{"success": False, "error": ...}`
- 外部调用(CLI/subprocess)捕获超时和 FileNotFoundError

## 5. 模块裁剪

本项目无 C 代码,不涉及 #if 裁剪宏。Python 服务的启用/禁用由 TRAE MCP 配置控制(安装/卸载 JSON 工具描述文件)。

## 6. 文件组织

```
项目根/
├── mcp-servers/          # Python MCP 服务端
├── mcps/                 # JSON 工具描述
├── claude/               # Claude Code 配置 + CLAUDE.md
├── rules/                # TRAE 全局规则
├── shell/                # Shell 配置模板
├── .trae/                # 项目管理
│   ├── specs/trae-config/  # 文档套件
│   └── work/              # 派发日志
├── project-rules.md      # 本文件
├── git-workflow-guidelines.md
├── install.sh
├── README.md
└── .gitignore
```

## 7. 敏感信息管理

- 含密钥的文件(`shell/zshrc`、`claude/settings.json`、`claude/.claude.json`)被 .gitignore 排除
- 使用 `.example` 文件作为脱敏模板
- install.sh 不覆盖已存在的配置文件

---

## 项目历史审计注脚

> audit 溯源表(下沉到本文件末尾,见 v2.3 变更说明)

| 审计编号 | 日期 | 范围 | 发现 | 严重度 | 处置 |
|----------|------|------|------|--------|------|
| AUDIT-001 | 2026-07-30 | install.sh 备份逻辑 | mkdir 在 cp 之后,若 backups/ 不存在会失败 | 中等 | 已自修复(mkdir 提前到 cp 之前) |
| AUDIT-002 | 2026-07-30 | run.sh Python 路径 | 硬编码绝对路径,不可移植 | 轻微 | 记录,列入 M3 优化(T-TBD-002 参数化) |
