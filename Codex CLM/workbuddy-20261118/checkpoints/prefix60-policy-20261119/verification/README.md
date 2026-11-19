# 阶段检查点发布与实际远端回读核验

本目录核验的是**目标尚未完成的当前全轨迹检查点**：120条已完成评分，1条服务端策略拒绝未评分，9槽位未启动；冻结目标65题/130条未改变，未提交完整65题完成审核。

- `VERIFIED.json`：H20归档CRC/SHA、原文件还原配方及私有GPT key扫描回执。
- `LOCAL_VERIFIED.json`：Mac从H20取得ZIP后的独立全校验。
- `GITHUB_BINARY_READBACK.json`：实际从固定GitHub提交下载393分卷、逐SHA、重组ZIP及全部CRC/SHA/还原配方核验。
- `GITHUB_READBACK_TRANSPORT.jsonl`：每次真实下载及失败记录；用量与模型API请求分开。
- `GITHUB_TREE_VERIFIED.json`、`GITHUB_BLOBS_VERIFIED.json`：实际Git SHA/模式/大小匹配，以及原CL-Bench与其他项目子树保持。
- `UPLOAD_REPL_RESET.json`、`TREE_CREATION_TIMEOUT.json`、`TREE_BUILD_LOG.jsonl`：上传工具临时状态丢失、GitHub大树请求超时及精确断点/分批恢复原证据。这些是发布管理故障，不是模型作答失败。
- `GITHUB_DELIVERY_VERIFIED.json`：上述阶段交付核验摘要。

实际远端回读固定到归档发布提交 `b8d71aee4f4dce07fc48c76fc3b4ef583a2d5017`，不是会变化的main。配套 `download_checkpoint_parts.py` 的参数依次为该提交SHA、检查点的archive/MANIFEST.json、一个新的下载目录、检查点source/benchmarks目录；它只下载公开分卷和核验文件，不运行归档内代码，不调用模型API。

原始模型/CLI轨迹在重建后的 `workbuddy-codex-20261118/` 中；本目录的核验侧文件生成于9:14快照之后，单独留存，不能据其存在把剩余题计作完成。
