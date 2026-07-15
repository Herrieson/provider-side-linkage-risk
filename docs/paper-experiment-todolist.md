# 论文实验 TodoList

本文档是论文实验的主任务清单，用来把当前 MVP 代码、已有结果和后续论文级实验串起来。目标不是只证明 demo 能跑通，而是形成一套可以写进论文的证据链：

```text
Threat model -> datasets -> attack -> ablation -> profile reconstruction -> mitigation -> reporting
```

更重要的是：本文档从一开始就把类似工作常见的实验弊病前置为设计约束。所有实验默认先通过数据真实性、攻击视图隔离、修复字段隔离、消融可解释性、复现实验和备用路线检查，再进入论文主表。

## -1. 先验风险控制原则

### 核心原则

- [ ] **真实数据优先**：论文主结果不能只依赖 synthetic Dataset A。Dataset A 只能用于 sanity check、可控变量实验和机制解释。
- [ ] **raw-first**：所有 real-repo 数据必须先报告 raw/no-repair 结果，再报告 repaired/deployment-variant 结果。
- [ ] **provider-view first**：每个数据集先做 provider-visible field audit，确认 `attack_view.jsonl` 不包含 ground truth、source provenance、repair metadata。
- [ ] **truth 隔离**：任何攻击、特征提取、画像恢复都不得读取 `ground_truth.jsonl`、`request_provenance.jsonl`、manifest 中的标签字段。
- [ ] **修复字段分层**：新增 timestamp、workspace、repository、synthetic secret 等字段必须标记为 repair，不能和原始 evidence 混写。
- [ ] **claim 分层**：session、project/repo、owner/org、enterprise identity、user identity 必须分开报告，不允许把 GitHub owner 直接写成企业组织。
- [ ] **negative controls**：必须包含 random、temporal、tool/schema、rare、prefix 等低能力或单信号基线，避免 hybrid 结果没有参照。
- [ ] **ablation-first explanation**：主攻击结果之后必须马上给 feature ablation，说明成功来自什么信号，而不是只给高 F1。
- [ ] **pre-registered metrics**：主指标和主数据集组合在跑大规模结果前固定，避免只挑好看的表。
- [ ] **失败也保留**：如果某个数据源、split、scaffold 上攻击失败，保留结果并解释边界，不删除不利证据。
- [ ] **utility 不缺席**：防御实验不能只报告攻击下降，还要报告 token/message 保留、延迟、上下文截断、任务质量代理指标。
- [ ] **伦理和许可先行**：所有真实数据源必须记录 license、可再分发限制、PII 处理策略和是否包含用户身份。
- [ ] **可复现优先**：每个实验输出 config snapshot、dataset manifest、command、git commit、row counts、skipped counts。

### 常见弊病与预防机制

| 潜在弊病 | 风险 | 一开始的预防机制 | 论文中如何表述 |
| --- | --- | --- | --- |
| 只用合成数据 | 审稿人会认为结果是模板生成器产物 | 论文主表必须包含 real-repo agent trajectory；合成数据只做控制实验 | “Controlled synthetic benchmark” 而不是主证据 |
| 把标签加入 attack view | 会变成证明自己加入的标签可恢复 | provider-view audit；禁止 source/provenance/repair fields 进入 attack view | 每个数据集报告 non-provider fields |
| repaired context 造成假阳性 | repository/workspace 是我们加的，不是原始日志 | raw/no-repair 先跑；repair 只作为 deployment variant/upper bound | 表格显式标 `repair_mode` |
| 过度解释 org | GitHub owner 不等于企业组织 | project/repo、owner/org、enterprise identity 分开 | 使用 “repo owner/organization-like owner” |
| user ground truth 不可靠 | 错误 user-level F1 | user unavailable 时跳过 user scoring | 明确 N/A，不用 0 或猜测标签 |
| 小样本 cherry-pick | 100 条样本结果不稳 | 1,000+ trajectories；跨 split/scaffold 重复；保留失败结果 | 报告 source diversity 和 sample sweep |
| heuristic 阈值过拟合 | 固定阈值只适合当前样本 | threshold sweep；holdout split；参数进 config | 报告曲线而不是单点 |
| 缺少消融 | 不知道攻击成功原因 | no-path/no-repo/no-context/no-tool/no-time 等消融 | 主结果后紧跟 ablation table |
| 缺少 negative controls | hybrid 高分不说明问题 | random、same-size random、temporal、single-signal baselines | 低成本/单信号/混合信号对比 |
| 防御只打当前攻击 | 不能声称解决隐私问题 | 多攻击、多信号、多 redaction variant；报告 residual leakage | 使用“reduces current attack”而不是“solves” |
| 防御不可用 | 安全了但任务做不了 | token/message retention、tool clipping、task success proxy | utility/privacy tradeoff |
| profile 由聚类真值偷看 | profile 结果不真实 | predicted-cluster profile 和 truth-cluster upper bound 分开 | 一个是攻击效果，一个是画像器上限 |
| 真实数据含 PII | 伦理和许可风险 | 不发布原文敏感片段；hash user；只发布 derived metrics | 写 ethics/data handling |
| 成本/规模不可复现 | 大规模跑不动 | runtime table；sample-size sweep；缓存中间特征 | 报告 compute budget |
| active attack 混入 passive setting | 威胁模型不清 | 主实验固定 A0 passive；A1 active 单独附录 | 不混表 |

### 实验准入门槛

任何进入论文主表的实验必须满足：

- [ ] 有 dataset manifest。
- [ ] 有 provider-view audit。
- [ ] 有明确 `repair_mode`。
- [ ] 有明确 ground truth levels：session/project/org/user 是否可靠。
- [ ] 有至少 3 个非 hybrid baseline。
- [ ] 有 row counts、cluster counts、skipped counts。
- [ ] 有 seed 和 config snapshot。
- [ ] 有失败/异常样本记录。

## -0. 分支路线和 Plan B

本文论文路线不能只押注一条数据或一个 claim。下面定义主线、分支和触发条件。

### 主线 A: Real-Repo Agent Trajectory Attack

目标：

```text
Open-SWE-Traces raw/no-repair
-> session/project/owner-level reconstruction
-> feature ablation
-> profile extraction
-> mitigation tradeoff
```

成立条件：

- [ ] 1,000 trajectory raw sample 上 hybrid 明显优于 temporal/tool/random baseline。
- [ ] no-workspace-path ablation 后 session-level 仍有可观恢复，或能明确量化 workspace/path 是主要泄漏源。
- [ ] 至少两个 scaffold/split 上趋势一致。
- [ ] project/repo 和 owner/org 分层报告后仍有可解释结果。

