# v6 关系语义独立抽样审计

按当前来源，冻结与完整重建关卡应暂缓。24 项 undetermined 中，23 项可接受，1 项漏掉有支持的 UPDATE。2 项确定关系 control 中，1 项有支持，另 1 项 UPDATE 缺少阶段推进证据。

本次是独立代理逐项核对，不是人工真值。未调用 DeepSeek。判断采用 CONTEXT.md 和 ADR 0001 的操作定义，未用 allowed_labels 或 state_key 代替语义。

样本覆盖四个风险任务，每个任务选 6 项。24 项均跨 state_key；风险抽样不能给出总体错误率，也未覆盖同键冲突与替代的质量。

主要阻塞是 u01 和 c02。u01 的“报名陶艺课 → 在该课产出作品”具有具体过程联系。c02 的“项目已完成 → 详述作品动机”目前没有新阶段。应补最小受控语义用例并核对原文后再决定是否修改提示。

## u01 · relation:73

- 旧 Memory `480d91e2f9e90f04b47fa0af`：Melanie signed up for a pottery class yesterday.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `missed_supported_relation`；建议 `UPDATE`
- 理由：原文先说昨天报名陶艺课，随后对正在展示的碗明确说是在该课做的。报名到上课产出作品是同一学习过程的阶段推进；不同 state_key 不能排除 UPDATE。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D5:4`："I just signed up for a pottery class yesterday."
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u02 · relation:73

- 旧 Memory `ace77a25a90690ed18490261`：Melanie finds pottery class like therapy, letting her express herself and get creative.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：陶艺带来的疗愈和自我表达是活动效果；做出一个碗是具体成果。后者没有明确重申该效果，也没有将效果本身推进到下一阶段。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D5:4`："It's like therapy for me, letting me express myself and get creative."
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u03 · relation:73

- 旧 Memory `b9a5ccd804677b0cdee96f2f`：Melanie is a big fan of pottery.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：喜欢陶艺与做出作品可以并存，但喜欢并非该作品制作过程中的一个明确阶段。做碗也不能单独证明先前的兴趣状态继续适用。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D5:6`："I'm a big fan of pottery"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u04 · relation:73

- 旧 Memory `efc2acb8ae95893ddf1e112a`：Melanie wants to be courageous for her family.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：希望为家人勇敢与在陶艺课做碗没有明确过程联系，原文未把陶艺作品视为该意愿的实现。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D3:10`："I want to be couragous for my family"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u05 · relation:73

- 旧 Memory `f59e2e3288e9d9ff2198a25a`：Melanie had a wedding day where she wore a dress.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：婚礼事件与陶艺作品是两项独立经历，没有保留、推进、替代或矛盾的证据。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D3:17`："You both looked so great on your wedding day!"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u06 · relation:73

- 旧 Memory `25cb2f95868ef76695e0f0c1`：Melanie has been married for 5 years.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：已婚五年与陶艺作品无适用条件或过程联系。作品不确认婚姻状态继续，也不改变婚姻事实。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D3:16`："5 years already!"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## u07 · relation:91

- 旧 Memory `d3e99b6d906b72fff7257d73`：Caroline is creating a library for when she has kids.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：为未来孩子建书库与争取跨性别权益的意愿不同；会议后的发言没有推进或取消育儿准备。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D6:7`："I'm creating a library for when I have kids."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## u08 · relation:91

- 旧 Memory `a8cec9be91860db3646ee08f`：Caroline still thinks counseling and mental health is the career path for her.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：咨询与心理健康职业意向和倡导权益可以共享助人动机；后文没有说已进入该职业的下一阶段，也未确认仍选择该职业。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D5:3`："I'm still thinking that counseling and mental health is the way to go."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:1`："it's shown me how important it is to fight for trans rights and spread awareness."

## u09 · relation:91

- 旧 Memory `e0782e983de28fbcbaf84d47`：Caroline is thinking of working with trans people, helping them accept themselves and supporting their mental health.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：考虑为跨性别人群提供心理支持与权益倡导具有主题联系，但后文未报告求职、训练或开展咨询等职业过程的进展。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D4:13`："I'm thinking of working with trans people, helping them accept themselves and supporting their mental health."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## u10 · relation:91

