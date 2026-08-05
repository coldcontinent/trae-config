# 验收清单 —— trae-config 项目

> 项目:trae-config（TRAE 配置同步仓库）
> 阶段:落地
> 日期:2026-07-30
> 对照 spec.md 逐项验收

## M2:规程同步验收

### FR-4:协作规程

- [x] FR-4.1 `rules/trae-global-rules.md` 包含 v2.5 全部章节(角色定位/抗压缩/项目级工作流/五段闭环/4 种模式/派发协议/验收红线/反推机制/用户介入点/度量/自检)
- [x] FR-4.2 `claude/CLAUDE.md` 包含 v2.5 全部章节(项目级上下文感知/执行原则/返回规范/反推机制/抗压缩意识)
- [x] FR-4.3 规程包含项目生命周期管理(立项→可行性→方案→文档套件→落地→结项)
- [x] FR-4.4 规程包含五段闭环(规划→派发→执行→验收→复盘)
- [x] FR-4.5 规程包含 4 种协作模式(A/B/C/D)判定流程和差异表
- [x] FR-3.5 两处配置版本号一致(v2.5 | 2026-07-30)

### FR-3:配置同步

- [x] FR-3.1 `install.sh` 一键安装全部配置(5 步完成)
- [x] FR-3.2 settings.json/zshrc 提供 .example 脱敏模板
- [x] FR-3.3 含密钥的文件被 .gitignore 排除
- [x] FR-3.4 install.sh 自动安装 CLAUDE.md 到 ~/.claude/CLAUDE.md(含备份)
- [x] NFR-4 README 包含安装步骤、目录结构、规程说明

## M1:项目基础设施验收

### 文档套件完整性

- [x] `feasibility.md` 可行性分析(技术/资源/风险/依赖)
- [x] `solution.md` 实现方案(架构/模块划分/技术选型/接口约定)
- [x] `spec.md` 需求规格(功能/非功能需求)
- [x] `tasks.md` 任务分解(WBS,按里程碑拆解)
- [x] `checklist.md` 验收清单(对照 spec 逐项)
- [x] `dispatch-log.md` 派发日志骨架(5 段结构)

### 项目级规则文件

- [x] `project-rules.md` 项目代码规范(占位符实例化 + audit 注脚)
- [x] `git-workflow-guidelines.md` git 规范(分支策略/commit 格式/PR 流程)

## M3:后续优化验收(待规划)

- [ ] T-TBD-001 MCP 工具描述同步性校验
- [ ] T-TBD-002 install.sh 工作区 ID 参数化
- [ ] T-TBD-003 MCP 服务端错误处理加固
- [ ] T-TBD-004 规程版本自动校验脚本