如果成立，论文主张：

> LLM Agent API 明文上下文中的工作目录、工具输出、上下文重叠、repo/service artifacts 等内容侧信号，足以在匿名 broker 场景下重建 real-repo agent workflows，并恢复有用的项目/组织级画像线索。

### Plan B1: Open-SWE 原始路径信号过强，导致结果像 workspace artifact

触发条件：

- [ ] raw 结果很高，但 no-workspace-path/no-path ablation 后 session/project/org F1 大幅下降到接近 baseline。

转向：

- [ ] 将论文主贡献改为 “Agent workspace/tool-output leakage measurement”。
- [ ] 重点分析 path/workspace/repo artifacts 在真实 agent traces 中出现的频率、位置和影响。
- [ ] 防御主线转为 path minimization、workspace pseudonymization、tool-output clipping。
- [ ] 保留原攻击作为风险展示，不声称上下文语义本身足够。

Plan B1 论文题眼：

> Agent traces routinely expose stable workspace and repository artifacts; anonymity fails unless clients minimize or pseudonymize tool-visible environment context.

### Plan B2: Open-SWE 结果 scaffold-specific

触发条件：

- [ ] `openhands/*` 高分，但 `sweagent/*` 明显低分，或反之。

转向：

- [ ] 把 scaffold 作为研究变量，而不是失败。
- [ ] 分析不同 agent framework 的 tool schema、message shape、workspace convention、context carryover 差异。
- [ ] 论文主张改为 “Agent scaffold design materially changes linkability risk”。
- [ ] mitigation 变成 scaffold-level design recommendations。

Plan B2 论文题眼：

> Linkability is not only a data property; it is shaped by agent scaffold conventions.

### Plan B3: Open-SWE 不足以支持 profile reconstruction

触发条件：

- [ ] workflow/project 能恢复，但 profile truth 只有 language/repo，无法支撑组织画像。

转向：

- [ ] 画像实验只在 synthetic + SWE-bench/Claw-SWE repaired workflows 上做。
- [ ] Open-SWE 作为 workflow reconstruction 主证据。
- [ ] 将 profile claim 降级为 “technical profile clues” 而不是完整 organization profile。
- [ ] 明确真实企业画像是 external validity limitation。

Plan B3 论文题眼：

> Workflow reconstruction is strongly supported on real-repo traces; richer profile reconstruction requires datasets with richer, ethically usable profile labels.

### Plan B4: Open-SWE 数据源访问、规模或许可受阻

触发条件：

- [ ] Hugging Face 下载/streaming 不稳定。
- [ ] 大规模样本无法稳定复现。
- [ ] license 或发布 derived dataset 存疑。

转向：

- [ ] 用 SWE-bench / SWE-bench Lite 构造 repaired workflows。
- [ ] 用 Claw-SWE-Bench 作为小型 fast validation。
- [ ] 用 DevGPT/WildChat 作为 dialogue-style supplement。
- [ ] 使用 GH Archive 只做 timing/noise model，不做内容主证据。

Plan B4 论文题眼：

> Even when full trajectories are unavailable, real issue/patch/test artifacts can produce reproducible agent-like API logs for linkability evaluation.

### Plan B5: 攻击强度不足，无法支持 de-anonymization 主张

触发条件：

- [ ] 在 raw real-repo 数据上 hybrid 只略优于 baseline。
- [ ] 消融后没有稳定主要信号。

转向：

- [ ] 把论文改成 benchmark/measurement paper：定义 threat model、数据契约、评估协议和负结果。
- [ ] 强调哪些匿名 broker 设定有效，哪些 Agent context 设计降低风险。
- [ ] 引入 warm-start 作为扩展，而不是主设定。

Plan B5 论文题眼：

> Under strict cold-start and provider-view constraints, linkability is bounded; the paper provides a benchmark and negative evidence for safer agent API design.

### Plan B6: Defense 很有效但 utility 无法接受

触发条件：

- [ ] M2/M3/M6 降低攻击，但 token/message retention 太低，或 task success proxy 明显不可接受。

转向：

- [ ] 不推荐单一强防御。
- [ ] 改为分级防御矩阵：低敏任务、代码任务、安全任务、企业任务分别采用不同策略。
- [ ] 强调 privacy/utility frontier。

Plan B6 论文题眼：

> Effective mitigation requires selective minimization, not blanket redaction.

### Plan B7: 成本过高，无法跑完整矩阵

触发条件：

- [ ] 5,000+ trajectories 或 embedding baseline 运行成本过高。

转向：

- [ ] 固定 1,000 trajectory 主表。
- [ ] 用 100/500/1,000 sample-size sweep 展示趋势。
- [ ] 将 embedding baseline 放附录或小样本。
- [ ] 优先运行低成本启发式 baselines 和 ablations。

Plan B7 论文题眼：

> Low-cost provider-side signals already provide meaningful linkability; expensive embeddings are not required for the main risk.

### 决策门

| Gate | 时间点 | 通过条件 | 不通过则切换 |
| --- | --- | --- | --- |
| G0 数据审计门 | 每个数据集导入后 | provider-view clean；ground truth levels 明确 | 修 importer 或降级数据集 |
| G1 raw evidence 门 | Open-SWE 1,000 后 | hybrid 显著优于 baseline | B1/B2/B5 |
| G2 消融门 | feature ablation 后 | 至少一个非标签、非修复主信号成立 | B1/B5 |
| G3 source diversity 门 | 多 split/scaffold 后 | 趋势跨来源不矛盾 | B2 |
| G4 profile 门 | profile truth 扩展后 | L2-L4 字段有证据覆盖 | B3 |
| G5 defense 门 | 防御矩阵后 | 有可接受 utility/privacy tradeoff | B6 |
| G6 scale 门 | 大规模实验后 | 结果可复现且成本可报告 | B7 |

## 0. 当前进度快照

### 已完成

