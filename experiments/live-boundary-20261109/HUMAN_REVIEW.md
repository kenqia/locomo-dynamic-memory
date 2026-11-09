# 人工实体归属与语义核查表

状态：已收到用户提交的 18 对案例核查意见；保留争议与待裁定项，不等于全部通过。原始提交见 [核查原文](human-review-submitted.txt)，转录记录见 [human-review-record.json](human-review-record.json)，AI 后续核对见 [待裁定说明](HUMAN_REVIEW_FOLLOWUP.md)。

先只看本表原文及后续盲化 X/Y 输出，完成独立判断后再看 AI 审阅与 blind-key。若证据不足，填写“不确定”，不要按常识补全身份或事件。

复核人：莫远序　日期：2026-11-09（姓名与日期由用户明确提供）

对每案区分：谁说的、说的是谁、喜爱/愿望/计划/实际状态、事件是否同一件事、时间是否过度精确、引用是否真的支持答案。

机器可读填写表见 `human-review.csv`；核查时只看 [可读盲输出](HUMAN_OUTPUTS.md)；原始 `review-packets.json` 带有可能提示变体身份的查询控制元数据，请在独立填写后再看。填写时可以直接编辑 CSV，或在本文件逐案记录。

## 六个实体归属案例

### e00 — 目标 conv-42/D5:11

**D5:10 · Nate · 6:59 pm on 18 March, 2022**

> Pets definitely bring tons of joy. They are always there for us and they're so cute! Relaxing with them is a great way to chill.

**D5:11 · Joanna · 6:59 pm on 18 March, 2022**

> I wish I wasn't allergic! I would get two turtles today if I could! I found out recently I'm allergic to cockroaches as well, so who knows if I'll ever get a pet.

**D5:12 · Nate · 6:59 pm on 18 March, 2022**

> Sorry! Maybe there are other animals you could consider! In the meantime though, I'll be sure to send you pics of my turtles so you can still watch them grow without getting too close.

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

### e01 — 目标 conv-42/D5:12

**D5:11 · Joanna · 6:59 pm on 18 March, 2022**

> I wish I wasn't allergic! I would get two turtles today if I could! I found out recently I'm allergic to cockroaches as well, so who knows if I'll ever get a pet.

**D5:12 · Nate · 6:59 pm on 18 March, 2022**

> Sorry! Maybe there are other animals you could consider! In the meantime though, I'll be sure to send you pics of my turtles so you can still watch them grow without getting too close.

**D5:13 · Joanna · 6:59 pm on 18 March, 2022**

> Great idea! I'm already really invested in those little guys!

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

### e02 — 目标 conv-42/D8:14

**D8:13 · Nate · 6:44 pm on 17 April, 2022**

> Speaking of which, here they go again!

**D8:14 · Joanna · 6:44 pm on 17 April, 2022**

> So cute! I love your turtles so much!

**D8:15 · Nate · 6:44 pm on 17 April, 2022**

> Me too! I love watching them play to simply enjoy the peaceful moments of life. Sometimes I even bring them in the kitchen so they can watch me make food like this!

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

### e03 — 目标 conv-42/D20:2

**D20:1 · Nate · 6:03 pm on 5 September, 2022**

> Hey Joanna! Long time no talk. So much has happened. Look how cute they are! Hanging with them has been a big help, especially recently. Speaking of which, I just had a letdown in a video game tourney - I didn't do too great, even though I tried. It was a setback, but I'm trying to stay positive.

**D20:2 · Joanna · 6:03 pm on 5 September, 2022**

> Hey Nate! Cute turtles! Bummer about the setback. Any positive vibes comin' your way? I just revised on of my old recipes and made this!

**D20:3 · Nate · 6:03 pm on 5 September, 2022**

> Hey Joanna, yeah it's a bummer that I didn't do well. But it's all part of the learning curve, you know? Also that looks super good! Anyways, how are you holding up?

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

### e04 — 目标 conv-42/D24:3

**D24:2 · Joanna · 2:01 pm on 21 October, 2022**

> Hey Nate! I have been revising and perfecting the recipe I made for my family and it turned out really tasty. What's been happening with you?

**D24:3 · Nate · 2:01 pm on 21 October, 2022**

> Hey Joanna! That's cool. I've been getting so stressed lately because of my tournament progress - tough competitors - but my turtles always cheer me up.

**D24:4 · Joanna · 2:01 pm on 21 October, 2022**

> Pets have a way of brightening our days. I still have that stuffed animal dog you gave me! I named her Tilly, and she's always with me while I write.

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

### e05 — 目标 conv-42/D25:26

**D25:25 · Nate · 8:16 pm on 25 October, 2022**

> Yeah, they each do. One is more adventurous while the other is more reserved, which I find cute. Having them around brings me joy and they make great companions.

**D25:26 · Joanna · 8:16 pm on 25 October, 2022**

> That's super cool! I never knew turtles could be so interesting until I met your turtles. Wow!

**D25:27 · Nate · 8:16 pm on 25 October, 2022**

> I've always liked turtles since I was a boy, so I know all about them!

目标轮次中哪些事实可以确认？________

事实主体及逐字依据：________

哪些陈述只是喜爱、愿望或不确定信息？________

X 判断与理由：________　Y 判断与理由：________

引用 Source ID 与逐字引文：________

不同意见/待核对内容：________

## 问答盲核查

q00–q11 对应 [可读盲输出](HUMAN_OUTPUTS.md) 中同名 packet_id。逐题检查 X/Y 的答案、解释与原文。新旧臂身份不出现在盲包中；`blind-key.json` 仅在独立判断后用于揭盲。

缺失事实只针对已供给的对照原文集合判断，不能将未提供的完整对话视为已经查过。失败输出标记“未执行/失败”，不替模型补答案。

## 提交人工结论

本页下方保留原空白模板用于追溯；已提交判断以核查原文和 CSV 为准，不再要求重复填写。CSV 中未单列的维度保留空白，不能据此认为整案未核查。提交覆盖 18/18 对；不把有条件意见当作统一二元真值，不追认冻结 AI 审阅失败批次，也不更改原 QA 分数。提交过程独立性及是否使用辅助工具未另行核验。原生成结果中 pending_user 描述当时快照；当前状态以独立 human-review-record.json 为准。
