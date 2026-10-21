# conv-26：答案输出优化后的四策略复验

Build `5c7699dd6543407697ae232633154036`；Run `70f6545c0de94cdabf5507be050a26da`；状态 `completed`。

10 道官方原始开发集 QA，四策略共 40 项。8 道有参考答案，2 道是证据不足对抗题。
同题配对、单次运行，不能推断统计显著性；未运行全关闭思考对照，不能单独归因于思考强度。

| 策略 | 成功 / 计划 | 可回答 8 题 QA 均值 | 2 题官方拒答匹配 | 全部 10 题均值 | 平均尝试秒数 | 查询 tokens |
| --- | --- | --- | --- | --- | --- | --- |
| dynamic | 10/10 | 0.334 | 0.500 | 0.367 | 25.55 | 725217 |
| dynamic_raw_fallback | 10/10 | 0.340 | 1.000 | 0.472 | 23.72 | 278361 |
| hybrid_no_resolution | 10/10 | 0.388 | 0.500 | 0.411 | 2.53 | 78966 |
| full_text | 10/10 | 0.376 | 1.000 | 0.501 | 2.57 | 635288 |

Full Text 完整来源并获得 HTTP 200 的项目为 10/10；预期来源轮次数为 [419]。其中答案也通过校验的项目为 10/10。完整来源检查要求未截断且未超出上下文。
原文兜底实际触发 7/10 题；逐题检索、有效与引用来源数见 CSV。
共享账本累计预留 1009/1111 次，包含历史、失败、重试及未知结果。

官方 QA 采用既有类别 F1 和拒答短语规则，长答案可能因多余词扣分。
计划均值与下表对已知失败记 0；CSV 的 qa_score 保留失败时未生成原始得分的 null，run_qa_score 记录聚合采用的值。
拒答规则只识别 `no information available`、`not mentioned`，须结合实际回答检查。
来源覆盖只说明标注轮次是否进入上下文，不证明事实正确。对抗题的标注轮次可能属于另一人物。
三种 RAG 各自执行查询分析；从成功结果及失败轨迹核对候选集合，相同题数为 dynamic 对 dynamic_raw_fallback：初始 10/10、扩展 10/10；dynamic 对 hybrid_no_resolution：初始 10/10、扩展 10/10。逐题顺序与集合比较见 results.json 的 candidate_comparisons。
`dynamic` 与 `hybrid_no_resolution` 比较查询时有效证据解析，两者仍共享构建时关系与历史扩展，不能据此隔离构建关系判断的作用。
动态关系与有效证据准确率缺少独立真值，保持未评。Full Text 的完整来源覆盖不算检索能力。

## 同题得分

| 官方 QA index | 用途 | dynamic | dynamic_raw_fallback | hybrid_no_resolution | full_text |
| --- | --- | --- | --- | --- | --- |
| 3 | fact | 0.250 | 0.000 | 0.667 | 0.667 |
| 4 | fact | 0.333 | 0.333 | 0.333 | 0.286 |
| 13 | cross_session | 0.316 | 0.133 | 0.400 | 0.353 |
| 15 | cross_session | 0.243 | 0.118 | 0.321 | 0.322 |
| 0 | time | 0.316 | 0.316 | 0.316 | 0.316 |
| 16 | time | 0.261 | 1.000 | 0.214 | 0.316 |
| 53 | state_progression | 0.476 | 0.320 | 0.385 | 0.417 |
| 79 | state_progression | 0.476 | 0.500 | 0.471 | 0.333 |
| 153 | insufficient | 0.000 | 1.000 | 0.000 | 1.000 |
| 157 | insufficient | 1.000 | 1.000 | 1.000 | 1.000 |

## 逐题回答

### QA 3：What did Caroline research?

参考：Adoption agencies。

- `dynamic`，succeeded / sufficient，QA=0.250，来源覆盖=1.000。Caroline researched adoption agencies and also looked into counseling or mental health work as a career.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。No information available.
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.667，来源覆盖=1.000。Caroline researched adoption agencies, and she has also been looking into counseling or mental health work as a career.
- `full_text`，succeeded / sufficient，QA=0.667，来源覆盖=1.000。Caroline researched adoption agencies, with the goal of adopting and giving a loving home to children in need.

### QA 4：What is Caroline's identity?

参考：Transgender woman。

- `dynamic`，succeeded / sufficient，QA=0.333，来源覆盖=0.000。Caroline is a trans woman.
- `dynamic_raw_fallback`，succeeded / sufficient，QA=0.333，来源覆盖=0.000。Caroline is a trans woman.
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.333，来源覆盖=0.000。Caroline is a trans woman, an artist from Sweden, and a member of the LGBTQ activist group 'Connected LGBTQ Activists.'
- `full_text`，succeeded / sufficient，QA=0.286，来源覆盖=1.000。Caroline is a transgender woman who transitioned about three years before June 2023, is originally from Sweden, and is pursuing adoption as a single parent while working toward a career in counseling/mental health.

### QA 13：What career path has Caroline decided to persue?

参考：counseling or mental health for Transgender people。

- `dynamic`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。Caroline has decided to pursue counseling and mental health as her career path, with a particular interest in working with trans people to help them accept themselves and support their mental health.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.133，来源覆盖=0.000。No final career path is established; Caroline said she would continue her education and check out career options, and she has been looking into counseling and mental-health careers.
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.400，来源覆盖=1.000。Caroline has decided to pursue counseling and mental health, with a particular interest in working with trans people.
- `full_text`，succeeded / sufficient，QA=0.353，来源覆盖=1.000。Caroline has decided to pursue a career in counseling and mental health, with a focus on working with transgender people to help them accept themselves and support their mental health.