- [x] 明确主威胁模型：`D1 + A0 + cold-start`，即匿名 broker 隐藏显式身份，模型提供商只做被动离线日志分析。
- [x] 完成合成 Dataset A 的生成器，包含 org/user/project/workflow/turn/profile truth。
- [x] 定义攻击者可见的 `attack_view.jsonl` 和评估用 `ground_truth.jsonl`。
- [x] 实现 5 类聚类攻击：`temporal`、`rare`、`prefix`、`tool`、`hybrid`。
- [x] 实现基础内容特征提取：path、username、domain、trace、repo id、shingles、tool schema fingerprint、system prompt fingerprint、timestamp、token count。
- [x] 实现 6 类防御变换：`M0`、`M1`、`M2`、`M3`、`M4`、`M6`。
- [x] 实现 session/user/project/org 聚类评估：pairwise precision/recall/F1、purity、split rate、merge rate。
- [x] 实现规则画像恢复和画像字段 precision/recall/F1。
- [x] 完成合成 MVP 实验，规模为 20 org、100 users、60 projects、18,400 requests。
- [x] 完成 Open-SWE-Traces importer，支持本地文件和 Hugging Face rows API fallback。
- [x] 将 Open-SWE-Traces 转换为 provider-visible `attack_view.jsonl`、`ground_truth.jsonl`、`request_provenance.jsonl`。
- [x] 完成 Open-SWE-Traces 100 trajectory raw sample 的导入、审计和 M0 attack-only 评估。
- [x] 完成 Open-SWE-Traces 1,000 trajectory raw sample 的导入和审计。
- [x] 完成 Open-SWE-Traces 1,000 final-turn project/owner probe。
- [x] 完成 Open-SWE-Traces 1,000 turns `3 6 9 12` session probe。
- [x] 完成 Open-SWE-Traces no-workspace-path ablation。
- [x] 完成 Open-SWE-Traces turn-delta ablation，确认累计上下文对 session 重建的影响。
- [x] 完成 Open-SWE-Traces 100-workflow candidate-edge diagnostics。
- [x] 增加 schema-flexible SWE-style repaired workflow importer，用于后续 SWE-bench/Claw-SWE-Bench 本地样本导入。
- [x] 完成 SWE-bench Lite repaired balanced sample：57 workflows、12 repos/owners、228 requests。
- [x] 完成 SWE-bench Lite repaired `no_repository_fields` ablation，确认 repaired `repository=` 字段主导 project/owner recovery。
- [x] 增加 defense utility/cost proxy 输出：token retention、message retention、tool char retention、marker removal counts。
- [x] 完成 Open-SWE 100-workflow turns `3 6 9 12` preliminary defense/utility probe。
- [x] 增加 selective workspace/path mitigation variants：`M7_WORKSPACE_STABLE`、`M8_WORKSPACE_SESSION`、`M9_PATH_TYPE_ONLY`。
- [x] 完成 Open-SWE 100-workflow selective mitigation probe，得到 workspace pseudonymization privacy/utility frontier。
- [x] 增加 SWE-bench `--repair-context-mode natural`，避免显式注入 `repository=` repair context。
- [x] 完成 SWE-bench Lite natural balanced audit、M0 和 no-path ablation。
- [x] 完成 Open-SWE `openhands/qwen35_122b` 500 raw cross-split replication：cumulative、no-workspace、turn-delta、turn-delta no-workspace。
- [x] 完成 Open-SWE `sweagent/minimax_m25` 500 raw cross-scaffold replication：cumulative、no-workspace、turn-delta、turn-delta no-workspace。
- [x] 完成 Open-SWE `sweagent/qwen35_122b` 500 raw cross-scaffold replication：cumulative、no-workspace、turn-delta、turn-delta no-workspace。
- [x] Open-SWE importer 增加 `--sample-mode first|reservoir` 和 `--max-source-rows`，为随机/蓄水池抽样 sweep 做准备。
- [x] Hugging Face rows API fallback 增加分页重试，并降低 page size，减少大页 `IncompleteRead`。
- [x] 本地 workflow sampler 增加 `--sample-mode reservoir` 和 `--seed`，用于从已导入数据集中做 sample-size sweep fallback。
- [x] 增加 Open-SWE 2x2 matrix 汇总器，生成 `docs/tables/open_swe_2x2_*` 表格。
- [x] 完成 OpenHands/minimax 本地 workflow reservoir 250 seed7 sweep：cumulative、no-workspace、turn-delta、turn-delta no-workspace。
- [x] 修复 `datasets` streaming 路径的 `hf_config` 传参，完成 OpenHands/minimax HF streaming reservoir 250 seed7 sweep。
- [x] 完成 OpenHands/minimax HF streaming reservoir 100/250/500 seed7 sweep，并保留 1,000 first-N 作为 anchor。
- [x] 自动生成 OpenHands/minimax sample-size sweep 表：`docs/tables/open_swe_openhands_minimax_sample_size_sweep.*`。
- [x] 确认基础检查通过：`uv run ruff check .` 和 `uv run python -m unittest discover -s tests -q`。

### 当前关键结果

合成 MVP：

- `M0` raw 下，`hybrid` 的 session F1 为 `0.855`，user F1 为 `1.000`，org F1 为 `0.769`。
- `M1` secret filtering 与 `M0` 基本一致，说明当前攻击主要依赖非 secret 的内容侧准标识符。
- `M2` entity redaction 和 `M6` combined defense 能打断当前 hybrid 攻击。
- `M3` context minimization 仍保留较强 session/user 信号，但 org 链接被打断。
- `M0/M1/M4` 下组织画像 micro F1 约为 `0.773`。

Open-SWE-Traces raw sample：

- 数据：`openhands/minimax_m25`，100 trajectories，1,200 requests，96 projects，94 owners。
- `repair_mode=none`，未向 attack view 添加 `repository=` 或修复 workspace 字段。
- `attack_view.jsonl` 中没有非 provider 字段；转换元数据放在 `request_provenance.jsonl`。
- raw trajectory 原文已经包含 workspace/tool context。
- `M0` 下，`hybrid` 的 session F1 为 `0.998`，project F1 为 `1.000`，owner/org F1 为 `1.000`。

Open-SWE-Traces 1,000 trajectory update:

- raw final-turn probe: hybrid project/repo F1 `0.995`, owner/org F1 `0.984`。
- final-turn no-workspace ablation: hybrid project/repo F1 `0.000`, owner/org F1 `0.000`。
- raw turns `3 6 9 12` cumulative probe: hybrid session F1 `0.985`, project/repo F1 `0.996`, owner/org F1 `0.987`。
- no-workspace cumulative probe: hybrid session F1 `0.529`, project/repo F1 `0.000`, owner/org F1 `0.000`。
- turn-delta probe: hybrid session F1 drops to `0.116`; no-workspace turn-delta drops to `0.023`。
- candidate-edge diagnostics: cumulative raw edges dominated by workspace/repo plus high shingle overlap; turn-delta no-workspace leaves only sparse session edges。
- Current interpretation: Open-SWE mainly supports workspace/tool-environment artifact leakage; cumulative-context overlap explains much of the session reconstruction strength.