- 旧 Memory `40fa459584311ebc9c3a2681`：Caroline is passionate about creating a safe, inviting place for people to grow.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：营造安全成长环境的热情与权益倡导意愿可并存；后文仍是宽泛意愿，没有同一具体项目的阶段推进。不能将话题相近直接记 UPDATE。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D4:15`："Now I'm passionate about creating a safe, inviting place for people to grow."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## u11 · relation:91

- 旧 Memory `98e7a1f4e17629630d19c154`：Caroline's own journey and the support she received made a huge difference in her life.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：两处都涉及获得支持后的助人动机，模型所写“no evidence linking them”过强。不过受支持的个人经历到新的宽泛倡导意愿之间，没有明确同一过程的后续阶段证据，未确定仍可接受。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D4:15`："My own journey and the support I got made a huge difference. Now I want to help people go through it too."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## u12 · relation:91

- 旧 Memory `ea75978f077ae0cd1dc3b611`：Caroline went to an LGBTQ+ pride parade last week.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：游行经历与后来的倡导意愿主题相关，但后文明确归因于新近会议和社群，未将早先游行标成同一倡导项目的前阶段。未发现足够的特定过程联系。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D5:1`："Last week I went to an LGBTQ+ pride parade."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:1`："I went to an LGBTQ conference two days ago"

## u13 · relation:148

- 旧 Memory `792b3a6ea07e1cc0f6da9f2b`：Caroline joined a mentorship program for LGBTQ youth last weekend.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：青年导师项目与新加入的活动组织都服务 LGBTQ 社群，但没有证据证明两者是同一组织、同一计划或前后阶段。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:2`："Last weekend I joined a mentorship program for LGBTQ youth"
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## u14 · relation:148

- 旧 Memory `1dd8915638d3bc4ff814518c`：Caroline painted the painting after visiting an LGBTQ center, wanting to capture everyone's unity and strength.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：参观中心后绘画与活动组织成员身份是不同活动，没有表明作品由该组织计划或加入组织推进了该绘画过程。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:16`："I painted this after I visited a LGBTQ center."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## u15 · relation:148

- 旧 Memory `03ac8ae7cc9b795267494740`：Caroline plans to have an LGBTQ art show with her paintings next month.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：计划举办画展与组织成员身份主题相近。原文没有说该组织负责画展，或加入组织代表画展准备进入下一阶段。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:12`："Next month I'm having an LGBTQ art show with my paintings"
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："We have regular meetings, plan events and campaigns"

## u16 · relation:148

- 旧 Memory `c1d17d188491340b6ea4016a`：Caroline is determined to adopt a child.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：收养意愿与权益组织成员身份未建立过程或适用条件联系，组织活动也不证明收养意愿实现。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D8:9`："It made me even more determined to adopt."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## u17 · relation:148

- 旧 Memory `810bba509064a824962cff4c`：Caroline and her mentee had a great time at the LGBT pride event last month.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：与受辅导者参加骄傲活动和组织成员身份没有明确同组织或阶段联系。不能因都属于 LGBTQ 活动而建立 UPDATE。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:6`："We had a great time at the LGBT pride event last month."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## u18 · relation:148

- 旧 Memory `30dea0d02066415795e4e04c`：Caroline attended a pride parade a few weeks ago.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：早先参加游行与后来的活动组织身份可能属于更广泛参与经历，但现有来源没有将其连成同一具体过程。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D8:17`："this pride parade I went to a few weeks ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## u19 · relation:172

- 旧 Memory `b76696c30018cca918a160a9`：Melanie went camping with her family two weekends before 17 July 2023.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：家庭露营与陶艺作品没有具体过程、状态延续或矛盾联系。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:1`："we went camping with my fam two weekends ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## u20 · relation:172

- 旧 Memory `6b664bf5b3931f434fa840d1`：Melanie's wedding day was full of love and joy, with everyone she loves present to celebrate.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：婚礼庆祝的感受与做陶艺作品的动机独立。共同出现快乐、表达等词不足以建立状态关系。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D8:14`："The day was full of love and joy."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## u21 · relation:172

