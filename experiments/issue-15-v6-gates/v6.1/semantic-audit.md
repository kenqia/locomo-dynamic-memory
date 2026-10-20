# v6.1 关系语义抽样复核

第5关暂不通过。30项中28项符合预审可接受标签，2项 UPDATE 不受来源支持。新增真实调用0次，报告不构成人工真值。

关系73的报名陶艺课到在该课做出作品已正确改为 UPDATE。关系148与172仍把同一成员身份的具名说明、同一已完成作品的详述当作新阶段。四项额外同键对照符合预审期望，分别为2项 undetermined 和2项 RETAIN。

更正痕迹：首次独立审计曾接受原 c01，即 relation:148 的 UPDATE。按与 relation:172 一致的标准重读后，撤回该接受结论；原报告保留，修订依据另存 controls-reassessment.json。加入事件已经建立成员身份，随后给组织命名并不自动产生下一阶段。

UPDATE 必须有来源支持的同一过程、两个可区分的现实阶段及其先后。后说、名称更具体、补充属性、event转state编码、解释已完成作品均不单独建立新阶段。

两项详述control在读取完整结果前预设的可接受集合为 RETAIN 或 undetermined，首选 RETAIN，二者须明确理由。模型给出的 UPDATE 不在此集合。

## v61-01 · relation:73

- 旧 Memory `efc2acb8ae95893ddf1e112a`：Melanie wants to be courageous for her family.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：希望为家人勇敢与在陶艺课做碗没有明确过程联系，原文未把陶艺作品视为该意愿的实现。

- `f69a07a79a2d5f4c8188300a/conv-26/D3:10`："I want to be couragous for my family"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-02 · relation:73

- 旧 Memory `25cb2f95868ef76695e0f0c1`：Melanie has been married for 5 years.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：已婚五年与陶艺作品无适用条件或过程联系。作品不确认婚姻状态继续，也不改变婚姻事实。

- `f69a07a79a2d5f4c8188300a/conv-26/D3:16`："5 years already!"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-03 · relation:73

- 旧 Memory `f59e2e3288e9d9ff2198a25a`：Melanie had a wedding day where she wore a dress.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：婚礼事件与陶艺作品是两项独立经历，没有保留、推进、替代或矛盾的证据。

- `f69a07a79a2d5f4c8188300a/conv-26/D3:17`："You both looked so great on your wedding day!"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-04 · relation:73

- 旧 Memory `480d91e2f9e90f04b47fa0af`：Melanie signed up for a pottery class yesterday.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `UPDATE`；可接受标签 `UPDATE`；复核 `supported_relation`。
- 理由：原文先说昨天报名陶艺课，随后对正在展示的碗明确说是在该课做的。报名到上课产出作品是同一学习过程的阶段推进；不同 state_key 不能排除 UPDATE。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:4`："I just signed up for a pottery class yesterday."
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-05 · relation:73

- 旧 Memory `ace77a25a90690ed18490261`：Melanie finds pottery class like therapy, letting her express herself and get creative.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：陶艺带来的疗愈和自我表达是活动效果；做出一个碗是具体成果。后者没有明确重申该效果，也没有将效果本身推进到下一阶段。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:4`："It's like therapy for me, letting me express myself and get creative."
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-06 · relation:73