SWE-bench Lite repaired balanced update:

- 数据：57 workflows，228 requests，12 projects/repos，12 owners/org-like labels。
- 这是 repaired workflow validation，不是 raw provider evidence。
- repaired M0 hybrid：session F1 `0.329`，project/repo F1 `1.000`，owner/org F1 `1.000`。
- `no_repository_fields` 后 hybrid：session F1 `0.254`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- Current interpretation: SWE-bench repaired project/owner recovery 主要来自 importer 加入的 `repository=` repair context，不能作为 raw 攻击证据。

Open-SWE preliminary defense/utility update:

- 100-workflow turns `3 6 9 12` 小样本上，`M2` entity/path redaction 将 hybrid project/org F1 降到 `0.000`，但保留全部 token count 元数据且 tool char retention 约 `0.858`。
- `M3` context minimization 将 token retention 降到 `0.131`、tool char retention 降到 `0.060`，但 hybrid project/org F1 仍为 `1.000`，说明泛化上下文裁剪没有移除核心 workspace path 信号。
- `M6` combined 将 hybrid session F1 降到 `0.030`、project/org F1 降到 `0.000`，但 token retention 只有 `0.131`，需要后续 utility/task-success 验证。

Open-SWE selective mitigation update:

- `M7_WORKSPACE_STABLE`：project/org F1 降到 `0.000`，session F1 仍为 `0.974`，token retention `1.000`，tool char retention `0.970`。
- `M8_WORKSPACE_SESSION`：project/org F1 降到 `0.000`，session F1 降到 `0.593`，token retention `1.000`，tool char retention `0.995`。
- `M9_PATH_TYPE_ONLY`：project/org F1 降到 `0.000`，session F1 降到 `0.529`，token retention `1.000`，tool char retention `0.888`。
- Current interpretation: 稳定 workspace pseudonymization 足以打断 project/owner linkage，但仍保留 session linkage；request-scoped pseudonymization 或 type-only path 能进一步压低 session linkage。

SWE-bench natural repair update:

- 数据：57 workflows，228 requests，12 projects/repos，12 owners/org-like labels。
- audit 中没有 `repository_field`、没有 `[repair_context]` marker。
- natural M0 hybrid：session F1 `0.260`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- natural no-path hybrid：session F1 `0.205`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- Current interpretation: 不显式注入 `repository=` 时，当前 SWE-bench repaired scaffold 不支持 project/owner recovery，是有价值的负结果。

Open-SWE cross-split update:

- `openhands/qwen35_122b` raw 500：500 workflows，6,000 requests，395 projects/repos，371 owners/org-like labels。
- cumulative raw hybrid：session F1 `0.974`，project/repo F1 `1.000`，owner/org F1 `1.000`。
- cumulative no-workspace hybrid：session F1 `0.548`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta raw hybrid：session F1 `0.038`，project/repo F1 `0.996`，owner/org F1 `0.997`。
- turn-delta no-workspace hybrid：session F1 `0.009`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- Current interpretation: 两个 OpenHands split 趋势一致，稳健信号是 workspace/tool-environment artifact leakage；session 高分主要来自 cumulative context。

Open-SWE cross-scaffold update:

- `sweagent/minimax_m25` raw 500：500 workflows，6,000 requests，374 projects/repos，347 owners/org-like labels。
- audit 中 workspace path 只出现在 `66/6000` requests，raw `repository=` marker 出现在 `11/6000` requests。
- cumulative raw hybrid：session F1 `0.711`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- cumulative no-workspace hybrid：session F1 `0.711`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta raw hybrid：session F1 `0.028`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta no-workspace hybrid：session F1 `0.028`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- Current interpretation: scaffold design materially changes linkability risk。OpenHands 暴露稳定 workspace/repo artifacts；SWE-agent 在该 split 下没有足够 project/owner artifact。

Open-SWE full 2x2 scaffold/split update:

- `sweagent/qwen35_122b` raw 500：500 workflows，6,000 requests，404 projects/repos，366 owners/org-like labels。
- audit 中 workspace path 只出现在 `53/6000` requests，raw `repository=` marker 出现在 `11/6000` requests。
- cumulative raw hybrid：session F1 `0.700`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- cumulative no-workspace hybrid：session F1 `0.697`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta raw hybrid：session F1 `0.003`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta no-workspace hybrid：session F1 `0.003`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- Current interpretation: Open-SWE 四格复现完成。OpenHands 两个 split 支持 workspace/repo artifact driven project/owner reconstruction；SWE-agent 两个 split 不支持 project/owner reconstruction，但 cumulative context 仍带来 session linkage。

Open-SWE reporting update:

- 当前 2x2 matrix 已自动汇总到 `docs/tables/open_swe_2x2_attack_matrix.csv` 和 `docs/tables/open_swe_2x2_attack_matrix.md`。
- dataset matrix 已输出到 `docs/tables/open_swe_2x2_dataset_matrix.csv`。
- OpenHands/minimax sample-size sweep 已自动汇总到 `docs/tables/open_swe_openhands_minimax_sample_size_sweep.csv` 和 `docs/tables/open_swe_openhands_minimax_sample_size_sweep.md`。
- 表格记录当前 sample mode；四格 scaffold/split matrix 仍是 first-N 样本，sample-size sweep 已开始使用 HF streaming reservoir sampling。

Open-SWE reservoir sweep update:

- 远端 Hugging Face rows API 在 `max_source_rows=5000/2000` 时出现 `HTTP 502`、`IncompleteRead` 和长时间阻塞；已增加 retry。安装 `datasets` 后，HF streaming reservoir 已跑通。
- HF streaming reservoir 100/250/500 seed7 均扫描 5,000 source rows，eligible trajectories 5,000。
- 100 reservoir：cumulative raw hybrid session/project/org F1 `0.987/1.000/1.000`；turn-delta no-workspace `0.033/0.000/0.000`。
- 250 reservoir：cumulative raw hybrid session/project/org F1 `1.000/1.000/1.000`；turn-delta no-workspace `0.026/0.000/0.000`。
- 500 reservoir：cumulative raw hybrid session/project/org F1 `0.997/0.974/0.935`；turn-delta no-workspace `0.021/0.000/0.000`。
- 1,000 first-N anchor：cumulative raw hybrid session/project/org F1 `0.985/0.996/0.987`；turn-delta no-workspace `0.023/0.000/0.000`。
- 当前解释：OpenHands/minimax 的 sample-size sweep 已经降低 first-N ordering concern；但精确点估计仍需 bootstrap CI 或多 seed。
- 本地 fallback：从 `open_swe_traces_raw_1000` 做 workflow-level reservoir 250 seed7。
- 本地 reservoir 250 audit：250 workflows，3,000 requests，211 projects/repos，194 owners/org-like labels，workspace path 出现在 3,000/3,000 requests。
- cumulative raw hybrid：session F1 `0.989`，project/repo F1 `1.000`，owner/org F1 `1.000`。
- cumulative no-workspace hybrid：session F1 `0.609`，project/repo F1 `0.000`，owner/org F1 `0.000`。
- turn-delta raw hybrid：session F1 `0.118`，project/repo F1 `1.000`，owner/org F1 `1.000`。
- turn-delta no-workspace hybrid：session F1 `0.020`，project/repo F1 `0.000`，owner/org F1 `0.000`。

