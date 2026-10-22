# 查询可靠性真实复验

使用既有评测 API 的类别 F1；失败记 0，未完成不算成功。固定开发题单轮复验，不能作为统计显著性或隐藏测试成绩。
逐题语义由作者核对原文并另记结论，不增加独立 LLM 评估器。历史对照不是同时运行的随机对照。

状态 `completed_with_errors`，本轮调用 23/32。

| 组 | 成功 / 计划 | 失败项 | 成功可回答题 F1 | 全部可回答题 F1（失败记0） | 同题前后比较（失败记0） |
| --- | --- | --- | --- | --- | --- |
| primary | 5/6 | 1 | 0.783073593073593 | 0.6525613275613276 | 6题：0.2878793219567029 → 0.6525613275613276 |
| dynamic_nonregression | 1/1 | 0 | 1.0 | 1.0 | 1题：0 → 1.0 |

## QA 15 · dynamic_raw_fallback

What activities does Melanie partake in?

状态 succeeded / sufficient，F1 0.75。

Running, reading, playing violin, pottery, painting, hiking, exploring forests, camping, roasting marshmallows, telling stories around the campfire, and enjoying family company.

解释：Me-time activities (running, reading, violin) are from May 2023; pottery from July 2023; painting 'lately' as of July 2023; hiking/forest exploring and camping activities are family activities. Camping items (roasting marshmallows, campfire stories, enjoying company) are drawn from both the completed June trip and the July general statement.

前轮同题：Melanie's activities include: running, reading, and playing the violin (me-time); a family camping trip in the mountains (last week as of 27 June 2023, i.e., 19–25 June 2023); hiking, exploring nature/forests, and roasting marshmallows around the campfire; roasting marshmallows and telling stories around the campfire on family camping trips; and making a plate in pottery class (yesterday as of 25 August 2023, i.e., 24 August 2023).，F1 0.05048076923076923。

## QA 32 · dynamic_raw_fallback

What LGBTQ+ events has Caroline participated in?

状态 succeeded / sufficient，F1 0.593939393939394。

LGBTQ support group, school event where she spoke about her transgender journey, LGBTQ+ counseling workshop, LGBTQ+ pride parade, LGBTQ conference, LGBTQ activist group, and volunteering at an LGBTQ+ youth center.

解释：All items are distinct events/activities Caroline described participating in. Dates omitted per instructions; the school event was a talk about her transgender journey, and the activist group was joined (membership), while the youth center was volunteering.

前轮同题：Caroline participated in these LGBTQ+ events/activities: a school event where she spoke about her transgender journey and encouraged students to get involved in the LGBTQ community (week of 2023-05-29 to 2023-06-04); an LGBTQ+ counseling workshop (Friday 2023-06-23); an LGBTQ+ pride parade (week of 2023-06-26 to 2023-07-02); an LGBTQ conference (two days before 2023-07-12, i.e., 2023-07-10); joining a new LGBTQ activist group (Tuesday 2023-07-18); and volunteering at an LGBTQ+ youth center (reported 2023-08-28).，F1 0.08003201280512205。

## QA 18 · dynamic_raw_fallback

Where has Melanie camped?

状态 succeeded / sufficient，F1 1.0。

The mountains, the beach, and the forest.

解释：Melanie reports camping in the mountains (last week as of 27 June 2023), at the beach, in the forest, and later camping with the kids exploring the forest and hiking. These are distinct camping events/locations, not conflicts.

前轮同题：Melanie has camped in the mountains (with her family, the week of 2023-06-19 to 2023-06-25), at the beach (family camping), and in the forest (another family camping trip).，F1 0.30264550264550266。

## QA 53 · dynamic_raw_fallback

When did Caroline apply to adoption agencies?

状态 succeeded / sufficient，F1 0.5714285714285714。

During the week of 21–27 August 2023 (exact day unknown).

解释：Caroline said she applied to adoption agencies "this week" in a source dated 23 August 2023, so the week runs Monday 21 August through Sunday 27 August 2023; the exact day is not specified.

前轮同题：Caroline applied to adoption agencies during the week of 2023-08-21 through 2023-08-27 (the week containing 23 August 2023, when she said she did it "this week"); the exact day is not stated.，F1 0.29411764705882354。

## QA 60 · dynamic_raw_fallback

What instruments does Melanie play?

状态 succeeded / sufficient，F1 1.0。

Clarinet and violin.

解释：Melanie states she plays clarinet (started when young) and lists playing violin among her me-time activities. Both are supported as instruments she plays.

前轮同题：Melanie plays the clarinet and the violin.，F1 0.6666666666666666。

## QA 136 · dynamic_raw_fallback

What does Melanie do to keep herself busy during her pottery break?

状态 failed / None，F1 None。

没有有效新答案。

解释：None

前轮同题：During her pottery break, Melanie has been reading a book Caroline recommended and painting to keep busy.，F1 0.3333333333333333。

## QA 3 · dynamic

What did Caroline research?

状态 succeeded / sufficient，F1 1.0。

Adoption agencies.

解释：Caroline said she is researching adoption agencies and looking into one such agency.

前轮同题：None，F1 0。
