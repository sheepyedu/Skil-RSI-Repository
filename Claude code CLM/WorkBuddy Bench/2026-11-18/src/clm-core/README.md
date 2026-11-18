# WorkBuddy 运行时核心代码

本目录保存实验实际使用的 CLM 上下文管理、容器入口与 DeepSeek 协议适配器。Claude Code 可执行文件版本为 2.1.160，复现时通过上游渠道获取，并按 [SOURCES.json](../../data/SOURCES.json) 校验二进制。

`skillrl/vendor/a2o.py` 来自腾讯 WorkBuddy Bench 固定提交，字节与上游一致，SHA-256 为 `5f40081d4a6b6087af77697e8534067a1f31afbfb30ca32572740f99382e1fd6`。保留适用的腾讯授权条款。 [上游原件](https://github.com/Tencent/workbuddy-bench/blob/625b2233093ae4f23e76be28c1f341d41cc70373/src/workbuddy_bench/proxy/protocols/a2o.py) · [授权条款](../../data/TENCENT-LICENSE.txt)