### 当前不能过度声明的点

- Open-SWE-Traces 是 real-repo agent trajectory data，不是企业生产日志。
- Open-SWE-Traces 的 owner/org 标签来自 GitHub repo owner，不能直接等同于企业组织身份。
- Open-SWE-Traces 已完成 OpenHands/SWE-agent x minimax/qwen35 2x2 first-N replication，但还缺跨 scaffold 的 reservoir sweep 和置信区间。
- 当前 hybrid attack 仍偏启发式，需要 feature ablation、candidate-edge diagnostics 和 threshold/sensitivity 报告。
- 当前 defense 评估还没有任务质量、token overhead、latency overhead，不能称为完整防御方案。

## 1. 论文主线和研究问题

### RQ1: 匿名 Agent 请求是否仍可被内容侧重识别？

- [x] 在合成 Dataset A 上完成初步验证。
- [x] 在 Open-SWE-Traces raw sample 上完成初步验证。
- [x] 在 Open-SWE-Traces 1,000 trajectory raw sample 上复现。
- [x] 在多个 Open-SWE-Traces config/split/scaffold 上复现。
- [x] 在至少一个独立 real-repo repaired workflow 数据集上复现。

验收标准：

- 主表报告 session/project/org 三层聚类 F1。
- 每个数据集都报告 provider-visible 字段审计。
- 每个数据集都明确 user-level ground truth 是否可用。

### RQ2: 哪些内容侧信号最关键？

- [x] 加入 hybrid feature ablation 框架：`--feature-ablations none no_paths no_repo_ids no_domains no_traces no_shingles no_tool_system no_time_length`。
- [x] 报告 no-path/no-workspace ablation。
- [x] 报告 no-domain ablation。
- [x] 报告 no-repo-id ablation。
- [x] 报告 no-trace/context-id ablation。
- [x] 报告 no-shingle/context-overlap ablation。
- [x] 报告 no-timestamp/no-token-length ablation。
- [x] 报告 no-tool-schema/no-system-prompt ablation。
- [x] 设计 provider-side semantic proxy baseline，并和低成本启发式方法比较。
- [ ] 如需强 embedding claim，补真实 embedding 或本地 sentence-transformer 小样本。

验收标准：

- 每个 ablation 都在合成和至少一个 real-repo 数据集上运行。
- 表格区分 session/project/org 层级。
- 结论必须能说明“哪些信号是主要贡献，哪些只是辅助”。

### RQ3: 从重建工作流中能恢复多少画像？

- [x] 合成 Dataset A 上完成规则画像恢复。
- [ ] 区分 truth-org upper bound 和 predicted-cluster 实际画像恢复。
- [x] 为 Open-SWE-Traces 增加 profile truth 扩展入口：language、repo name、package/build files、CI clues、framework clues。
- [x] 增加 evidence coverage 指标，要求每个预测字段都能追溯到 request ids。
- [x] 增加 unsupported prediction 统计。
- [ ] 增加 fuzzy match 或 normalization，避免 repo/service 名轻微变体导致误判。
- [ ] 增加 profile risk score，将 L1-L5 字段分层汇总。

验收标准：

- 画像表按字段报告 precision/recall/F1。
- 同时报告 predicted-cluster profile 和 ground-truth-cluster profile。
- 不依赖 L5 secret 也能恢复 L2-L4 画像，才可以支撑主张。

新增补跑命令：

```bash
uv run python -m agent_privacy.data.profile_truth \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12

uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12 \
  --output results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_profile \
  --defenses M0 \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --ablations none \
  --feature-ablations none \
  --profile-level org \
  --open-swe-fast-features
```

### RQ4: 哪些缓解方法有效，代价是什么？

- [x] 初步实现 `M1/M2/M3/M4/M6`。
- [ ] 拆分 `M2` redaction 变体：stable、per-session、per-request、type-only。
- [x] 增加 no-workspace-path transform，作为攻击可行性消融，不等同于 defense。
- [x] 增加 workspace/path selective mitigation variants。
- [ ] 增加 domain-only redaction、repo-only redaction、trace-only redaction。
- [ ] 增加 length padding 和 length bucketing 的独立变体。
- [ ] 增加 tool-output clipping 比例参数。
- [ ] 增加 context minimization 的多档强度。
- [ ] 增加 broker mixing 的多档延迟窗口。
- [x] 设计任务质量代理指标：保留消息比例、保留 token 比例、tool output 截断比例。
- [ ] 如果接入可执行 benchmark，再报告 task success rate。

验收标准：

- 防御表同时报告 attack F1 drop、profile F1 drop、token overhead/retention、latency/mixing 参数。
- 不把“打断当前启发式攻击”等同于“解决隐私问题”。

## 2. 数据集 Todo

### Dataset A: Controlled Synthetic

当前用途：快速 sanity check、完整 ground truth、可控消融。

- [x] 支持 org/user/project/workflow/turn/profile truth。
- [x] 支持 noise requests。
- [x] 支持 shared template/repo/service/stack/cross-user project/context carryover/time mixing knobs。
- [ ] 增加 scale sweep configs：
  - `small`: 5 orgs, 3 users/org, 2 projects/org。
  - `medium`: 当前 MVP 规模。
  - `large`: 100 orgs, 5-20 users/org。
- [ ] 增加 difficulty sweep configs：
  - low/high shared templates。
  - low/high shared repo/service names。
  - low/high context carryover。
  - low/high noise rate。
  - low/high time mixing。
- [ ] 增加 username/path ablation generator option。
- [ ] 增加 synthetic secret 注入比例，并确认 `M1` 只影响 L5，不影响 L2-L4 主结果。
- [ ] 输出 dataset card：生成参数、规模、字段、限制、伦理说明。

