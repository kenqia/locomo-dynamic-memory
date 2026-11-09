# 用户提交核查后的核对说明

2026-11-09。复核人：莫远序（用户明确提供）。已收到六个实体案例和十二个问答案例，共18/18对的文字核查。原始意见保存在 [提交文本](human-review-submitted.txt)，逐案转录见 [记录](human-review-record.json) 和 [CSV](human-review.csv)。以下是作者 AI 对原文和现有契约的后续核对，未改写复核人的判断。

## 保留的待裁定项

- **q02，报告与事件日期**：复核人认为 Y 更准确，并建议把 Memory 锚定 August 11。D6:3 原文却是 “I was in Chicago”，August 11 是报告日期；能够记录 report time，但不能据此确定事件在当天发生。原意见保留，时间精度继续标为有分歧。
- **q08，两臂人物归属**：复核人指出 X 将 Toby 当作女友；核对发现 Y 的 explanation 同样写了 “his girlfriend Toby”。Y 的拒答在计划/完成及目的地上更谨慎，仍不能视为没有人物错误。原盲包只给 D14:1；额外读取公开对话 conv-44/D12:1 得到 “meet Toby, my puppy”，支持 Toby 为幼犬。这是提交后的补充来源，不回填为原两臂已送达证据，也不假定复核人当时看过该轮。
- **q06/q11，星期边界**：October 28, 2023 本身为周六，严格之后为 November 4；July 24, 2023 本身为周一，严格之前为 July 17。原问题字面、原文与参考答案之间的时间一致性仍待裁定，不能只看 Gold 短答认定正确。
- **e00/e02/e05，陈述类型**：复核人提出 attitude/experience 等类型建议。当前 `MemoryDraft.statement_type` 只允许 fact/plan/intention/uncertain；ADR 0001 将 fact 定义为原文断言，并不表示外部客观真值。因此“自述喜爱被标 fact”不能直接算 schema 错误；主观状态的抽取口径、维度和否定作用域仍需统一。e00 已用 intention 和 counterfactual basis 区别于实际获得乌龟；event/date 字段如何表示反事实意图仍有语义风险，不将日期字段直接解读为实际事件完成。
- **e02/e05，引用充分性**：保留“your turtles”需要邻轮识别 Nate、实际 Memory 却只引目标轮的问题。新增内容是否算有用恢复取决于抽取口径，不能单按非空数量判收益。
- **q05 Y / q10 Y，执行失败**：与冻结包逐项一致，均保留 failed，不代模型补答案。

## 接收范围与验证

姓名、日期及判断来自用户提交；AI仅转录。未单列的人物/时间/遗漏维度没有自行补票，没有代写签名；独立性及是否使用辅助工具未另行核验。对有条件判断不生成统一正确率，不据此证明候选整体改善。

附带文本仅将 CRLF 换为 LF，正文逐字保留，原附件与归档文件分别记录 SHA。18 个 packet_id、X/Y映射、提交中的Source编号与盲包对应；q05/q10失败身份一致。旧 generation/review freeze、AI标签、分数和用量保持不变，新增模型调用为0。

本次只更新核查记录与文档，未改生产代码；未重跑离线代码测试或付费模型。此前1024通过、1跳过是 f18d76d 之前的代码验证。当前核查文件及PDF的SHA另见 [human-review-provenance.json](human-review-provenance.json)；此前 provenance.json 属于 f18d76d 提交快照，不冒称仍描述修改后的文件。
