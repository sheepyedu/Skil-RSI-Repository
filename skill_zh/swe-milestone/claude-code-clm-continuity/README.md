# Claude Code CLM 工程连续性

要求另有明确可用的 CLM 兼容扩展；没有扩展时选原生版本。技能不能安装或启用扩展，也不声称复现论文中的上下文训练、缓存复用或性能结果。

## 适用场景与安装

用于同一代码库内需要连续完成的依赖型需求。每次只安装一种语言、一个运行时版本；对照实验不要同时载入两个版本。安装时把本目录原样复制到有权限使用的 Claude Code 技能位置，例如相关项目的 `.claude/skills/`。客户端支持显式调用时，可使用 `/claude-code-clm-continuity`。核对实际载入的正文，尤其注意无交互或受限配置。无需把本说明塞进模型提示，也无需增加权限。本包不包含脚本、钩子、服务地址或凭据。

- [Agent Skills 格式](https://agentskills.io/specification)
- [Claude Code 技能载入与生命周期](https://code.claude.com/docs/en/skills#skill-content-lifecycle)
- [SWE-Milestone：连续任务与隔离快照](https://arxiv.org/html/2603.13428v4#S4.SS1)
- [验证和审计说明](references/validation.md)
