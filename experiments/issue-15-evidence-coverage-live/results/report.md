# 证据覆盖优化的真实实验 A/B

状态 `completed`。复用 Build `5c7699dd6543407697ae232633154036`，未重新构建记忆库。
A 为固定 5 题定向修复及时间防退化；B 为预选 10 道尚未用于调参的新问题。
B 仅为同一 conv-26 内的问题级留出，底层对话事实已有开发暴露，不代表新对话或隐藏测试泛化。

| 实验 | 策略 | 执行成功 / 计划 | 可回答题 F1 | 官方拒答匹配 | 调用数 |
| --- | --- | --- | --- | --- | --- |
| A | dynamic | 5/5 | 0.271 | 1/1 | 15 |
| A | dynamic_raw_fallback | 5/5 | 0.142 | 1/1 | 19 |
| B | dynamic_raw_fallback | 10/10 | 0.225 | 1/2 | 34 |
| B | hybrid_no_resolution | 10/10 | 0.342 | 1/2 | 20 |

A 只与前轮同样 4 道可回答题比较，不使用前轮 8 题总均值作基点：
- `dynamic`：0.321 → 0.271。
- `dynamic_raw_fallback`：0.188 → 0.142。

适用参考规则的已知执行失败在计划均值中记 0。F1 不是语义正确率；标注来源送达也不等于完整答案。
两组题目和策略不同，不能直接用 A 与 B 的均值作泛化差值；没有预设分数保证。
同题初始和扩展候选比较保存在 results.json。没有独立动态真值，动态准确率仍未评。

本轮调用 88/102，历史累计 1097/1111，失败与重试均占额度。
原库构建摘要未变：True；快照构建摘要未变：True。

## 逐题回答与实际来源

### A · QA 3：What did Caroline research?

参考答案：Adoption agencies。

- `dynamic`：succeeded / sufficient，F1=0.267。Caroline researched adoption agencies and looked into counseling or mental health work as a career.
  解释：Caroline described researching adoption agencies (25 May 2023) and looking into counseling/mental health work as a career (27 June, 6 July, and 12 July 2023).
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：None。
  前轮同题：Caroline researched adoption agencies and also looked into counseling or mental health work as a career.；F1=0.250。
- `dynamic_raw_fallback`：succeeded / insufficient，F1=0.000。No information available.
  解释：The only supplied evidence shows Caroline saying she is off to do some research, but it does not identify the topic, field, project, or subject of that research.
  标注来源覆盖：首次解析 0.000，联合解析 0.000，最终回答 0.000。原文补查：True。
  前轮同题：No information available.；F1=0.000。

### A · QA 15：What activities does Melanie partake in?

参考答案：pottery, camping, painting, swimming。

- `dynamic`：succeeded / sufficient，F1=0.259。Melanie's activities include running, reading, playing the violin, pottery (making bowls and plates in pottery class), painting nature-inspired pictures with her partner, hiking and exploring forests, and camping with her family (including roasting marshmallows, telling stories around the campfire, and camping at the beach).
  解释：Direct statements from Melanie across sessions describe her me-time activities (running, reading, violin), pottery class and creations, painting with her partner, hiking/exploring forests, and family camping activities. All cited sources are within the conversation cutoff.
  标注来源覆盖：首次解析 0.500，联合解析 未评，最终回答 0.500。原文补查：None。
  前轮同题：Melanie's activities include running, reading, playing the violin, pottery (making bowls and plates), painting nature-inspired works with her partner, hiking and exploring forests, and camping with her family (roasting marshmallows, telling stories around the campfire, and enjoying nature).；F1=0.243。
- `dynamic_raw_fallback`：succeeded / insufficient，F1=0.000。No information available.
  解释：No delivered memories or raw sources identify specific activities Melanie actually partakes in. The only related evidence concerns intended outing planning (proposing a family outing, agreeing to plan something special, intending to think about possible activities), which does not establish accomplished activities. The raw source refers to Caroline's projects/activities, not Melanie's. A complete list of Melanie's activities is therefore missing.
  标注来源覆盖：首次解析 0.000，联合解析 0.000，最终回答 0.000。原文补查：True。
  前轮同题：Melanie partakes in running (including running longer since a prior chat), reading, playing the violin, painting with her partner (especially nature-inspired paintings lately), and pottery (which she uses for self-expression and peace, though she had to take a break after getting hurt last month).；F1=0.118。