- 旧 Memory `b9a5ccd804677b0cdee96f2f`：Melanie is a big fan of pottery.
- 新 Memory `6238c781aa4e813acfed882f`：Melanie made a black and white bowl in her pottery class.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：喜欢陶艺与做出作品可以并存，但喜欢并非该作品制作过程中的一个明确阶段。做碗也不能单独证明先前的兴趣状态继续适用。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:6`："I'm a big fan of pottery"
- `f69a07a79a2d5f4c8188300a/conv-26/D5:8`："Yeah, I made this bowl in my class."

## v61-07 · relation:91

- 旧 Memory `e0782e983de28fbcbaf84d47`：Caroline is thinking of working with trans people, helping them accept themselves and supporting their mental health.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：考虑为跨性别人群提供心理支持与权益倡导具有主题联系，但后文未报告求职、训练或开展咨询等职业过程的进展。

- `f69a07a79a2d5f4c8188300a/conv-26/D4:13`："I'm thinking of working with trans people, helping them accept themselves and supporting their mental health."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## v61-08 · relation:91

- 旧 Memory `98e7a1f4e17629630d19c154`：Caroline's own journey and the support she received made a huge difference in her life.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：两处都涉及获得支持后的助人动机，模型所写“no evidence linking them”过强。不过受支持的个人经历到新的宽泛倡导意愿之间，没有明确同一过程的后续阶段证据，未确定仍可接受。

- `f69a07a79a2d5f4c8188300a/conv-26/D4:15`："My own journey and the support I got made a huge difference. Now I want to help people go through it too."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## v61-09 · relation:91

- 旧 Memory `40fa459584311ebc9c3a2681`：Caroline is passionate about creating a safe, inviting place for people to grow.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：营造安全成长环境的热情与权益倡导意愿可并存；后文仍是宽泛意愿，没有同一具体项目的阶段推进。不能将话题相近直接记 UPDATE。

- `f69a07a79a2d5f4c8188300a/conv-26/D4:15`："Now I'm passionate about creating a safe, inviting place for people to grow."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## v61-10 · relation:91

- 旧 Memory `ea75978f077ae0cd1dc3b611`：Caroline went to an LGBTQ+ pride parade last week.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：游行经历与后来的倡导意愿主题相关，但后文明确归因于新近会议和社群，未将早先游行标成同一倡导项目的前阶段。未发现足够的特定过程联系。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:1`："Last week I went to an LGBTQ+ pride parade."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:1`："I went to an LGBTQ conference two days ago"

## v61-11 · relation:91

- 旧 Memory `a8cec9be91860db3646ee08f`：Caroline still thinks counseling and mental health is the career path for her.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：咨询与心理健康职业意向和倡导权益可以共享助人动机；后文没有说已进入该职业的下一阶段，也未确认仍选择该职业。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:3`："I'm still thinking that counseling and mental health is the way to go."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:1`："it's shown me how important it is to fight for trans rights and spread awareness."

## v61-12 · relation:91

- 旧 Memory `d3e99b6d906b72fff7257d73`：Caroline is creating a library for when she has kids.
- 新 Memory `1a4534c2816be2a913dd5d0a`：Caroline wants to help make a difference in fighting for trans rights and spreading awareness.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：为未来孩子建书库与争取跨性别权益的意愿不同；会议后的发言没有推进或取消育儿准备。

- `f69a07a79a2d5f4c8188300a/conv-26/D6:7`："I'm creating a library for when I have kids."
- `f69a07a79a2d5f4c8188300a/conv-26/D7:3`："I wanna help make a difference."

## v61-13 · relation:148

- 旧 Memory `c1d17d188491340b6ea4016a`：Caroline is determined to adopt a child.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：收养意愿与权益组织成员身份未建立过程或适用条件联系，组织活动也不证明收养意愿实现。

- `f69a07a79a2d5f4c8188300a/conv-26/D8:9`："It made me even more determined to adopt."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-14 · relation:148

- 旧 Memory `30dea0d02066415795e4e04c`：Caroline attended a pride parade a few weeks ago.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：早先参加游行与后来的活动组织身份可能属于更广泛参与经历，但现有来源没有将其连成同一具体过程。

- `f69a07a79a2d5f4c8188300a/conv-26/D8:17`："this pride parade I went to a few weeks ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-15 · relation:148

- 旧 Memory `792b3a6ea07e1cc0f6da9f2b`：Caroline joined a mentorship program for LGBTQ youth last weekend.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：青年导师项目与新加入的活动组织都服务 LGBTQ 社群，但没有证据证明两者是同一组织、同一计划或前后阶段。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:2`："Last weekend I joined a mentorship program for LGBTQ youth"
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-16 · relation:148

- 旧 Memory `810bba509064a824962cff4c`：Caroline and her mentee had a great time at the LGBT pride event last month.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：与受辅导者参加骄傲活动和组织成员身份没有明确同组织或阶段联系。不能因都属于 LGBTQ 活动而建立 UPDATE。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:6`："We had a great time at the LGBT pride event last month."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-17 · relation:148

- 旧 Memory `03ac8ae7cc9b795267494740`：Caroline plans to have an LGBTQ art show with her paintings next month.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：计划举办画展与组织成员身份主题相近。原文没有说该组织负责画展，或加入组织代表画展准备进入下一阶段。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:12`："Next month I'm having an LGBTQ art show with my paintings"
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："We have regular meetings, plan events and campaigns"

