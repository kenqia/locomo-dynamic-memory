# 查询可靠性真实复验

使用既有评测 API 的类别 F1；失败记 0，未完成不算成功。固定开发题单轮复验，不能作为统计显著性或隐藏测试成绩。
逐题语义由作者核对原文并另记结论，不增加独立 LLM 评估器。历史对照不是同时运行的随机对照。

状态 `completed_with_errors`，本轮调用 44/64。

| 组 | 成功 / 计划 | 失败项 | 成功可回答题 F1 | 全部可回答题 F1（失败记0） | 同题前后比较（失败记0） |
| --- | --- | --- | --- | --- | --- |
| primary | 11/11 | 0 | 0.31844187888830744 | 0.31844187888830744 | 10题：0.20935185185185184 → 0.31844187888830744 |
| dynamic_nonregression | 2/3 | 1 | 0.32302631578947366 | 0.21535087719298246 | 3题：0.2704365079365079 → 0.21535087719298246 |

## QA 0 · dynamic_raw_fallback

When did Caroline go to the LGBTQ support group?

状态 succeeded / sufficient，F1 0.2857142857142857。

Caroline went to the LGBTQ support group on 7 May 2023 (she said “yesterday” in the 8 May 2023 session).

解释：Memory 7b29fbb3088ff54b1d95727f records Caroline’s statement that she went to an LGBTQ support group “yesterday,” anchored to the source session time of 1:56 pm on 8 May 2023, giving 7 May 2023.

前轮同题：Caroline went to the LGBTQ support group on 7 May 2023 ("yesterday" relative to the 8 May 2023 session).，F1 0.3。

## QA 3 · dynamic_raw_fallback

What did Caroline research?

状态 succeeded / sufficient，F1 0.5714285714285714。

Caroline was researching adoption agencies.

解释：Supported by Caroline's statement on 25 May 2023 that she was researching adoption agencies, motivated by her dream of having a family and giving a loving home to children in need.

前轮同题：No information available.，F1 0.0。

## QA 15 · dynamic_raw_fallback

What activities does Melanie partake in?

状态 succeeded / sufficient，F1 0.05048076923076923。

Melanie's activities include: running, reading, and playing the violin (me-time); a family camping trip in the mountains (last week as of 27 June 2023, i.e., 19–25 June 2023); hiking, exploring nature/forests, and roasting marshmallows around the campfire; roasting marshmallows and telling stories around the campfire on family camping trips; and making a plate in pottery class (yesterday as of 25 August 2023, i.e., 24 August 2023).

解释：All items are drawn from Melanie's own statements. The camping trip is a completed past event (last week relative to 27 June 2023); the pottery plate was made the day before 25 August 2023. Camping-related details across sources corroborate rather than conflict. No raw_sources were supplied, so only memory citations are used.

前轮同题：No information available.，F1 0.0。

## QA 18 · dynamic_raw_fallback

Where has Melanie camped?

状态 succeeded / sufficient，F1 0.30264550264550266。

Melanie has camped in the mountains (with her family, the week of 2023-06-19 to 2023-06-25), at the beach (family camping), and in the forest (another family camping trip).

解释：Three distinct camping locations are supported: mountains (completed trip, 'last week' anchored to the 2023-06-27 source, i.e., 2023-06-19 through 2023-06-25), beach (family camping habit), and forest (another family camping trip). The beach statement is a general habit rather than a dated event; no exact dates are given for the beach or forest trips.

前轮同题：Melanie has camped at the beach with her family.，F1 0.07407407407407407。

## QA 32 · dynamic_raw_fallback

What LGBTQ+ events has Caroline participated in?

状态 succeeded / sufficient，F1 0.08003201280512205。

Caroline participated in these LGBTQ+ events/activities: a school event where she spoke about her transgender journey and encouraged students to get involved in the LGBTQ community (week of 2023-05-29 to 2023-06-04); an LGBTQ+ counseling workshop (Friday 2023-06-23); an LGBTQ+ pride parade (week of 2023-06-26 to 2023-07-02); an LGBTQ conference (two days before 2023-07-12, i.e., 2023-07-10); joining a new LGBTQ activist group (Tuesday 2023-07-18); and volunteering at an LGBTQ+ youth center (reported 2023-08-28).

解释：All six items are distinct reported events/activities; relations between them are undetermined, so they are listed separately rather than merged. Dates are anchored to each source session_time: 'last week' at 2023-06-09 = 2023-05-29 to 2023-06-04; 'Last Friday' at 2023-06-27 = 2023-06-23; 'Last week' at 2023-07-03 = 2023-06-26 to 2023-07-02; 'two days ago' at 2023-07-12 = 2023-07-10; 'last Tues' at 2023-07-20 = 2023-07-18. The youth-center volunteering has no explicit time expression, only the 2023-08-28 report date.

前轮同题：Caroline participated in a school LGBTQ-related event (around "last week" relative to 9 June 2023), where she spoke about her transgender journey and encouraged students to get involved in the LGBTQ community; she also volunteered at an LGBTQ+ youth center (mentioned 28 August 2023).，F1 0.041666666666666664。

## QA 36 · dynamic_raw_fallback

When did Caroline join a mentorship program?

状态 succeeded / sufficient，F1 0.26666666666666666。