### A · QA 153：What are Melanie's plans for the summer with respect to adoption?

参考答案：无，应识别错误前提或证据不足。

- `dynamic`：succeeded / insufficient，F1=1.000。No information available.
  解释：The only delivered evidence shows Melanie saying in October 2023 that a friend's adoption made her feel she 'maybe should do it too,' which is a tentative consideration, not a plan for the summer. No information about summer plans or any concrete adoption plan is provided.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 0.000。原文补查：None。
  前轮同题：Melanie has only said she feels like maybe she should adopt too, after a friend adopted last year; no specific summer plans are stated.；F1=0.000。
- `dynamic_raw_fallback`：succeeded / insufficient，F1=1.000。No information available.
  解释：The delivered evidence contains no Melanie adoption plan for the summer. Melanie's summer references are camping and family outings (e.g., D2:7, D10:12, D12:16), and her adoption remark is only a general reaction to her buddy's adoption ('maybe I should do it too,' D17:4) with no summer timing or concrete adoption step. Caroline, not Melanie, is researching adoption agencies (D2:8) and contacting a mentor for adoption advice (D17:1).
  标注来源覆盖：首次解析 0.000，联合解析 1.000，最终回答 1.000。原文补查：True。
  前轮同题：No information available about Melanie's summer adoption plans. The only adoption-related evidence is that on 13 October 2023 she said a friend's adoption made her feel like maybe she should adopt too.；F1=1.000。

### A · QA 0：When did Caroline go to the LGBTQ support group?

参考答案：7 May 2023。

- `dynamic`：succeeded / sufficient，F1=0.273。Caroline went to an LGBTQ support group on 7 May 2023 (she said "yesterday" in a conversation on 8 May 2023).
  解释：The source states she attended the day before the 8 May 2023 session, anchoring the event to 7 May 2023.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：None。
  前轮同题：Caroline went to an LGBTQ support group on 7 May 2023 (the day before the 8 May 2023 conversation).；F1=0.316。
- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.300。Caroline went to the LGBTQ support group on 7 May 2023 ("yesterday" relative to the 8 May 2023 session).
  解释：The memory and raw source both state she went "yesterday" relative to the 8 May 2023 session, resolving to 7 May 2023.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
  前轮同题：Caroline went to the LGBTQ support group on 7 May 2023 (the day before the 8 May 2023 conversation).；F1=0.316。

### A · QA 53：When did Caroline apply to adoption agencies?

参考答案：The week of 23 August 2023。

- `dynamic`：succeeded / sufficient，F1=0.286。Caroline applied to adoption agencies "this week," as stated in her message on 23 August 2023 — i.e., during the week preceding that date.
  解释：The source gives only the relative expression "this week" anchored to the 23 August 2023 session, so the exact day is not specified.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：None。
  前轮同题：The week of 23 August 2023 (she said she applied "this week" as of 23 August 2023).；F1=0.476。
- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.267。Caroline applied to adoption agencies "this week," in a message sent at 3:31 pm on 23 August 2023; the exact day within that week is not stated.
  解释：The raw source contains Caroline's direct statement that she applied to adoption agencies "this week," anchored to the week containing 23 August 2023. The exact day is unspecified, so the original anchored expression is retained.
  标注来源覆盖：首次解析 0.000，联合解析 1.000，最终回答 1.000。原文补查：True。
  前轮同题：During the week containing 23 August 2023 (she said on 23 August 2023 that she applied to adoption agencies "this week").；F1=0.320。

### B · QA 18：Where has Melanie camped?