### QA 15：What activities does Melanie partake in?

参考：pottery, camping, painting, swimming。

- `dynamic`，succeeded / sufficient，QA=0.243，来源覆盖=0.500。Melanie's activities include running, reading, playing the violin, pottery (making bowls and plates), painting nature-inspired works with her partner, hiking and exploring forests, and camping with her family (roasting marshmallows, telling stories around the campfire, and enjoying nature).
- `dynamic_raw_fallback`，succeeded / sufficient，QA=0.118，来源覆盖=0.000。Melanie partakes in running (including running longer since a prior chat), reading, playing the violin, painting with her partner (especially nature-inspired paintings lately), and pottery (which she uses for self-expression and peace, though she had to take a break after getting hurt last month).
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.321，来源覆盖=0.000。Melanie's activities include running, reading, playing the violin, pottery, hiking and exploring forests, and camping with her family (roasting marshmallows, telling stories around the campfire, and enjoying nature).
- `full_text`，succeeded / sufficient，QA=0.322，来源覆盖=1.000。Melanie paints (including landscapes, still life, animals, and abstract works), does pottery (she has taken pottery classes and a pottery workshop with her kids), runs (including a charity race for mental health), plays the clarinet, swims with her kids, camps and hikes with her family, goes to the beach, visits museums and parks with her kids, volunteers at a homeless shelter with her family, and attends concerts and live music shows.

### QA 0：When did Caroline go to the LGBTQ support group?

参考：7 May 2023。

- `dynamic`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。Caroline went to an LGBTQ support group on 7 May 2023 (the day before the 8 May 2023 conversation).
- `dynamic_raw_fallback`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。Caroline went to the LGBTQ support group on 7 May 2023 (the day before the 8 May 2023 conversation).
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。Caroline went to an LGBTQ support group the day before 8 May 2023, i.e., on 7 May 2023.
- `full_text`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。She went the day before 8 May 2023 (i.e., 7 May 2023), saying she had gone "yesterday."

### QA 16：When did Melanie sign up for a pottery class?

参考：2 July 2023。

- `dynamic`，succeeded / sufficient，QA=0.261，来源覆盖=1.000。Melanie signed up for a pottery class yesterday, i.e., on 2 July 2023 (relative to her message on 3 July 2023).
- `dynamic_raw_fallback`，succeeded / sufficient，QA=1.000，来源覆盖=1.000。2 July 2023
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.214，来源覆盖=1.000。Melanie signed up for a pottery class the day before 3 July 2023, i.e., on 2 July 2023 (she said "yesterday" in a session on 3 July 2023).
- `full_text`，succeeded / sufficient，QA=0.316，来源覆盖=1.000。Melanie signed up for a pottery class the day before 3 July 2023, i.e., on 2 July 2023.

### QA 53：When did Caroline apply to adoption agencies?

参考：The week of 23 August 2023。

- `dynamic`，succeeded / sufficient，QA=0.476，来源覆盖=1.000。The week of 23 August 2023 (she said she applied "this week" as of 23 August 2023).
- `dynamic_raw_fallback`，succeeded / sufficient，QA=0.320，来源覆盖=1.000。During the week containing 23 August 2023 (she said on 23 August 2023 that she applied to adoption agencies "this week").
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.385，来源覆盖=1.000。Caroline applied to adoption agencies "this week" as of her 23 August 2023 message, i.e., during the week containing 23 August 2023.
- `full_text`，succeeded / sufficient，QA=0.417，来源覆盖=1.000。Caroline applied to adoption agencies this week, as of her 23 August 2023 conversation (the week containing 23 August 2023).

### QA 79：When did Caroline pass the adoption interview?

参考：The Friday before 22 October 2023。

- `dynamic`，succeeded / sufficient，QA=0.476，来源覆盖=1.000。Last Friday, relative to 22 October 2023 (the Friday before that date; exact calendar date not stated).
- `dynamic_raw_fallback`，succeeded / sufficient，QA=0.500，来源覆盖=1.000。Friday 20 October 2023 ("last Friday" relative to 22 October 2023).
- `hybrid_no_resolution`，succeeded / sufficient，QA=0.471，来源覆盖=1.000。Last Friday, relative to 22 October 2023 (the exact date was not stated).
- `full_text`，succeeded / sufficient，QA=0.333，来源覆盖=1.000。Caroline passed the adoption agency interviews last Friday, i.e. Friday 20 October 2023 (relative to her 22 October 2023 message).

### QA 153：What are Melanie's plans for the summer with respect to adoption?

参考：无参考答案，应识别证据不足。

- `dynamic`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。Melanie has only said she feels like maybe she should adopt too, after a friend adopted last year; no specific summer plans are stated.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=1.000，来源覆盖=0.000。No information available about Melanie's summer adoption plans. The only adoption-related evidence is that on 13 October 2023 she said a friend's adoption made her feel like maybe she should adopt too.
- `hybrid_no_resolution`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。No specific summer adoption plans are stated; Melanie only says her buddy's adoption makes her feel like maybe she should adopt too.
- `full_text`，succeeded / insufficient，QA=1.000，来源覆盖=1.000。No information available.

### QA 157：What does Melanie's necklace symbolize?

参考：无参考答案，应识别证据不足。

- `dynamic`，succeeded / insufficient，QA=1.000，来源覆盖=0.000。No information available.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=1.000，来源覆盖=1.000。No information available.
- `hybrid_no_resolution`，succeeded / insufficient，QA=1.000，来源覆盖=1.000。No information available.
- `full_text`，succeeded / insufficient，QA=1.000，来源覆盖=1.000。No information available.