## v61-18 · relation:148

- 旧 Memory `1dd8915638d3bc4ff814518c`：Caroline painted the painting after visiting an LGBTQ center, wanting to capture everyone's unity and strength.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：参观中心后绘画与活动组织成员身份是不同活动，没有表明作品由该组织计划或加入组织推进了该绘画过程。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:16`："I painted this after I visited a LGBTQ center."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-19 · relation:148

- 旧 Memory `feafe311934ed4d80915e79a`：Caroline joined a new LGBTQ activist group last Tuesday.
- 新 Memory `20674ca1f268fb05625dedfa`：Caroline is a member of the group 'Connected LGBTQ Activists'.
- 模型 `UPDATE`；可接受标签 `RETAIN, undetermined`；复核 `unsupported_relation`。
- 理由：D10:3 的加入事件已经建立成员身份，且同一句已描述正在认识成员与参与。D10:5 通过 our group 补充名称和常规活动，未显示其后发生新的阶段。加入事件与成员状态的 event/state 编码差异本身也不是现实过程的新阶段。

- `f69a07a79a2d5f4c8188300a/conv-26/D10:3`："I just joined a new LGBTQ activist group last Tues."
- `f69a07a79a2d5f4c8188300a/conv-26/D10:3`："I'm meeting so many cool people"
- `f69a07a79a2d5f4c8188300a/conv-26/D10:5`："Our group, 'Connected LGBTQ Activists'"

## v61-20 · relation:172

- 旧 Memory `6b664bf5b3931f434fa840d1`：Melanie's wedding day was full of love and joy, with everyone she loves present to celebrate.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：婚礼庆祝的感受与做陶艺作品的动机独立。共同出现快乐、表达等词不足以建立状态关系。

- `f69a07a79a2d5f4c8188300a/conv-26/D8:14`："The day was full of love and joy."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-21 · relation:172

- 旧 Memory `aff1cf8b21974105565d7fc0`：Melanie went on another camping trip in the forest with her family.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：另一次森林露营与陶艺制作无明确联系，既不证明延续，也不推进或替代。

- `f69a07a79a2d5f4c8188300a/conv-26/D8:32`："We even went on another camping trip in the forest."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-22 · relation:172

