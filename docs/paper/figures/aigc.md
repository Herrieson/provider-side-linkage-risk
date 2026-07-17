# Paper Figure Generation Briefs

本文档收录当前论文及补充材料中全部插图的文生图描述。目标不是直接把生成图作为实验
证据，而是让图像模型给出高质量构图、视觉隐喻和配色参考，再使用 Figma、Illustrator、
Inkscape、Keynote 或绘图代码手工重建为矢量图。

当前图清单：

| 编号 | 文件 | 用途 | 版式 |
| --- | --- | --- | --- |
| Figure 1 | `carp_pipeline.pdf` | 正文：Measurement Contract + CARP/ASL 双路径 | 双栏，约 2.2:1 |
| Figure 2 | `results_overview.pdf` | 正文：通道、并发、Agent-state 增益与不可区分性 | 双栏，四联图 |
| Figure 3 | `t3_longitudinal.pdf` | 正文：层次化纵向传播和 watchlist 结果 | 单栏，约 1.54:1 |
| Supplementary Figure | `evidence_layers.pdf` | 补充材料：数据证据层级与研究问题 | 双栏，约 2.33:1 |

## 统一视觉规范

### 视觉方向

- 风格：高水平 AI / security / systems 论文中的现代科学信息图，克制、精确、扁平、矢量化。
- 背景：纯白或接近白色，保证黑白打印和投影展示均清楚。
- 构图：清晰的从左到右或从上到下的阅读路径；装饰服从信息层级。
- 质感：可以精致，但不能像产品营销页、运营仪表盘、海报或科幻概念图。
- 形状：使用几何容器、细线箭头、稀疏图节点、标签、时间线和小型领域图标。
- 圆角：轻微圆角即可，避免大量胶囊、气泡和过度圆润的卡片。
- 阴影：原则上不用；如生成参考需要层次，只允许非常轻的中性投影，手绘时删除。
- 颜色：颜色用于编码语义，而不是装饰。任何关键区别都不能只依赖红绿颜色。

建议沿用现有图的统一色板：

| 角色 | 颜色 |
| --- | --- |
| 主文字 / 节点描边 | `#17212B` |
| 次要文字 / 基线 | `#5B6670` |
| 索引 / 结构信号 | `#2878B5` |
| 跨缓存链接 / 主要方法 | `#2A9D8F` |
| 后续 watchlist / 时间延伸 | `#D99B2B` |
| 冲突、隔离或边界提示 | `#C65353` |
| 浅蓝填充 | `#EAF3FA` |
| 浅青填充 | `#E8F5F2` |
| 浅金填充 | `#FBF2DF` |
| 浅红填充 | `#F9EAEA` |
| 浅灰填充 | `#F2F4F6` |

### 字体与输出

- 字体：Inter、Source Sans 3、Helvetica、Arial 或其他清晰的无衬线字体。
- 字重：标题 semibold，阶段名 medium，说明 regular；不要使用极粗黑体。
- 字号：按最终论文尺寸检查，正文标签不得小于约 7 pt，标题约 9--10 pt。
- 所有文字保持水平，不使用旋转文字；坐标轴标题除外。
- 最终文件必须手工重建为 PDF/SVG，文字保持矢量或嵌入字体。
- 生成参考图建议使用 2048 px 以上长边；最终论文图不要直接使用低分辨率生成图。
- 在 100% 论文显示比例和灰度模式下各检查一次，不允许文字、误差线或标记重叠。

### 通用负面提示词

下面这一段可以附在每个文生图 prompt 后面：

```text
Negative prompt: photorealistic, 3D render, isometric perspective, cyberpunk, neon glow,
dark background, gradient mesh, glassmorphism, glossy UI, marketing dashboard, stock art,
hooded hacker, human faces, robots, padlocks, shields, floating particles, lens flare,
dramatic shadows, excessive rounded cards, decorative blobs, illegible tiny text,
garbled typography, fake logos, watermark, clutter, low contrast, red-green-only encoding,
distorted axes, invented numbers, raster blur.
```

### 使用原则