参考答案：beach, mountains, forest。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.074。Melanie has camped at the beach with her family.
  解释：The raw source directly states Melanie's family was camping at the beach; no named beach or other camping locations are supported.
  标注来源覆盖：首次解析 0.000，联合解析 0.333，最终回答 0.333。原文补查：True。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.556。Melanie has camped in the mountains, in the forest, and at the beach.
  解释：Melanie describes camping in the mountains (last week as of 27 June 2023), another camping trip in the forest, and her family camping at the beach. Other camping mentions (with kids a few weeks before 13 September 2023, and a Perseid meteor shower trip last year) do not specify a location.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 55：What subject have Caroline and Melanie both painted?

参考答案：Sunsets。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.000。Nature-inspired subjects.
  解释：Melanie says they love painting together lately, especially nature-inspired ones, supporting a shared painting subject.
  标注来源覆盖：首次解析 0.500，联合解析 0.500，最终回答 0.500。原文补查：True。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.182。Both Caroline and Melanie have painted sunsets: Caroline painted a sunset picture, and Melanie painted a sunset-inspired painting.
  解释：Caroline describes painting a sunset after visiting the beach (25 Aug 2023), and Melanie shares a painting inspired by sunsets (13 Oct 2023). Both also paint other subjects, but sunset is the shared subject supported by the delivered evidence.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 0.000。原文补查：None。

### B · QA 36：When did Caroline join a mentorship program?

参考答案：The weekend before 17 July 2023。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.267。Caroline joined a mentorship program for LGBTQ youth "last weekend" relative to 17 July 2023, i.e., the weekend of 15–16 July 2023; the exact day is not stated.
  解释：The source session time is 2:31 pm on 17 July 2023, and Caroline said she joined "Last weekend." Resolved against that session date, the join occurred on the weekend of 15–16 July 2023; the exact day is not specified, so the interval is retained.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.417。Caroline joined a mentorship program for LGBTQ youth last weekend, relative to 17 July 2023 (i.e., the weekend before that date).
  解释：The source states 'Last weekend I joined a mentorship program for LGBTQ youth' at session time 2:31 pm on 17 July 2023, so the join date is anchored to the weekend before 17 July 2023; no exact calendar date is given.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 74：When did Melanie's family go on a roadtrip?

参考答案：The weekend before 20 October 2023。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.278。Melanie said the roadtrip was "this past weekend" in a session dated 20 October 2023, so it took place the weekend immediately before 20 October 2023; the exact day within that weekend is not stated.
  解释：The source session time is 6:55 pm on 20 October 2023, and the original expression "this past weekend" anchors the trip to the weekend before that date. The exact day is not given.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.417。Melanie's family went on the roadtrip "this past weekend" relative to 20 October 2023, i.e., the weekend before 20 October 2023.
  解释：The source states the roadtrip occurred "this past weekend" as of the 20 October 2023 session, so the exact day is not given; the original relative expression is preserved.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 65：What are some changes Caroline has faced during her transition journey?

参考答案：Changes to her body, losing unsupportive friends。

- `dynamic_raw_fallback`：succeeded / insufficient，F1=0.271。Caroline's transition changed her relationships: some close friends kept supporting her, while a few couldn't handle it, and her relationships now feel more genuine. Art also allowed her to explore her transition and changing body.
  解释：Supported: relationship changes and art as a way to explore her transition/changing body. Missing: specific personal-development details Caroline described since coming out, and the evidence does not provide an exhaustive list of every change she faced.
  标注来源覆盖：首次解析 1.000，联合解析 1.000，最终回答 1.000。原文补查：True。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.317。Caroline's transition changed her relationships: some close friends kept supporting her, but a few weren't able to handle it, and her relationships now feel more genuine. She found transitioning and acceptance difficult, but support from friends, family, and people she looked up to helped her through tough times. Art allowed her to explore her transition and changing body, and she realized she could be herself without fear and had the courage to transition.
  解释：Supported changes include altered relationships (some friends supportive, a few unable to handle it), a difficult transition and acceptance process eased by support, art as a way to explore her transition and changing body, and gaining courage to be herself without fear. The evidence is as of the conversation cutoff.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 136：What does Melanie do to keep herself busy during her pottery break?

