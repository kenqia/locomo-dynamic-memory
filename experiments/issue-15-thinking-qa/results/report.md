# conv-26：分阶段思考与四策略对照

Build `5c7699dd6543407697ae232633154036`；Run `1e6e9dac610b4491b1362a151022af05`；状态 `completed_with_errors`。

10 道官方原始开发集 QA，四策略共 40 项。8 道有参考答案，2 道是证据不足对抗题。
同题配对、单次运行，不能推断统计显著性；未运行全关闭思考对照，不能单独归因于思考强度。

| 策略 | 成功 / 计划 | 可回答 8 题 QA 均值 | 2 题官方拒答匹配 | 全部 10 题均值 | 平均尝试秒数 | 查询 tokens |
| --- | --- | --- | --- | --- | --- | --- |
| dynamic | 9/10 | 0.154 | 0.000 | 0.123 | 28.69 | 923490 |
| dynamic_raw_fallback | 4/10 | 0.039 | 0.000 | 0.032 | 22.68 | 295731 |
| hybrid_no_resolution | 3/10 | 0.020 | 0.000 | 0.016 | 4.84 | 182704 |
| full_text | 8/10 | 0.179 | 0.000 | 0.143 | 3.09 | 885971 |

Full Text 完整来源并获得 HTTP 200 的项目为 10/10；预期来源轮次数为 [419]。其中答案也通过校验的项目为 8/10。完整来源检查要求未截断且未超出上下文。
原文兜底实际触发 7/10 题；逐题检索、有效与引用来源数见 CSV。
共享账本累计预留 907/1000 次，包含历史、失败、重试及未知结果。

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
| 3 | fact | 0.167 | 0.000 | 0.000 | 0.174 |
| 4 | fact | 0.182 | 0.000 | 0.000 | 0.200 |
| 13 | cross_session | 0.267 | 0.316 | 0.000 | 0.286 |
| 15 | cross_session | 0.000 | 0.000 | 0.000 | 0.224 |
| 0 | time | 0.130 | 0.000 | 0.000 | 0.122 |
| 16 | time | 0.128 | 0.000 | 0.000 | 0.120 |
| 53 | state_progression | 0.192 | 0.000 | 0.000 | 0.147 |
| 79 | state_progression | 0.164 | 0.000 | 0.163 | 0.160 |
| 153 | insufficient | 0.000 | 0.000 | 0.000 | 0.000 |
| 157 | insufficient | 0.000 | 0.000 | 0.000 | 0.000 |

## 逐题回答

### QA 3：What did Caroline research?

参考：Adoption agencies。

- `dynamic`，succeeded / sufficient，QA=0.167，来源覆盖=1.000。Caroline researched two areas: adoption agencies (she was looking into an adoption agency as part of her dream to give kids a loving home), and counseling/mental health work as a career (she had been looking into counseling or mental health work and started exploring counseling and mental health career options). This is based on evidence available as of the conversation cutoff (9:55 am on 22 October, 2023); later developments are not known.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。The supplied evidence does not identify what Caroline researched. The only raw source where Caroline refers to her own research is her statement that she was "off to go do some research," which does not state the subject or topic. Other mentions of research in the evidence concern advice to Melanie or Melanie's own research, not Caroline's. Therefore, the topic of Caroline's research is unknown from the delivered evidence.

Known only as of the conversation cutoff (2023-10-22T09:55:00); later reality is unknown.
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.174，来源覆盖=1.000。Caroline researched adoption agencies — she described it as a dream to have a family and give a loving home to kids who need it, and she chose an agency that helps LGBTQ+ folks with adoption because of its inclusivity and support. She also mentioned doing research more generally before heading off ("off to go do some research"), but the specific research she described was into adoption agencies. This is based on the conversation as of the cutoff of 9:55 am on 22 October, 2023; I cannot speak to anything after that time.

### QA 4：What is Caroline's identity?

参考：Transgender woman。

- `dynamic`，succeeded / sufficient，QA=0.182，来源覆盖=0.000。Caroline identifies as a trans woman. In her own words, she made a painting to show her path as a trans woman, describing it as a reminder to love her authentic self. This is as of the conversation cutoff on 22 October, 2023; later changes are not known.
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.200，来源覆盖=1.000。Caroline is a transgender woman. She describes her "transgender journey" and transitioning (she began transitioning about three years before June 2023), speaks of sharing her story as a trans woman, and is active in the LGBTQ+ community—attending support groups, pride parades, conferences, and advocacy/mentoring work. She is originally from Sweden (she moved from her home country and has a grandmother there), is a single person pursuing adoption to become a parent, and is interested in a career in counseling/mental health. She is also an artist who paints about her trans experience. (This reflects only what was stated up to the conversation cutoff of 9:55 am on 22 October, 2023.)