1. 文生图模型主要负责构图、图标语言和视觉节奏，不负责生成准确文字。
2. 最好要求模型留出文字区域，只保留阶段编号 `1--5`；所有英文标签后期手工覆盖。
3. Figure 2 是定量实验图，生成图只能作为风格参考，不能从生成图读取柱高或数值。
4. 不改变论文当前因果叙事：CARP 负责稀疏发现，ASL 负责 Agent-state 选择性关联。
5. 不把 broker 画成攻击者。攻击者是 honest-but-curious model provider；broker 只做可选的
   protocol-level identifier stripping。

---

## Figure 1: Controlled Measurement Framework and Agent-Native Linkage

### 论文角色

这张图是全文的测量契约和参考攻击总览。它需要在一次扫视中回答五个问题：

1. Broker 做了什么：终止客户端请求并剥离终端调用者标识。
2. 攻击能看到什么：`attack view` 中的明文内容与允许的 upstream telemetry。
3. 攻击看不到什么：`hidden truth` 只在最终评分时解封。
4. 如何做因果归因：paired controls 对可见请求进行移除、改写、并发、轮换或冲突变换。
5. CARP 如何作为参考攻击：五个确定性、受预算约束的稀疏链接步骤。

当前正文 caption：

> Measurement framework and reference attack. The upper lane enforces the threat contract: paired
> controls alter only the provider-visible attack view, attacks cannot read the sealed truth, and
> labels are unsealed only for scoring. The lower lane instantiates the attack with CARP's five
> bounded sparse-linkage steps.

### 推荐构图

使用双栏横向画布，比例约 `2.64:1`，分为上下两条清晰 lane，中间用一条浅灰细线分隔。

#### 上层：Controlled Measurement

从左到右依次画六个节点：

1. `Agent traces`：匿名代码和工具调用请求，不出现人物或真实姓名。
2. `Broker transform`：终止客户端连接、使用 broker 自身 upstream credential，并剥离 caller IDs。
3. `Attack view`：只包含明文 content 与论文允许的 telemetry。
4. `Paired controls`：对路径、上下文、时间、别名和冲突条件进行 remove / perturb。
5. `Linkage methods`：CARP 稀疏发现与 ASL Agent-state 选择性关联。
6. `Score + attribute risk`：输出指标，并判断风险来自 direct exposure、continuity 还是 propagation。

Broker transform 后必须产生一个下方分支 `Hidden truth / labels only`。该框使用红色虚线边框，
不能连接到 paired controls 或 attack；它只通过一条红色弧线进入最终 scoring，并标注
`unsealed only for scoring`。在 attack view 与 hidden truth 之间标注 `attack cannot read`。
这一结构是全图最重要的科学约束，不能只用小锁或脚注代替。

#### 下层：CARP Reference Attack

用五个紧凑阶段框从左到右连接：

1. `Cache-local blocking`：cache 只缩小候选空间，不决定标签。
2. `Typed-anchor indexes`：对 repository/domain、user/email、business object 建立限频倒排索引。
3. `Context candidates`：用 shingle overlap、containment 和 semantic agreement 产生稀疏候选。
4. `Budgeted refinement`：在每请求 pair budget 内过滤歧义边。
5. `Cross-cache propagation`：稳定 handle 跨 cache 连接多个独立伪匿名 component。

底部不再画大型卡片，而用一条文字输出带概括：workflow partitions、task-entity components、
profiles、later-traffic watchlists。上下两层颜色语义一致，但上层强调 measurement contract，
下层才是 CARP 实例，避免让读者误以为整篇论文只是一张算法流水线图。

### 必须手工覆盖的准确文字

```text
Controlled measurement: provider-visible evidence remains separate from linkage truth
Agent traces
Broker transform / strips caller IDs
Attack view / content + allowed telemetry
Hidden truth / labels only
attack cannot read
Paired controls / remove or perturb
Linkage methods
Score + attribute risk
unsealed only for scoring

Two complementary bounded linkage paths
CARP: block + index | context candidates | budgeted refinement | typed-handle propagation
ASL: bounded Agent state | multi-view candidates | support--conflict gate | selective hierarchy
Outputs: workflow partitions | task-entity components | profiles | later-traffic watchlists
```

### 可直接使用的英文文生图 Prompt

