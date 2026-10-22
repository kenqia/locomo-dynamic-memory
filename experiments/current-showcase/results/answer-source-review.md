# 20条回答的来源语义核验

由当前开发助手逐条核对实际引用和相邻原文，未调用独立LLM评估器，不作为独立人类gold或课程动态准确率。全部20条均保留，不替换低分或保守拒答。

引用身份合法20/20。14条正面回答中，12条有直接或跨来源文本支持，1条为明确保留不确定性的推断，1条仅部分支持；另6条无正面事实断言的拒答单列。

完整性和问答适用性另查：QA51漏sunrise且部分分组超出明确文本；QA69只覆盖一个已支持特征；QA144报告事故结局而非儿子的应对。QA14/59保守拒答丢失官方参考答案允许的推断。

| QA | 来源支持 | 回答适用性 | 核验说明 |
| --- | --- | --- | --- |
| 0 | supported | answers_question | D1:3 says yesterday, anchored to 8 May 2023; 7 May 2023 is supported. |
| 1 | supported | answers_question_verbose | D1:14 explicitly says painted the lake sunrise last year; session is 8 May 2023, supporting 2022. The answer adds unnecessary date explanation, lowering lexical F1. |
| 3 | supported | answers_question | D2:8 explicitly states researching adoption agencies, spoken by Caroline. |
| 11 | supported | answers_question | D3:13 connects four years to moving from her home country; D4:3 identifies that country as Sweden. Both sources concern Caroline. |
| 14 | no_positive_claim | conservative_refusal_gold_mismatch | No unsupported positive assertion. The counterfactual is not directly established; official gold permits a likely inference. Refusal therefore scores zero and is not counted as successful factual answering. |
| 22 | qualified_inference | answers_question_with_uncertainty | D6:9 supports owning children's classics, not actual Dr. Seuss possession. Answer says likely/plausibly and explicitly notes no title is named; preserve this as qualified inference rather than a directly verified fact. |
| 45 | supported | answers_question | D11:4 says last Friday, relative to Monday 14 August 2023, yielding Friday 11 August. |
| 51 | partially_supported | incomplete | Horse, sunset inspiration, joint nature painting and abstract work have explicit cited support. The singular landscape/still-life nature painting combines favorite painting genres with a displayed work rather than an explicit textual description of that particular work. Sunrise from D1:14 is omitted. Do not label the whole list fully supported and complete. |
| 59 | no_positive_claim | conservative_refusal_gold_mismatch | No unsupported assertion of religious identity. Religious symbols and destiny-related remarks permit the official tentative gold but do not state a definite identity. Record the refusal and lost QA coverage separately. |
| 60 | supported | answers_question | Melanie explicitly plays clarinet in D15:26 and her violin in D2:5; both items are present. |
| 68 | supported | answers_question_lexical_mismatch | D16:8 states Seven years now on 13 September 2023. Seven years answers duration directly; official gold Since 2016 is lexically different. No exact start day should be invented. |
| 69 | supported | incomplete | D8:26 is Melanie explicitly praising Caroline's courage to be herself. The selected trait is supported, but the answer does not cover the broader thoughtful/authentic/driven reference set. |
| 102 | supported | answers_question | D6:9 explicitly lists children's classics, stories from different cultures and educational books. D6:7 gives future-library context; answer does not claim completed parenthood. |
| 130 | supported | answers_question | D15:28 names Bach and Mozart as classical music Melanie likes. |
| 144 | supported | off_target | D18:1 and D18:3 support the son being okay after the accident, but the answer reports outcome rather than how he handled it. It misses fear and family reassurance. Legal, factually grounded citations do not make this a complete answer. |
| 148 | supported | answers_question | D18:5 explicitly says Thankfully, they enjoyed the Grand Canyon a lot. Thankful/relieved is a reasonable contextual paraphrase; do not infer additional reactions. |
| 152 | no_positive_claim | appropriate_refusal | The charity race realization belongs to Melanie, not Caroline. Refusal preserves speaker identity. |
| 176 | no_positive_claim | appropriate_refusal | The meteor-shower experience is Melanie's. Caroline's reaction to the story is not her own experience while watching. |
| 182 | no_positive_claim | appropriate_refusal | No text supports Melanie finding something in her neighborhood on a walk; do not transfer Caroline's source claim. |
| 187 | no_positive_claim | appropriate_refusal | Sources mention a serious cafe sign and call it a precaution, but its actual contents are not described in available text. The answer does not invent image content. |

确切答案、Trace ID、来源ID及答案摘要见answer-source-review.json；完整引用原文及邻轮见answer-source-packets.json。
