# 公开代码与受控数据

上游LoCoMo仓库本地LICENSE标CC-BY-NC-4.0，来源commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`；本地provenance保存SHA。此事实不自动确认课程提交渠道、人物隐私或派生Memory的公开披露许可。

公开候选仅显式收集源码、锁、Schema/清单/哈希、合成fixture和经过扫描的研究汇总/附录。排除官方locomo10.json、私有Gold、完整Memory/Source/逐字审阅、raw wire/stdout/stderr、所有var、课程PDF和旧deliverables。既有Git历史包含官方数据，不能用本次diff无数据推导整条历史可新公开；远端发布单独待确认。

Synthetic fixture为项目原创Alex/Sam虚构对话，CC0-1.0，dataset与manifest均标识；MockTransport生成预录答案不接真实模型。Real Experimental Result只展示旧冻结聚合，明确producer和分母。

六份原JSON包含人物名、原文Source Turn、关系support_quote及模型断言，按受控数据处理。已复制到本机0700交付目录，文件0600，逐份SHA与原件相同。无QA Gold字段或凭据字段；不意味所有内容均可公开。归档含实验输出/身份/账本，保留原失败，不发公共Git。

公开清单`six-memory-exports-manifest.json`只含身份、数量、指纹、Embedding版本和哈希。`memory-export-schema.json`由Pydantic原契约生成。`validate-six-exports`和Web共享读取器；文件可解析/Schema/来源/时间/Projection/Index/SHA通过，不重写原数据。

仍待负责人确认课程许可、受控接收者/渠道和最终单包需求后再披露原JSON。若正式渠道不允许原文，只交Schema/哈希/合成演示并报告缺口。没有擅自上传或正式课程提交。

本机已生成`controlled-memory-delivery-v1.tar.gz`候选，包含六原JSON、Schema、清单、上游LICENSE和本说明；逐成员重新SHA验证，0600/父目录0700。体积及包SHA见experiments/personal-release/controlled-data-package.json。它未获披露授权，不在公开tar/Git内。

公开源码也按数据边界审核：tests/test_answer_regressions.py和tests/test_imports.py因含上游问题/短Source派生案例整模块排除；本地全仓保留。扫描包含Python原字节及官方问题/完整Source字面匹配，非作者另审AST/JSON解码字段。早期rehearsal包已废止，限制本机访问，从未发布。