```text
Create a publication-quality flat vector systems diagram for an AAAI paper on a white background,
wide 2.64:1 aspect ratio. Use two horizontal lanes separated by one thin light-gray rule.

Upper lane: visualize a controlled provider-side privacy measurement contract. Draw a precise
left-to-right flow with six compact stages: anonymous agent traces; a broker transformation that
strips caller identifiers; a provider-visible attack view containing content and allowed telemetry;
paired controls that remove or perturb evidence; reference attacks and diagnostics; final scoring
and risk attribution. From the broker transformation, branch downward to a separate dashed coral
box for hidden evaluation truth. The hidden-truth box must not connect to the attack or controls.
Route one coral curved arrow directly from hidden truth to final scoring, visually stating that
labels are unsealed only for scoring and that the attack cannot read them.

Lower lane: show CARP as only one bounded reference attack. Draw five numbered compact stages with
thin arrows: cache-local blocking, typed-anchor indexes, context candidates, budgeted refinement,
and cross-cache propagation. Finish with a restrained unframed output line for workflow partitions,
task-entity components, profiles, and later-traffic watchlists.

Make the upper measurement lane visually primary and the lower CARP lane secondary. Do not portray
the broker as the attacker. Do not merge attack view and ground truth. Use restrained scientific
geometry, generous whitespace, 1.3 px strokes, slight corner radii, no gradients or shadows.
Palette: charcoal #17212B, muted gray #5B6670, blue #2878B5, teal #2A9D8F, amber #D99B2B,
coral #C65353, with pale matching fills. Leave clean label zones if text rendering is unreliable.
```

### 手绘时不可改变的科学语义

- Provider 可以看到 broker 自身的 upstream 信息，但不能看到 broker 内部的终端客户映射。
- `attack view` 和 `hidden truth` 必须物理分离；truth 只能进入 scoring。
- Paired controls 作用于 attack view，不能修改或泄漏 scoring labels。
- 五个 CARP 阶段的顺序不能改变，cache metadata 只用于 blocking。
- Stage 3/4 必须表现为稀疏候选，跨缓存传播不能画成一个全局大簇。
- CARP 必须是下层“reference attack”，不能在视觉上覆盖 measurement framework。

---

## Figure 2: T3 Longitudinal Linkage and Watchlist

### 论文角色

这张图是严格的定量结果图，比较三种条件在三个实体层级上的 F1，并同时展示 precision、
recall 和 95% bootstrap interval。它承担的核心叙事是：仅在局部 cache 中冷启动时 recall
很低；稳定 handle 的跨 cache 传播显著提高覆盖；用早期流量建立的 watchlist 还能匹配后续
流量，但结果依赖 controlled T3 overlay 的稳定性。

当前正文 caption：

> T3 F1 bars with 95% intervals; triangles/circles mark precision/recall. T3 uses trace-grounded
> semi-synthetic entity truth.

### 推荐构图

使用单栏横向画布，比例约 `1.64:1`。保持标准 grouped bar chart，不要改成雷达图、面积图、
3D 柱图或插画式数据故事。

- X 轴从左到右：`User`、`Project`、`Organization`。
- 每组严格包含三根等宽柱：灰色 baseline、青色 percolation、金色 watchlist。
- 柱高表示 F1；柱顶上方显示两位小数。
- 青色和金色柱使用黑色细误差线和短 cap；灰色基线没有 bootstrap error bar。
- 空心三角表示 precision，深色实心圆表示 recall。
- Y 轴范围 `0.0--1.0`，步长 `0.2`，只保留浅灰水平网格线。
- 移除顶部和右侧边框；底部和左侧轴线使用深灰细线。
- 图例放在顶部空白区，分两列或三列，不能遮挡 `1.0` 附近的三角形。
- 图内标题简洁，不额外加入机制解释段落。

### 精确数据

生成模型不得自行补值。手绘时按下表设置柱高、误差线和点标记。

| Level | Condition | Precision | Recall | F1 | F1 95% CI |
| --- | --- | ---: | ---: | ---: | --- |
| User | Bucket-local cold start | 0.954 | 0.121 | 0.214 | not shown |
| User | Cross-cache stable-handle linkage | 0.952 | 0.648 | 0.771 | [0.733, 0.805] |
| User | Later-traffic watchlist | 0.950 | 0.557 | 0.702 | [0.675, 0.725] |
| Project | Bucket-local cold start | 1.000 | 0.087 | 0.159 | not shown |
| Project | Cross-cache stable-handle linkage | 0.998 | 0.522 | 0.686 | [0.653, 0.717] |
| Project | Later-traffic watchlist | 1.000 | 0.709 | 0.830 | [0.816, 0.840] |
| Organization | Bucket-local cold start | 1.000 | 0.174 | 0.297 | not shown |
| Organization | Cross-cache stable-handle linkage | 1.000 | 0.635 | 0.777 | [0.756, 0.796] |
| Organization | Later-traffic watchlist | 1.000 | 0.779 | 0.876 | [0.860, 0.891] |