### Dataset B1: Open-SWE-Traces

当前用途：主 real-repo agent trajectory benchmark。

- [x] 实现 importer。
- [x] 支持 raw `repair_mode=none`。
- [x] 支持 repaired `repository`、`workspace`、`repository_workspace`。
- [x] 支持 provider-view audit。
- [x] 完成 100 trajectory raw sample。
- [x] 扩展到 1,000 trajectories。
- [ ] 在以下组合上重复：
  - [x] `openhands/minimax_m25`
  - [x] `openhands/qwen35_122b`
  - [x] `sweagent/minimax_m25`
  - [x] `sweagent/qwen35_122b`
- [x] 报告 source rows seen、trajectories used、requests、workflows、projects、owners。
- [x] 报告 project/owner repetition distribution。
- [x] 添加 no-workspace-path raw ablation。
- [x] 添加 path/repo/context candidate-edge diagnostics。
- [x] 明确 user-level unavailable，默认跳过 user scoring。
- [ ] 输出 dataset card 和 audit markdown。

### Dataset B2: SWE-bench Repaired Workflows

用途：独立 real-repo validation，不依赖 Open-SWE trajectory 格式。

- [x] 选择 SWE-bench Lite test split 作为 repaired validation 子集。
- [x] 构造本地 schema-flexible importer：issue/problem statement、repo、patch、test patch、failing tests、log snippets。
- [x] 将每个 issue 构造成 multi-turn Agent request sequence。
- [x] 使用 repo owner 作为 owner/org，repo 作为 project，instance id 作为 session。
- [x] 输出 attack/truth/provenance/manifest。
- [x] 审计是否有非 provider 字段泄漏。
- [x] 运行 M0 attack-only 和 `no_repository_fields` ablation。
- [x] 增加不显式注入 `repository=` 的 alternate repair policy，测试是否还能从 issue/patch/test artifacts 恢复 repo。

### Dataset D: Claw-SWE-Bench

用途：小型 fast validation set。

- [ ] 实现 importer。
- [ ] 先跑 lite subset，再跑 full subset。
- [ ] 构造 workflow repair policy，避免过度添加 attack-visible 标签。
- [ ] 报告与 Open-SWE-Traces 的差异。

### Dataset C/E: DevGPT, WildChat/CodeChat Supplement

用途：真实开发者对话风格补充，不作为主 Agent-tool 证据。

- [ ] 确定许可和再分发限制。
- [ ] 设计脱敏策略，避免公开用户名或个人身份。
- [ ] 只评估 session-level linkability 和技术 profile，不强行做 org-level。
- [ ] 明确其不是 tool-using Agent trajectory。

## 3. 攻击方法 Todo

### Baselines

- [x] `temporal` baseline。
- [x] `rare` baseline。
- [x] `prefix` baseline。
- [x] `tool` baseline。
- [x] `hybrid` attack。
- [x] `provider_lowcost` two-stage attack：cache gating、rare buckets、semantic proxy、context-overlap refine、workflow export。
- [x] 加入 `random` baseline。
- [x] 加入 `oracle-size` 或 `same-size random clustering` baseline。
- [x] 加入 `semantic proxy` baseline/ablation。
- [ ] 加入真实 `embedding` baseline。
- [ ] 加入 `topic/task-type` baseline。

### Hybrid 改进

- [ ] 参数化 hybrid 权重和阈值，不要只写死在代码里。
- [ ] 输出 candidate edges，包含 edge reason、feature overlaps、score components。
- [x] 支持 threshold sweep，画 precision-recall/F1 曲线；当前完成 Open-SWE sample100 fixed-turn context sweep。
- [ ] 支持按层级独立调参：session/project/org。
- [ ] 支持 connected components 之外的 community detection 或 hierarchical clustering。
- [x] 增加 turn-order reconstruction 初版：在 predicted session cluster 内按 provider-visible timestamp 排序。
- [x] 增加 turn-order metrics 初版：`ordering_metrics_all.csv` 输出 adjacent-pair accuracy 和 pairwise order accuracy。
- [x] 增加 context-containment 排序。
- [ ] 增加 Kendall tau 和 edit distance。
- [x] 导出 reconstructed workflow artifacts：`reconstructed_workflows.jsonl` 和 `workflow_reconstruction_metrics_all.csv`。

### 可解释性

- [ ] 对每个实验输出 top linking features。
- [ ] 对每个层级输出 merge error examples 和 split error examples。
- [ ] 输出不含长原文的 edge explanation snippets。
- [ ] 将 candidate-edge diagnostics 写入 JSONL，便于论文人工审计。

## 4. 防御和缓解 Todo

### Redaction Variants

- [ ] `redact_stable_global`: 当前近似策略。
- [ ] `redact_stable_session`: 同一 session 内稳定，跨 session 变化。
- [ ] `redact_per_request`: 每个请求独立映射。
- [ ] `redact_type_only`: 只保留 `[PATH]`、`[DOMAIN]`、`[REPO]` 类型。
- [ ] `redact_hash_bucket`: 映射到粗粒度桶，测试 utility/privacy tradeoff。

### Context Minimization Variants

- [ ] `tool_clip_1_line`
- [ ] `tool_clip_5_lines`
- [ ] `drop_prior_context`
- [ ] `local_summary_only`
- [ ] `drop_assistant_history`
- [ ] `current_turn_only`

### Broker-Side Variants

- [ ] delay window: 0, 10 min, 1 hour, 24 hours。
- [ ] token length bucket: none, powers-of-two, coarse buckets。
- [ ] batch mixing by model/task。
- [ ] system prompt normalization。
- [ ] tool schema normalization。
- [x] provider-lowcost cache gating 已实现；Open-SWE 因无 cache telemetry 标记为 `cache_unavailable`。
- [ ] cache isolation simulation。
- [ ] multi-provider splitting simulation。

### Utility/Cost

- [x] 记录每个 transform 前后的 token count。
- [x] 记录 message retention ratio。
- [x] 记录 removed entity counts。
- [ ] 记录 synthetic latency overhead。
- [ ] 如果能接入任务执行，记录 pass rate 或 resolved rate。

## 5. 实验矩阵 Todo

### Phase 1: Attack Feasibility

- [ ] Dataset A medium, M0, all baselines + hybrid。
- [x] Open-SWE-Traces raw 1,000, M0, scalable baselines + hybrid。
- [ ] Open-SWE-Traces multi-split, M0, all baselines + hybrid。
- [x] SWE-bench repaired workflows, M0, scalable baselines + hybrid。