- 旧 Memory `49e43e04899bc8e967037bd8`：Melanie celebrated her daughter's birthday with a concert the night before 14 August 2023.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：为女儿庆生的音乐会与制作陶艺作品是不同活动。让孩子微笑与让观众微笑不是同一具体过程。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D11:1`："We celebrated my daughter's birthday with a concert"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## u22 · relation:172

- 旧 Memory `aff1cf8b21974105565d7fc0`：Melanie went on another camping trip in the forest with her family.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：另一次森林露营与陶艺制作无明确联系，既不证明延续，也不推进或替代。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D8:32`："We even went on another camping trip in the forest."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## u23 · relation:172

- 旧 Memory `d3d5ae3b3f3f8410718157cb`：Melanie had a quiet weekend after going camping with her family two weekends ago.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：露营后的安静周末与后来的陶艺作品无过程或适用条件联系。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D9:1`："I had a quiet weekend after we went camping with my fam two weekends ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## u24 · relation:172

- 旧 Memory `3402011625a483f97bc40d3e`：The concert Melanie attended was by Matt Patterson.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `undetermined`；复核 `reasonable_undetermined`
- 理由：音乐会表演者的身份与陶艺作品是两项独立事实，后文不修改或验证表演者身份。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D11:3`："It was Matt Patterson"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## c01 · relation:148

- 旧 Memory `feafe311934ed4d80915e79a`：Caroline joined a new LGBTQ activist group last Tuesday.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 原判定 `UPDATE`；复核 `supported_control`；建议 `UPDATE`
- 理由：“joined a new LGBTQ activist group”与随后“our group”明确指向同一组织；从加入事件到具名成员及常规活动可支持进入并参与该组织的过程。此支持来自指代和活动内容，不能由同 state_key 单独推得。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D10:3`："I just joined a new LGBTQ activist group last Tues."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists', is made of all kinds of people investing in positive changes. We have regular meetings, plan events and campaigns"

## c02 · relation:172

- 旧 Memory `32a5b80fcfba6f409b45b842`：Melanie finished another pottery project.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 原判定 `UPDATE`；复核 `unsupported_control`
- 理由：D12:2 已明确说项目完成；D12:6 用过去时描述所做作品及制作动机。当前来源未显示另一件新作品或完成后的新阶段，UPDATE 理由擅自加入“then new bowl”。若是同一作品的详述，不符合阶段推进定义。

证据：

- `f69a07a79a2d5f4c8188300a/conv-26/D12:2`："I finished another pottery project"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## 局限

- 24项未确定样本均跨 state_key，来自四个风险任务，每任务6项；不能外推总体漏标率或审核同键替代、冲突判定。
- 这份报告是独立代理复核，不是人工真值或课程评分。
- 只审阅 packet 中 Memory 与 source 原文；已补读同一冻结DB导出的 D5:2 至 D5:9、D12:1 至 D12:7 邻接原文，未审计其余全量对话或全部关系。
- 未运行 DeepSeek，未读取凭据，未修改生产源码或任何数据库。

## 阻塞项补证与现有校验前提

已补读 `/tmp/issue15-v6-audit-context.json` 的邻接原文。u01 的同课指代保持成立。c02 则明确是同一作品的说明链，D12:2 宣告完成，D12:4 展示，D12:5 询问配色，D12:6 解释动机。

- D12:4："Here it is."
- D12:5："That bowl is awesome, Mel! What gave you the idea for all the colors and patterns?"

对 u01 和 c02 分别构造 UPDATE 草稿，以既有 `relation_label_error()` 与 `RelationDraft.model_validate()` 做无模型验证，二者均通过。前提检查没有禁止跨键 UPDATE，两个端点也均为 fact。草稿附两端来源，使用单条原文的连续引句，applicability 留空，不推造日期或条件。

u01 的语义有来源支持。c02 虽然结构校验接受，仍未满足领域定义中的阶段推进，这说明结构校验通过不能证明关系正确。同一会话中后说的一句话也不等于后发生的阶段。