### QA 13：What career path has Caroline decided to persue?

参考：counseling or mental health for Transgender people。

- `dynamic`，succeeded / sufficient，QA=0.267，来源覆盖=0.500。Caroline has decided to pursue a career in counseling and mental health. She has been looking into counseling and mental health career options, and as of 3 July 2023 she still considered counseling and mental health the path she wants to pursue. She has also expressed interest in working specifically with trans people, helping them accept themselves and supporting their mental health, though she noted she was still figuring out the details. This reflects the evidence available as of the conversation cutoff on 22 October 2023; later developments are not known.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.316，来源覆盖=0.000。The supplied evidence does not show that Caroline has firmly decided on or committed to a specific career path. She said she would continue her education and check out career options (D1:9), and later said she had been looking into counseling and mental health as a career, motivated by wanting to help people who went through similar experiences (D4:11; D7:7). These statements indicate exploration of counseling and mental health career options, not a confirmed decision. This answer reflects the conversation cutoff of 9:55 am on 22 October, 2023; anything beyond that cutoff is unknown.

Known only as of the conversation cutoff (2023-10-22T09:55:00); later reality is unknown.
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.286，来源覆盖=1.000。Caroline has decided to pursue a career in counseling and mental health work. She is keen on counseling or working in mental health, wanting to support people (particularly trans people) who have gone through similar experiences to hers, helping them accept themselves and supporting their mental health. She has been researching this path and attended an LGBTQ+ counseling workshop. As of the conversation cutoff (9:55 am on 22 October, 2023), this is her stated career direction; I cannot speak to any developments after that time.

### QA 15：What activities does Melanie partake in?

参考：pottery, camping, painting, swimming。

- `dynamic`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.224，来源覆盖=1.000。Melanie partakes in a variety of activities, especially creative and family-oriented ones. She paints (including a lake sunrise painting and nature-inspired paintings with her kids) and describes painting as a way to express feelings and relax. She does pottery, having signed up for a pottery class and made bowls, plates, and pots, and she took her kids to a pottery workshop. She also plays the violin and clarinet, runs (including a charity race for mental health and running to de-stress), reads, swims with her kids, and enjoys family activities such as camping (including roasting marshmallows, hiking, and exploring nature), going to the beach, visiting museums, going to parks, attending concerts, and volunteering at a homeless shelter with her family. She also cares for pets (a dog and cats). This is based on conversations up to the cutoff of 9:55 am on 22 October, 2023; I cannot speak to anything after that time.

### QA 0：When did Caroline go to the LGBTQ support group?

参考：7 May 2023。

- `dynamic`，succeeded / sufficient，QA=0.130，来源覆盖=1.000。Caroline said she went to an LGBTQ support group "yesterday" relative to her statement on 8 May 2023, so the visit was on 7 May 2023. This is only as of the supplied conversation cutoff (9:55 am on 22 October 2023); no later information is known.
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.122，来源覆盖=1.000。Caroline said she went to an LGBTQ support group "yesterday" during a conversation on 8 May 2023, which places the visit on 7 May 2023. (This is based on the conversation record as of the cutoff of 9:55 am on 22 October 2023; I cannot speak to anything after that time.)

### QA 16：When did Melanie sign up for a pottery class?

参考：2 July 2023。

- `dynamic`，succeeded / sufficient，QA=0.128，来源覆盖=1.000。Melanie said she signed up for a pottery class "yesterday" relative to her message on 3 July 2023, so she signed up on 2 July 2023. This is only as of the supplied conversation cutoff (9:55 am on 22 October 2023); later reality is not known.
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.120，来源覆盖=1.000。Melanie said she signed up for a pottery class "yesterday" relative to her message on 3 July, 2023, so she signed up on 2 July, 2023. (This is based on the conversation up to the cutoff of 9:55 am on 22 October, 2023; I cannot speak to anything after that.)

### QA 53：When did Caroline apply to adoption agencies?

参考：The week of 23 August 2023。

- `dynamic`，succeeded / sufficient，QA=0.192，来源覆盖=1.000。Caroline said she applied to adoption agencies "this week" in a message sent at 3:31 pm on 23 August 2023, so the application occurred during the week preceding that session (around mid-to-late August 2023). This is only as of the supplied conversation cutoff (22 October 2023); later reality is not known.
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `full_text`，succeeded / sufficient，QA=0.147，来源覆盖=1.000。Caroline applied to adoption agencies during the week before 23 August 2023. In her message on 23 August 2023 she said, "Guess what I did this week? I took the first step towards becoming a mom - I applied to adoption agencies!" (Note: this is based on the conversation record up to the cutoff of 9:55 am on 22 October 2023; I cannot speak to anything after that time.)