柱顶两位小数标签：

```text
User:          0.21  0.77  0.70
Project:       0.16  0.69  0.83
Organization:  0.30  0.78  0.88
```

### 必须手工覆盖的准确文字

```text
Persistent Handles Enable Longitudinal Linkage

Bucket-local cold start
Cross-cache stable-handle linkage
Later-traffic watchlist
Precision
Recall

Score
User
Project
Organization
Bars: F1; △ precision; ● recall
```

### 可直接使用的英文文生图 Prompt

```text
Create an aesthetic composition reference for a rigorous single-column scientific grouped bar
chart in an AAAI paper, white background, landscape 1.64:1 aspect ratio. The final chart will be
redrawn manually from exact data, so prioritize typography hierarchy, spacing, legend placement,
marker clarity, and publication polish without inventing any data.

Show three evenly spaced x-axis groups: User, Project, Organization. Each group contains exactly
three equal-width bars: muted graphite for bucket-local cold start, teal for cross-cache stable-handle
linkage, and warm amber for a later-traffic watchlist. Use a linear y-axis from 0.0 to 1.0 with thin
light-gray horizontal grid lines every 0.2. Teal and amber bars have thin black 95% interval error
bars with short caps; graphite bars have no interval. Overlay one hollow dark triangle for precision
and one small filled charcoal circle for recall at each bar's x position. Precision markers sit near
the top of the scale, while recall markers explain the F1 differences.

Use a restrained modern scientific style, flat vector geometry, generous margins, no top or right
axis spine, clean sans-serif type, and a compact legend in the upper whitespace that does not cover
markers. Put small two-decimal F1 labels above bars. Palette: graphite #5B6670, teal #2A9D8F,
amber #D99B2B, ink #17212B, grid #D9DEE3. Preserve strong grayscale contrast. Do not use 3D,
gradients, pictograms, dashboard cards, or decorative illustration. Leave all numerical placement
for precise manual reconstruction.
```

### 手绘时不可改变的科学语义

- 柱表示 F1，不是 recall，也不是请求覆盖率。
- 三角是 precision，圆点是 recall，二者不能交换。
- 置信区间只画在 percolation 和 watchlist F1 柱上。
- baseline 的 precision 很高但 recall 很低，这是图中必须保留的关键现象。
- watchlist 使用前 2,500 条请求建立，并仅在后续流量上评估；不要画成训练集拟合结果。
- T3 是 trace-grounded semi-synthetic entity truth，不能用人物、真实公司 logo 或真实客户头像暗示生产身份恢复。
- 图中数值必须来自上表，不得凭 AIGC 输出估读。

---

## Supplementary Figure: Evidence Layers and Dataset Roles

### 论文角色

这张图不在当前 7 页主稿中，而是补充制品。它用一个快速可扫描的证据矩阵告诉读者：
不同数据集提供什么真实 trace substrate、哪些 truth 是可靠的、以及各自支撑论文中的哪类
结论。它的目标是增强实验设计的可信度，而不是把数据集包装成一个新的 benchmark。

### 推荐构图

使用双栏横向画布，比例约 `2.33:1`。采用四列、四行的证据矩阵，但让每一行具有轻量的
领域视觉识别：

- 深色 header 带贯穿顶部，四个列名均匀对齐；
- 每一数据集占一条完整横向色带，列之间只用白色细分隔线；
- 第一列数据集名称可配一个很小的线性图标，但不牺牲文字空间；
- Open-SWE 使用浅蓝，tau-bench historical 使用浅青，hierarchy overlay 使用浅金，
  controlled replay 使用浅红；
- 从上到下视觉上由 natural trace evidence 过渡到 controlled mechanism evidence，但不要
  使用“高到低质量”的箭头，以免把可控实验错误表达为低质量数据；
- 底部放一条不带边框的 claim-scope 注释，使用次要灰色文字。

建议小图标：