Caroline joined a mentorship program for LGBTQ youth last weekend relative to 17 July 2023, i.e., the weekend of 15–16 July 2023. No exact day is specified.

解释：The source session_time is 2:31 pm on 17 July 2023, and Caroline said she joined 'Last weekend,' so the join date is the preceding weekend, 15–16 July 2023. The exact day is not given, so the weekend range is retained.

前轮同题：Caroline joined a mentorship program for LGBTQ youth "last weekend" relative to 17 July 2023, i.e., the weekend of 15–16 July 2023; the exact day is not stated.，F1 0.26666666666666666。

## QA 53 · dynamic_raw_fallback

When did Caroline apply to adoption agencies?

状态 succeeded / sufficient，F1 0.29411764705882354。

Caroline applied to adoption agencies during the week of 2023-08-21 through 2023-08-27 (the week containing 23 August 2023, when she said she did it "this week"); the exact day is not stated.

解释：The source expression "this week" is anchored to the source session time of 3:31 pm on 23 August 2023, giving the Monday–Sunday week 2023-08-21 to 2023-08-27. The precise day within that week is unknown.

前轮同题：Caroline applied to adoption agencies "this week," in a message sent at 3:31 pm on 23 August 2023; the exact day within that week is not stated.，F1 0.26666666666666666。

## QA 60 · dynamic_raw_fallback

What instruments does Melanie play?

状态 succeeded / sufficient，F1 0.6666666666666666。

Melanie plays the clarinet and the violin.

解释：Clarinet is stated directly by Melanie on 28 August 2023; violin is mentioned as one of her me-time activities on 25 May 2023. Both are attributed to Melanie herself.

前轮同题：Melanie plays clarinet and violin.，F1 0.6666666666666666。

## QA 74 · dynamic_raw_fallback

When did Melanie's family go on a roadtrip?

状态 succeeded / sufficient，F1 0.3333333333333333。

Melanie's family roadtrip happened "this past weekend" relative to the 20 October 2023 conversation, i.e., the weekend of 14–15 October 2023.

解释：The source session_time is 6:55 pm on 20 October 2023, and Melanie says the roadtrip was "this past weekend," placing it on the weekend of 14–15 October 2023. Her son was on the trip and got into an accident, supporting family participation. Exact day within the weekend is not specified.

前轮同题：Melanie said the roadtrip was "this past weekend" in a session dated 20 October 2023, so it took place the weekend immediately before 20 October 2023; the exact day within that weekend is not stated.，F1 0.2777777777777778。

## QA 136 · dynamic_raw_fallback

What does Melanie do to keep herself busy during her pottery break?

状态 succeeded / sufficient，F1 0.3333333333333333。

During her pottery break, Melanie has been reading a book Caroline recommended and painting to keep busy.

解释：Melanie said she had to take a break from pottery after getting hurt last month (source dated 13 October 2023), and that she has been reading a recommended book and painting to keep busy. The reading detail comes from the raw source text; the painting activity is also captured in memory eef2de7a1146b7880239b699.

前轮同题：Melanie has been painting to keep busy.，F1 0.2。

## QA 153 · dynamic_raw_fallback

What are Melanie's plans for the summer with respect to adoption?

状态 succeeded / insufficient，F1 1.0。

No information available.

解释：The only adoption-related evidence about Melanie is an uncertain October 2023 statement that she maybe should adopt too, prompted by a friend's adoption. It contains no summer timing and no concrete adoption plan, so the requested summer adoption plan is not supported.

前轮同题：No information available.，F1 1.0。

## QA 3 · dynamic

What did Caroline research?

状态 failed / None，F1 None。

没有有效新答案。

解释：None

前轮同题：Caroline researched adoption agencies and looked into counseling or mental health work as a career.，F1 0.26666666666666666。

## QA 15 · dynamic

What activities does Melanie partake in?

状态 succeeded / sufficient，F1 0.225。

Melanie's activities include running, reading, playing the violin, pottery (making bowls and plates), painting (especially nature-inspired paintings with her partner), hiking, exploring forests, and camping with her family (including roasting marshmallows, telling stories around the campfire, and enjoying nature).

解释：Activities are drawn from Melanie's stated me-time hobbies (running, reading, violin), her pottery class work, painting with her partner, and family hiking/camping activities. Note she took a break from pottery after an injury last month (as of 13 October 2023).

前轮同题：Melanie's activities include running, reading, playing the violin, pottery (making bowls and plates in pottery class), painting nature-inspired pictures with her partner, hiking and exploring forests, and camping with her family (including roasting marshmallows, telling stories around the campfire, and camping at the beach).，F1 0.2589285714285714。

## QA 53 · dynamic

When did Caroline apply to adoption agencies?

状态 succeeded / sufficient，F1 0.42105263157894735。

Caroline applied to adoption agencies during the week of 21–27 August 2023 (exact day unknown).

解释：Caroline said she applied to adoption agencies "this week" in a message sent 23 August 2023, anchoring the application to the week of Monday 21 August through Sunday 27 August 2023; the exact day is not stated.

前轮同题：Caroline applied to adoption agencies "this week," as stated in her message on 23 August 2023 — i.e., during the week preceding that date.，F1 0.2857142857142857。