参考答案：Read a book and paint.。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.200。Melanie has been painting to keep busy.
  解释：The cited memory and raw source state that Melanie has been painting to keep busy; the source also mentions reading a recommended book, but the direct answer to the pottery-break question is painting.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.143。Melanie has been painting to keep busy during her pottery break.
  解释：In the 13 October 2023 session, Melanie says she had to take a break from pottery after getting hurt and that she has been painting to keep busy.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 32：What LGBTQ+ events has Caroline participated in?

参考答案：Pride parade, school speech, support group。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.042。Caroline participated in a school LGBTQ-related event (around "last week" relative to 9 June 2023), where she spoke about her transgender journey and encouraged students to get involved in the LGBTQ community; she also volunteered at an LGBTQ+ youth center (mentioned 28 August 2023).
  解释：The school event's exact date is unknown; the source only says "last week" relative to the 9 June 2023 session. The list may not be complete, as additional events are not described.
  标注来源覆盖：首次解析 0.250，联合解析 未评，最终回答 0.250。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.041。Caroline has participated in: an LGBTQ support group (the day before 8 May 2023); a school event where she spoke about her transgender journey and encouraged students to get involved in the LGBTQ community (last week as of 9 June 2023); an LGBTQ+ counseling workshop (last Friday as of 27 June 2023); an LGBTQ+ pride parade (last week as of 3 July 2023); an LGBTQ conference (two days before 12 July 2023); a mentorship program for LGBTQ youth (last weekend as of 17 July 2023); a new LGBTQ activist group, 'Connected LGBTQ Activists' (last Tuesday as of 20 July 2023); and volunteering at an LGBTQ+ youth center (as of 28 August 2023).
  解释：All listed events are past participations reported by Caroline. Relative times are anchored to each source session date. Her LGBTQ art show is a plan for the following month, not a completed event, so it is excluded from participation.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 0.750。原文补查：None。

### B · QA 60：What instruments does Melanie play?

参考答案：clarinet and violin。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.667。Melanie plays clarinet and violin.
  解释：Clarinet is stated directly; violin appears among her me-time activities. These are the instruments explicitly mentioned, not necessarily an exhaustive list.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.667。Melanie plays the clarinet and the violin.
  解释：Melanie states she plays clarinet (started when young) and lists playing her violin among her me-time activities.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 178：Is Oscar Melanie's pet?

参考答案：No。

- `dynamic_raw_fallback`：succeeded / sufficient，F1=0.000。No. Oscar is Caroline's guinea pig, not Melanie's pet. Melanie's pets are Luna and Oliver, and she later got another cat named Bailey.
  解释：Caroline identifies Oscar as her guinea pig; Melanie names her pets as Luna and Oliver and later mentions another cat, Bailey.
  标注来源覆盖：首次解析 1.000，联合解析 未评，最终回答 1.000。原文补查：False。
- `hybrid_no_resolution`：succeeded / sufficient，F1=0.000。No. Oscar is Caroline's guinea pig, not Melanie's pet.
  解释：Caroline states Oscar is her guinea pig. Melanie's pets are named Luna and Oliver (plus later Bailey), so Oscar is not Melanie's pet.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。

### B · QA 191：What happened to Caroline's son on their road trip?

参考答案：无，应识别错误前提或证据不足。

- `dynamic_raw_fallback`：succeeded / insufficient，F1=1.000。No information available.
  解释：The delivered evidence only describes Melanie's son: he got into an accident during their road trip and was okay afterward. No evidence identifies a son of Caroline, says Caroline's son was on the road trip, or describes what happened to him.
  标注来源覆盖：首次解析 1.000，联合解析 1.000，最终回答 1.000。原文补查：True。
- `hybrid_no_resolution`：succeeded / insufficient，F1=1.000。No information available.
  解释：The question asks about Caroline's son on their road trip. The delivered evidence contains no information about Caroline having a son or about a road trip involving Caroline's son. The road-trip accident evidence concerns Melanie's son, not Caroline's, so it does not answer the question.
  标注来源覆盖：首次解析 未评，联合解析 未评，最终回答 1.000。原文补查：None。