论文输出：

- Main attack table。
- Dataset statistics table。
- Provider-view audit table。

### Phase 2: Feature Ablation

- [ ] Dataset A medium feature ablations。
- [ ] Open-SWE-Traces raw feature ablations。
- [x] no-workspace-path ablation。
- [ ] no-repo-id ablation。
- [ ] no-context-overlap ablation。
- [ ] no-timing ablation。
- [ ] no-tool/system ablation。

论文输出：

- Ablation table。
- Edge reason distribution figure。
- Error analysis table。

### Phase 3: Scale and Difficulty

- [x] Synthetic scale/difficulty/profile matrix：`docs/tables/synthetic_matrix_summary.md`。
- [x] Synthetic user-level controlled evidence：Synthetic Dataset A contains full `user_id` truth; current matrix reports `hybrid_user_f1=1.000`。
- [ ] Synthetic fine-grained noise/time-mixing sweeps beyond current scenarios。
- [x] OpenHands/minimax HF reservoir sample-size sweep: 100/250/500 plus 1,000 first-N anchor。
- [x] Provider-lowcost longitudinal fixed-budget snapshot table：`open_swe_provider_lowcost_longitudinal.*`。
- [x] Provider-lowcost full-snapshot fixed-turns points：first 1,000/4,000/8,000/12,000 requests。
- [ ] Provider-lowcost full all-turn 12,000-request point：当前 source context 过大，需进一步流式化 feature extraction / workflow reconstruction。
- [x] SWE-agent/minimax local reservoir sample-size sweep: 100/250/500 from imported raw500 source。
- [ ] SWE-agent/minimax full-source HF reservoir sample-size sweep: optional/network-dependent stronger robustness check。
- [ ] Open-SWE 1,000 HF reservoir point if compute/network budget allows。
- [x] Open-SWE workflow-level bootstrap CI for main 2x2 table：`docs/tables/open_swe_2x2_bootstrap_ci.md`。
- [ ] Open-SWE workflow-level bootstrap CI for sample-size/longitudinal tables。
- [x] Open-SWE sample100 provider-lowcost/control baseline workflow-level bootstrap CI。

论文输出：

- Sensitivity curves。
- Scale/runtime table。

### Phase 4: Profile Reconstruction

- [x] Synthetic predicted-cluster profile in controlled matrix。
- [ ] Synthetic truth-cluster profile upper bound。
- [x] Open-SWE repo/project technical profile extraction。
- [x] Field-level profile tables。
- [x] Profile-derived watchlist 初版：输出 `profile_watchlist.json` 和 retrieval metrics。
- [x] Open-SWE truth-cluster profile upper bound vs predicted-cluster profile table。
- [x] L1-L5 risk stratification。

论文输出：

- Profile reconstruction table。
- Evidence coverage table。
- [x] Example reconstructed profile with redacted snippets：`docs/redacted-profile-examples.md`。

### Phase 5: Mitigations

- [ ] Synthetic M0/M1/M2/M3/M4/M6。
- [x] Open-SWE M0/M1/M2/M3/M4/M6 preliminary 100-workflow probe。
- [x] Selective redaction variants summarized as preliminary defense utility frontier。
- [ ] Context minimization variants beyond current path/workspace transforms。
- [ ] Broker mixing variants。
- [ ] Combined best-effort defense。

论文输出：

- Defense effectiveness table。
- Utility/privacy tradeoff table。
- Defense recommendation matrix。

## 6. 工程 Todo

### CLI and Config

- [ ] 把 attack method 参数、hybrid weights、thresholds 移入 config。
- [ ] 增加 experiment manifest，记录 git commit、config、dataset manifest、命令、时间。
- [ ] 增加 `--no-delete-output` 或 `--resume`，避免每次运行删除旧结果。
- [ ] 增加 `--ablation` 参数。
- [ ] 增加 `--defense-params` 参数。
- [ ] 增加统一的 `run_experiment.py` 或 shell recipe。
- [ ] 增加结果目录命名规范：
  - `results/{dataset}_{sample_size}_{repair_mode}_{experiment_kind}_{date}/`
  - 示例：`results/open_swe_1000_none_attack_202607/`
  - 示例：`results/synthetic_medium_m0_ablation_202607/`
- [ ] 每个结果目录写入 `manifest.json`：
  - command
  - git commit
  - dataset path
  - dataset manifest hash
  - config path
  - defense config
  - method config
  - seed
  - start/end time
  - row counts
  - skipped counts
- [ ] 每个结果目录写入 `README.md`，用 10 行以内说明这个结果能不能进入论文主表。

### Reporting

- [ ] 自动生成 main tables。
- [x] 自动生成 Open-SWE 2x2 attack/dataset tables。
- [x] 自动生成 OpenHands/minimax sample-size sweep table。
- [ ] 自动生成 ablation tables。
- [ ] 自动生成 defense tables。
- [ ] 自动生成 dataset audit tables。
- [ ] 自动生成 markdown summary。
- [ ] 导出 LaTeX-ready CSV 或 `.tex` table。
- [ ] 自动生成 risk checklist：
  - 是否 raw-first。
  - 是否 provider-view clean。
  - 是否包含 baselines。
  - 是否包含 ablations。
  - 是否区分 project 和 owner/org。
  - 是否有 utility/cost 指标。
- [ ] 自动生成 paper appendix tables，保留失败和弱结果。

### Tests

- [x] 基础 smoke test。
- [x] Open-SWE local JSONL importer test。
- [ ] feature extraction unit tests。
- [ ] defense transform unit tests。
- [ ] clustering metrics edge-case tests。
- [ ] profile evaluation tests。
- [ ] provider-view audit regression test。
- [ ] ablation transform tests。

### Reproducibility

- [ ] 固定所有随机种子。
- [ ] 每个实验输出 config snapshot。
- [ ] 每个数据集输出 source manifest。
- [ ] 每个结果输出 row counts 和 skipped counts。
- [ ] 记录 dependency versions。
- [ ] 提供 one-command reproduction for smoke、synthetic main、Open-SWE main。
- [ ] 增加 `make` 或 shell recipes：
  - `run_smoke`
  - `run_synthetic_main`
  - `import_open_swe_100`
  - `import_open_swe_1000`
  - `run_open_swe_attack`
  - `run_open_swe_ablation`
  - `build_tables`
- [ ] 对最终论文主表结果进行 clean-room rerun，确认不是旧缓存或手工文件造成。
- [x] Open-SWE importer 支持 first-N 与 reservoir sampling，并将 sample mode 写入 manifest。

