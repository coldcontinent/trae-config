# Git 规范 —— trae-config

> 项目:trae-config（TRAE 配置同步仓库）
> 版本:v2.5 | 2026-07-30
> 与 TRAE 全局规则「commit message 规程」互补:本节管"对不对",全局规则管"真不真"

---

## 1. 分支策略

| 分支 | 用途 | 命名 |
|------|------|------|
| `main` | 稳定发布分支 | 固定 |
| `dev` | 日常开发集成 | 固定 |
| 功能分支 | 新功能开发 | `feat/<简述>` |
| 修复分支 | Bug 修复 | `fix/<简述>` |
| 规程分支 | 协作规程更新 | `rules/v<版本号>` |

## 2. Commit Message 格式

### 2.1 格式

```
<type>(<scope>): <subject>

<body>
```

### 2.2 type 取值

| type | 含义 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 |
| `docs` | 文档变更 |
| `refactor` | 重构(不改功能) |
| `chore` | 构建/工具/配置 |
| `rules` | 协作规程变更 |

### 2.3 scope 取值

| scope | 含义 |
|-------|------|
| `cli-agent` | MCP cli-agent 服务 |
| `mac-computer-use` | MCP mac-computer-use 服务 |
| `mcp-tools` | MCP 工具描述(JSON) |
| `claude` | Claude Code 配置 |
| `rules` | 协作规程 |
| `install` | 安装脚本 |
| `shell` | Shell 配置 |

### 2.4 规程变更特殊约定

协作规程变更时,commit message 必须注明版本号:
```
rules: 更新协作规程至 v2.5,新增项目级工作流

- 新增 rules/trae-global-rules.md(大脑侧 v2.5)
- 新增 claude/CLAUDE.md(手脚侧 v2.5)
- 两处配置版本号一致:v2.5 | 2026-07-30
```

## 3. PR 流程

1. 从 `dev` 拉功能分支
2. 开发完成后提 PR 到 `dev`
3. PR 标题格式同 commit message 格式
4. PR 描述包含:改动范围、验收点、是否含敏感信息
5. 合并后删除功能分支
6. `dev` 定期合并到 `main`(发布节点)

## 4. 敏感信息防护

- 提交前检查:不提交含 API Key 的文件
- .gitignore 排除:`shell/zshrc`、`claude/settings.json`、`claude/.claude.json`
- 若误提交敏感信息:立即 `git rm --cached` 移除 + 修改密钥 + 强推(需用户确认)

## 5. 与全局规则 commit 规程的关系

| 维度 | 全局规则管 | 本规范管 |
|------|-----------|----------|
| commit message | 断言数与 diff 实证对应 | 格式/类型/scope |
| 撰写权 | 大脑撰写 | 角色不变 |
| 内容真实性 | 必须以 git diff 为依据 | 格式规范性 |