- Open-SWE：终端窗口与 repository branch；
- tau-bench historical：工具调用括号与 order / reservation ticket；
- Hierarchy overlay：真实 trace 纸片上叠加一层小型彩色 handle；
- Controlled replay：重标识的公开轨迹与时间轴。

### 精确矩阵内容

| Dataset | Trace substrate | Reliable truth | Paper role |
| --- | --- | --- | --- |
| Open-SWE | Real software-agent traces | workflow, repo, owner-like | Main real-data evidence |
| tau-bench historical | Real tool-agent traces | workflow/session | Non-code external validity |
| Hierarchy overlay | Real traces + controlled overlay | user / tenant / project | Longitudinal mechanism |
| Controlled replay | Re-keyed public traces | known workflow structure | Computation scale |

底部准确说明：

> Claim strength follows the available truth: overlays and synthetic data are mechanism evidence,
> not real identity recovery.

### 可直接使用的英文文生图 Prompt

```text
Create a refined publication-quality flat vector evidence matrix for the supplementary material of
an AI security paper, clean white background, wide 2.33:1 aspect ratio. The figure has four aligned
columns and four dataset rows. Use one continuous dark-charcoal header band with four evenly aligned
column zones. Below it, use four full-width softly colored horizontal rows separated by narrow white
rules, not floating dashboard cards.

The four rows represent: a real software-agent trace dataset in pale blue, a real tool-agent trace
dataset in pale teal, a real-trace plus controlled-overlay dataset in pale amber, and controlled
synthetic traffic in pale coral. Add one very small monoline domain icon at the left of each row:
a terminal plus repository branch, a tool-call bracket plus reservation ticket, a trace sheet with
one overlay tag, and a regular generated node hierarchy. Keep the icons secondary to the table text.

The columns communicate dataset name, trace substrate, reliable ground truth, and role in the paper.
Leave generous horizontal label zones for exact text to be added manually. At the bottom, reserve an
unframed one-line note area explaining that claim strength follows available truth and that overlays
and synthetic data provide mechanism evidence rather than real identity recovery.

Style: precise modern scientific information design, flat vector, subtle 4 px corner radius only at
the outer row boundary, no gradients, no heavy shadows, consistent 1 px separators, clean sans-serif
typography, generous white space. Palette: ink #17212B, pale blue #EAF3FA, pale teal #E8F5F2,
pale amber #FBF2DF, pale coral #F9EAEA, muted note text #5B6670. The figure should feel elegant,
calm, and credible rather than defensive or promotional. Do not render paragraphs of fake text;
leave clean zones for manual labels.
```

### 手绘时不可改变的科学语义

- Open-SWE 的 owner-like truth 不是企业组织身份。
- tau-bench historical 的可靠 truth 主要是 workflow/session；不要擅自填充真实 user/org truth。
- Hierarchy overlay 必须明确保留 `controlled overlay`，不能画成纯真实企业日志。
- Controlled replay 的作用是 computation scale，不是流量代表性证据。
- 四行不是简单的质量排名，而是互补的证据层。
- 该图不应声称论文发布了一个新的 benchmark。

---

## 最终手工重绘检查表

- [ ] 图的文件名和 LaTeX 引用保持不变。
- [ ] Figure 1 在约 6.9 inch 双栏宽度下可读，Figure 2 在约 3.3 inch 单栏宽度下可读。
- [ ] 所有文本均为准确英文，不包含 AIGC 生成的乱码。
- [ ] Figure 2 的柱高、precision、recall 和 CI 与本文档精确数据一致。
- [ ] 颜色在灰度下仍可分辨；必要时给三组柱增加低密度且不抢眼的 hatch。
- [ ] 没有自然人头像、真实公司 logo、hooded hacker、机器人或大锁等安全陈词滥调。
- [ ] 没有把 broker 画成攻击者，也没有把 evaluation truth 画进攻击输入。
- [ ] 没有把 direct exposure 包装成隐式语义推断。
- [ ] 没有把 T3 controlled overlay 表述成真实生产身份恢复。
- [ ] 导出 PDF/SVG 后字体嵌入、无裁切、无重叠、无低分辨率位图。
- [ ] 更新图后重新编译 `docs/overleaf/api.tex`，确认正文不超过 7 页、总页数不超过 9 页且无 overfull box。