- 旧 Memory `d3d5ae3b3f3f8410718157cb`：Melanie had a quiet weekend after going camping with her family two weekends ago.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：露营后的安静周末与后来的陶艺作品无过程或适用条件联系。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:1`："I had a quiet weekend after we went camping with my fam two weekends ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-23 · relation:172

- 旧 Memory `b76696c30018cca918a160a9`：Melanie went camping with her family two weekends before 17 July 2023.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：家庭露营与陶艺作品没有具体过程、状态延续或矛盾联系。

- `f69a07a79a2d5f4c8188300a/conv-26/D9:1`："we went camping with my fam two weekends ago."
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-24 · relation:172

- 旧 Memory `49e43e04899bc8e967037bd8`：Melanie celebrated her daughter's birthday with a concert the night before 14 August 2023.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：为女儿庆生的音乐会与制作陶艺作品是不同活动。让孩子微笑与让观众微笑不是同一具体过程。

- `f69a07a79a2d5f4c8188300a/conv-26/D11:1`："We celebrated my daughter's birthday with a concert"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-25 · relation:172

- 旧 Memory `3402011625a483f97bc40d3e`：The concert Melanie attended was by Matt Patterson.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：音乐会表演者的身份与陶艺作品是两项独立事实，后文不修改或验证表演者身份。

- `f69a07a79a2d5f4c8188300a/conv-26/D11:3`："It was Matt Patterson"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-26 · relation:172

- 旧 Memory `32a5b80fcfba6f409b45b842`：Melanie finished another pottery project.
- 新 Memory `fdd1ba084c0100474dbf66b3`：Melanie made a bowl with colors and patterns to catch the eye and make people smile.
- 模型 `UPDATE`；可接受标签 `RETAIN, undetermined`；复核 `unsupported_relation`。
- 理由：D12:2 已完成项目；D12:4 展示同一项目，D12:5 问配色，D12:6 解释制作动机。后说的作品细节没有发生在项目完成之后的新阶段。

- `f69a07a79a2d5f4c8188300a/conv-26/D12:2`："I finished another pottery project"
- `f69a07a79a2d5f4c8188300a/conv-26/D12:6`："I made something to catch the eye and make people smile."

## v61-27 · relation:31

- 旧 Memory `04d691cc6e211e79cc0700fc`：Caroline is feeling hopeful and optimistic about the adoption process.
- 新 Memory `421e00bab892b9e79dd9b35a`：Caroline felt super powerful giving her talk.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：收养过程中的希望、乐观与演讲时的强大感属于不同事件条件下的感受。两者能并存；没有证据说明后者替代前者、保持前者，或构成同一过程的新阶段。同键 emotional_state 过于宽泛，不能据此制造关系。

- `f69a07a79a2d5f4c8188300a/conv-26/D2:10`："I'm feeling hopeful and optimistic."
- `f69a07a79a2d5f4c8188300a/conv-26/D3:3`："I felt super powerful giving my talk."

## v61-28 · relation:31

- 旧 Memory `7140560fa6eac1c93cd6d4b9`：Caroline is thrilled to make a family for kids who need one.
- 新 Memory `421e00bab892b9e79dd9b35a`：Caroline felt super powerful giving her talk.
- 模型 `undetermined`；可接受标签 `undetermined`；复核 `reasonable_undetermined`。
- 理由：为需要家庭的孩子组建家庭而兴奋，与演讲时的强大感有不同诱因。后文未提收养，没有延续、替代或冲突证据；不能仅依后说的情绪替换先前情绪。

- `f69a07a79a2d5f4c8188300a/conv-26/D2:14`："I'm thrilled to make a family for kids who need one."
- `f69a07a79a2d5f4c8188300a/conv-26/D3:3`："I felt super powerful giving my talk."

## v61-29 · relation:76

- 旧 Memory `69299a7bd9cfc5dcb916dc38`：Caroline has been looking into counseling and mental health as a career.
- 新 Memory `8c3fb2d3e5167026633668ca`：Caroline has been looking into counseling or mental health work.
- 模型 `RETAIN`；可接受标签 `RETAIN`；复核 `supported_relation`。
- 理由：新来源明确说自上次交流后还在进一步了解咨询或心理健康工作，为此前职业探索持续提供正面证据。more 表示继续探索，未陈述申请、培训、入职等可区分的新阶段，因此首选 RETAIN。and/or 的措辞变化不证明旧值遭替代或矛盾。

- `f69a07a79a2d5f4c8188300a/conv-26/D4:11`："I've been looking into counseling and mental health as a career."
- `f69a07a79a2d5f4c8188300a/conv-26/D6:3`："Since our last chat, I've been looking into counseling or mental health work more."

## v61-30 · relation:76

- 旧 Memory `a8cec9be91860db3646ee08f`：Caroline still thinks counseling and mental health is the career path for her.
- 新 Memory `8c3fb2d3e5167026633668ca`：Caroline has been looking into counseling or mental health work.
- 模型 `RETAIN`；可接受标签 `RETAIN`；复核 `supported_relation`。
- 理由：旧来源说仍认为咨询与心理健康是职业方向，新来源明确在继续探索这一工作方向，支持该兴趣在当前职业探索语境继续适用。未声称职业已实现，也未进入明确下一阶段，故首选 RETAIN，不因 more 就记 UPDATE。

- `f69a07a79a2d5f4c8188300a/conv-26/D5:3`："I'm still thinking that counseling and mental health is the way to go."
- `f69a07a79a2d5f4c8188300a/conv-26/D6:3`："Since our last chat, I've been looking into counseling or mental health work more."

## 局限

- 样本为定向风险抽样，24项原未确定对照均跨key，另加2项control及4项同键对照；不能估计全库准确率。
- 独立代理复核不是人工真值或课程评分。
- 两项重复/详述control预设可接受集合为RETAIN或undetermined，首选RETAIN；本次模型输出UPDATE不在集合内。
- 同键样本没有充分覆盖真实SUPERSEDE或CONFLICT场景。
- 新增真实调用0次；未改源码或数据库。