### QA 79：When did Caroline pass the adoption interview?

参考：The Friday before 22 October 2023。

- `dynamic`，succeeded / sufficient，QA=0.164，来源覆盖=1.000。Caroline passed the adoption agency interviews "last Friday" relative to the session time of 9:55 am on 22 October 2023. The exact calendar date is not stated in the source, but it would be the Friday before 22 October 2023 (i.e., 20 October 2023). This is only as of the supplied conversation cutoff of 22 October 2023; later reality is not known.
- `dynamic_raw_fallback`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}
- `hybrid_no_resolution`，succeeded / insufficient，QA=0.163，来源覆盖=1.000。The exact date Caroline passed the adoption interview is not stated. She reported on 22 October 2023 that she passed the adoption agency interviews "last Friday," which places the event relative to that session but does not give a precise calendar date. Evidence is insufficient to state an exact date.
- `full_text`，succeeded / sufficient，QA=0.160，来源覆盖=1.000。Caroline passed the adoption agency interviews on Friday, 20 October 2023 — she announced it on 22 October 2023, saying she had passed them "last Friday." (This is only as of the supplied conversation cutoff of 9:55 am on 22 October 2023; later developments are not known.)

### QA 153：What are Melanie's plans for the summer with respect to adoption?

参考：无参考答案，应识别证据不足。

- `dynamic`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。The available evidence is insufficient to describe Melanie's plans for the summer regarding adoption. The only relevant evidence is that on 13 October 2023 she said a friend's adoption made her feel like maybe she should adopt too, which indicates tentative consideration rather than a concrete plan, and it says nothing about summer plans. This is only as of the conversation cutoff of 9:55 am on 22 October 2023; no later information is available.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。The available evidence does not establish any summer adoption plans for Melanie. The only adoption-related evidence is a tentative statement from 13 October 2023 in which Melanie says a friend's adoption makes her feel like maybe she should do it too — a vague consideration, not a plan, and not tied to summer. The summer-related evidence from 25 May 2023 concerns her kids being excited about summer break and a possible camping trip, not adoption. No supplied source connects Melanie's adoption consideration to summer, so this remains unknown as of the conversation cutoff (9:55 am on 22 October, 2023).

Known only as of the conversation cutoff (2023-10-22T09:55:00); later reality is unknown.
- `hybrid_no_resolution`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。The supplied evidence is insufficient to state Melanie's plans for the summer regarding adoption. The only adoption-related evidence about Melanie is that on 13 October 2023 she said a buddy adopted last year and that it makes her feel like maybe she should do it too — an uncertain consideration, not a summer plan. Her summer-related evidence concerns a family outing and camping, not adoption. No evidence describes an adoption plan for the summer. This is only as of the conversation cutoff of 9:55 am on 22 October 2023; later developments are unknown.
- `full_text`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}

### QA 157：What does Melanie's necklace symbolize?

参考：无参考答案，应识别证据不足。

- `dynamic`，succeeded / insufficient，QA=0.000，来源覆盖=0.000。The available evidence is insufficient to answer what Melanie's necklace symbolizes. No memories or sources were supplied, so no symbolic meaning can be stated.
- `dynamic_raw_fallback`，succeeded / insufficient，QA=0.000，来源覆盖=1.000。The supplied evidence does not identify a necklace belonging to Melanie or describe what her necklace symbolizes. The only necklace discussed is Caroline's: Melanie compliments it and asks about its meaning, and Caroline says it stands for love, faith, and strength and reminds her of her roots and family support. No supplied evidence establishes a necklace of Melanie's or its symbolism.

Known only as of the conversation cutoff (2023-10-22T09:55:00); later reality is unknown.
- `hybrid_no_resolution`，succeeded / insufficient，QA=0.000，来源覆盖=1.000。The supplied evidence does not describe any necklace belonging to Melanie or what it might symbolize. The only necklace mentioned belongs to Caroline, whose grandmother gave it to her and which she says stands for love, faith, and strength. There is no evidence about a necklace of Melanie's, so its symbolism cannot be determined from the available sources. This answer is limited to the conversation cutoff of 9:55 am on 22 October, 2023.
- `full_text`，failed / None，QA=未评，来源覆盖=未评。{'code': 'invalid_output'}