## 6.5 论文交付物 Todo

### 必须交付

- [x] `Dataset card: Synthetic A`
- [x] `Dataset card: Open-SWE-Traces adapted`
- [x] `Dataset card: SWE-bench Lite adapted`
- [x] `Provider-view audit table`
- [ ] `Main attack table`
- [ ] `Feature ablation table`
- [x] `Scale/difficulty table`
- [x] `Profile reconstruction table`
- [x] `Defense effectiveness table`
- [x] `Utility/privacy tradeoff table` 初版：privacy metrics + token/tool-retention proxies；task utility 仍待补。
- [x] `Runtime/cost table`：historical longitudinal scale table + sample100 threshold/timed runtime table。
- [ ] `Ethics and data handling statement`
- [ ] `Reproducibility appendix`

### 建议图表

- [ ] 攻击框架图：mixed anonymous requests -> graph edges -> workflow clusters -> profiles。
- [ ] 数据契约图：attack view、ground truth、provenance 三者隔离。
- [ ] edge reason distribution：path/repo/context/tool/time 各自贡献。
- [x] sample-size sweep curve/table data。
- [x] defense privacy/utility frontier table。
- [ ] profile field recovery heatmap。

### 每个主表的最低要求

- [ ] 表格 caption 明确 dataset、repair mode、threat setting、ground truth level。
- [ ] 表格中包含至少一个 naive baseline 和一个 single-signal baseline。
- [ ] 表格中不混合 raw 和 repaired 结果，除非列中显式标出。
- [ ] Open-SWE 表格必须写 project/repo 和 owner/org，不写 enterprise。
- [ ] user-level 不可靠时写 N/A，不写 0。
- [ ] defense 表必须同时有 utility/cost 列，否则只能称为 preliminary defense probe。

## 7. 论文写作 Todo

### Introduction

- [ ] 明确问题：隐藏显式身份不等于内容侧不可链接。
- [ ] 强调 Agent API 与普通 chatbot 的差异：工具输出、路径、日志、代码、上下文递增。
- [ ] 陈述贡献：threat model、two-stage attack、benchmark、mitigation evaluation。

### Threat Model

- [x] 写出 D0/D1、A0/A1、cold-start/warm-start。
- [ ] 将主实验固定为 D1 + A0 + cold-start。
- [ ] 明确非目标，避免被审稿人质疑过强假设。

### Dataset Section

- [ ] Dataset A 作为 controlled benchmark。
- [ ] Open-SWE-Traces 作为 real-repo agent trajectory benchmark。
- [ ] 明确 repair policy。
- [ ] 明确 provider-visible fields。
- [ ] 明确伦理和数据限制。

### Attack Section

- [ ] 写两阶段攻击框架。
- [ ] 写 feature taxonomy。
- [ ] 写 graph construction 和 clustering。
- [ ] 写 profile reconstruction。
- [ ] 写复杂度和成本分析。

### Evaluation Section

- [ ] 主攻击结果。
- [ ] 消融实验。
- [ ] 规模和难度实验。
- [ ] 画像恢复实验。
- [ ] 防御实验。
- [ ] 错误分析。

### Discussion

- [ ] 不把 GitHub owner 等同于企业。
- [ ] 讨论真实企业日志可能更强也可能更弱。
- [ ] 讨论 provider retention policy 和合规含义。
- [ ] 讨论 defense 的 utility tradeoff。
- [ ] 讨论 active provider 只作为 upper bound。

## 8. 推荐优先级

### P0: 先稳住攻击证据

1. [x] Open-SWE-Traces raw sample 扩到 1,000 trajectories。
2. [x] 加 no-workspace-path ablation。
3. [x] 加 project-level scoring 并和 owner/org-level 分开报告。
4. [x] 加 candidate-edge diagnostics。
5. [x] 跨 Open-SWE scaffold/split 重复；OpenHands 和 SWE-agent 2x2 矩阵已完成。

### P1: 再补论文必要消融

1. [x] hybrid/provider-lowcost feature ablation。
2. [x] threshold sweep。
3. [ ] error analysis。
4. [ ] synthetic scale/difficulty sweep。
5. [x] truth-cluster profile upper bound。
6. [x] SWE-bench alternate repair policy，不显式注入 `repository=`。
7. [x] 优化 provider-lowcost 大规模 candidate generation，使 8k/12k fixed-turn snapshot 能在固定预算内完成。
8. [ ] 优化 full all-turn 12k view 的 feature extraction 和 workflow reconstruction。

### P2: 最后系统化防御

1. [x] selective workspace/path redaction variants。
2. [ ] context minimization variants。
3. [ ] broker mixing variants。
4. [x] utility/cost proxy metrics。
5. [ ] combined defense recommendation。

## 9. 当前下一步命令建议

先重新生成当前 2x2 表格，作为后续 sweep 的对照：

```bash
uv run python -m agent_privacy.experiments.summarize_open_swe --output-dir docs/tables
```

当前 OpenHands/minimax 的 HF reservoir 100/250/500 已完成，SWE-agent/minimax 已完成
local-from-raw500 reservoir 100/250/500。SWE-agent full-source HF reservoir 仍可作为更强
robustness check，但不是当前机制叙事的唯一缺口。

```bash
uv run python -m agent_privacy.data.open_swe_traces \
  --use-hf \
  --hf-config sweagent \
  --hf-split minimax_m25 \
  --output-dir artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_250_seed7_hf \
  --limit 250 \
  --sample-mode reservoir \
  --max-source-rows 5000 \
  --seed 7 \
  --repair-mode none
```

```bash
uv run python -m agent_privacy.experiments.run_dataset \
  --dataset-dir artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_250_seed7_hf \
  --output results/open_swe_traces_sweagent_minimax_reservoir_250_seed7_hf_turns_3_6_9_12_m0_fast \
  --levels session project org \
  --methods temporal rare tool hybrid \
  --defenses M0 \
  --ablations none \
  --skip-profile \
  --turn-ids 3 6 9 12 \
  --open-swe-fast-features
```

随后优先做：

- Reservoir sample-size sweep：如网络稳定，补 SWE-agent/minimax full-source HF reservoir。
- Bootstrap CI：补 longitudinal/sample-size 的 workflow-level bootstrap。
- Threshold/feature ablation：把 hybrid score、edge reason、阈值扫描参数化并输出曲线。
- Profile reconstruction：继续完善 Open-SWE language/repo/package/build/CI clues 的 profile truth 和 evidence coverage。
