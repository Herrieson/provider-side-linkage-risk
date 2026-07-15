# 去身份化并不等于不可关联：模型 API 提供商视角下的 LLM Agent 请求重建风险

> **状态（2026-07-14）：历史规划稿，不是当前投稿论文。** 本文档早于 held-out
> 900-workflow 协议，仍包含已被替代的数值和更宽泛的探索性 claim。当前论文、范围和证据
> 边界以 `docs/overleaf/api.tex`、`docs/paper/submission-scope.md` 和
> `docs/paper/claim-audit.md` 为准。

## 摘要

LLM Agent 正在被用于软件开发、自动化运维、代码修复和企业内部工作流。为了降低隐私风险，许多部署会通过 broker、gateway 或 enterprise proxy 隐藏用户标识、组织标识、trace ID 和 session ID，再将请求转发给模型 API 提供商。然而，去除显式身份字段并不意味着请求内容本身不可关联。与普通聊天不同，Agent 请求通常包含长上下文、重复的历史对话、工具调用结果、workspace 路径、仓库结构、文件名、依赖、错误日志和环境状态。这些内容侧信号可能形成稳定的准标识符，使模型 API 提供商能够从匿名请求池中重新发现工作流、项目和组织近似实体。

本文研究一个冷启动的 provider-side reconstruction 问题：模型 API 提供商看不到 broker 侧用户身份，也没有预先建立用户画像，但可以观察正常推理过程中可见或可计算的请求内容、长度、时间、tool/schema、cache-like bucket、罕见 token 和上下文重叠信号。我们提出 CARP（Cache-Anchored Rarity Percolation），一个面向 provider-visible Agent logs 的低成本候选生成与稀有锚点渗透算法。CARP 的第一阶段从海量匿名请求中聚类属于同一 workflow、project、owner-like organization 或 semi-synthetic user 的请求；第二阶段在聚类后的请求序列上重建 Agent 工作流和技术画像。该流程先使用 cache-like bucket 锚定局部候选空间，再利用罕见 token、代码/路径符号、tool/schema、上下文递增和轻量语义信号建立稀疏候选边，最后通过受预算约束的 percolation 恢复工作流顺序并抽取画像字段。

我们在四层数据上评估这一风险。第一层是适配后的 Open-SWE-Traces，它提供真实 Agent 软件工程轨迹，用于评估 workflow/session reconstruction、project/repository linkage、GitHub owner-like linkage、turn ordering 和部分技术画像。第二层是 Open-SWE-grounded User Overlay Dataset B，它在真实 Open-SWE trace substrate 上注入受控 user/profile truth，用于评估真实用户标签缺失时无法在 Open-SWE 上直接评估的 user-level mechanism。第三层是 Synthetic Dataset A，用于在完整 ground truth 下进行规模、难度和 profile richness 的控制实验。第四层是 tau-bench historical trajectories 及其 trace-grounded T3 overlay，它提供 airline/retail 等非代码工具 Agent 轨迹，并仿照 Open-SWE overlay 构建 tenant/customer/business-project 三层真值。实验显示，Open-SWE 中的 workspace/repo artifacts 对 project 和 owner-like linkage 具有主导作用，而 cumulative context 与上下文重叠对 workflow/session reconstruction 至关重要；在 Open-SWE sample100 上，provider_lowcost 方法的 session F1 为 0.882，project/org F1 均为 1.000，显著高于 random 和 oracle-size random controls。在 Dataset B 的 12k streamed provider_lowcost 运行中，U3 设置达到 session F1 0.691、user F1 0.281、project F1 0.639、org F1 0.604；在刻意混淆 user-specific signals 的 U4 hard-shared 设置中，user F1 降至 0.029，显示 user-level 重建依赖可区分的用户信号而非无条件成立。在 tau-bench historical sample200 上，provider_lowcost 在没有 repo/path 主导信号的非代码轨迹中仍达到 session F1 0.458，远高于 random session F1 0.008；在 tau-bench T3 first-2500 三层 overlay 上，跨 cache 桶的强业务实体 percolation 将 user/project/org F1 从 0.214/0.159/0.297 提升到 0.771/0.686/0.777，同时保持 precision 0.952/0.998/1.000。由 first-2500 构建的实体 watchlist 在全部后续请求上进一步达到 user/project/org F1 0.702/0.830/0.876。成本上，12k 请求的 naive all-pairs comparison 需要约 7,199 万请求对，而 CARP/provider_lowcost 只生成约 36.2 万到 36.6 万候选对，约减少 197x 到 199x；单机 prototype 外推约为 5.4 到 6.7 CPU-hours / 1M requests。我们进一步报告 bootstrap confidence intervals、feature ablations、runtime/cost instrumentation、结构化画像对比和 defense utility frontier。

本文的核心结论是：broker 去除显式身份字段不足以防止模型 API 提供商进行内容侧关联。稳定路径、仓库标识、代码符号、工具输出和 cumulative Agent context 可以在冷启动条件下形成可利用的 linkage surface。与此同时，我们也明确限定结论边界：Open-SWE 的 org 是 GitHub owner-like label，不是企业组织；Open-SWE 不包含可靠真实 user_id，因此真实 user-level reconstruction 在该数据集上应报告为 N/A；Dataset B 是 trace-grounded semi-synthetic benchmark，不应被表述为真实用户身份恢复证据。

## 1. 引言

LLM Agent 的典型工作方式不是一次性问答，而是在多轮请求中持续观察环境、调用工具、读取文件、运行测试、分析报错并修改代码。这样的工作流让 Agent 能完成复杂任务，也让每一次 API 请求携带比普通聊天更多的环境状态。一个请求可能包含当前目录结构，另一个请求包含测试失败日志，后续请求又带上前几轮对话、工具输出和代码片段。单独看，每条请求可能只是一次普通模型调用；连续看，它们构成了一个开发者或组织正在进行的具体工作。

现实部署中，用户通常希望模型 API 提供商只看到完成推理所需的内容，而不要看到用户身份或企业身份。broker、gateway、router 和 enterprise proxy 因此常被用来隐藏显式标识：provider 不再看到真实 user ID、org ID、trace ID、session ID，也无法直接知道哪些请求来自同一个客户。这个设计的直觉是，只要身份字段被移除，请求就被混入匿名池，provider 很难进行持续跟踪。

本文指出，这一直觉对 LLM Agent 请求并不充分。Agent 请求内容本身包含大量准标识符。workspace 路径、repo slug、包名、文件名、类名、函数名、CI job、服务名、数据库名、错误字符串和 tool schema 都可能在多条请求中稳定重复。更重要的是，许多 Agent 框架采用 cumulative context：后续请求会携带前序上下文和工具观察结果。这意味着同一 workflow 内部的请求天然具有上下文递增关系。即使没有任何显式 ID，provider 仍可能通过内容侧信号重建请求之间的关联。

本文研究的问题是：

> 在 broker 已经隐藏显式用户和组织标识的情况下，一个冷启动的模型 API 提供商能否从匿名 LLM Agent 请求池中重新聚类请求、恢复工作流，并构建项目或组织近似实体的技术画像？

这个问题包含两个阶段。第一阶段是 linkage：provider 需要从混合请求池中判断哪些请求属于同一工作流、项目、owner-like organization，或在带有受控真值的数据中属于同一用户。第二阶段是 profiling：provider 在获得一组关联请求之后，进一步恢复 Agent 工作流顺序，抽取技术栈、项目结构、工具链和潜在安全线索。

一个直接做法是对所有请求进行全量 embedding 聚类或 pairwise similarity 计算。但这既不符合海量 provider traffic 的成本约束，也不符合冷启动威胁模型。本文因此关注低成本 provider-side pipeline。我们的核心观察是，provider 在正常推理中已经可以获得或廉价计算一些粗粒度信号，例如 cache-like bucket、上下文长度、请求时间、tokenization 后的罕见 token、tool/schema 和局部 embedding。攻击不需要一开始做全局语义搜索，而可以先用这些信号构建候选桶，再在候选桶内做轻量候选边生成和上下文链式恢复。

本文的贡献如下：

1. 我们形式化了 broker 去身份化条件下的 LLM Agent provider-side reconstruction 问题，将隐私风险从单条 prompt 泄露扩展到跨请求 linkage、workflow reconstruction 和 profile accumulation。
2. 我们提出并实现了 CARP，一个 cache-anchored rarity percolation 算法。它将 cache-like bucket、罕见/结构 token、上下文重叠、tool/schema、时间/长度和轻量语义信号组织为稀疏候选边生成过程，在冷启动条件下恢复匿名请求之间的关联，同时避免 naive all-pairs comparison。
3. 我们构建了四层评估体系：真实 Open-SWE-Traces 用于软件工程 Agent 生态有效性，tau-bench historical trajectories 及 T3 overlay 用于非代码工具 Agent 外部有效性和三层机制评估，Open-SWE-grounded User Overlay Dataset B 用于 user-level mechanism，Synthetic Dataset A 用于完整 ground truth 下的控制实验。
4. 我们系统报告 feature ablations、negative controls、bootstrap confidence intervals、turn ordering、profile reconstruction、runtime/cost instrumentation 和初步 defense utility frontier，并明确区分真实数据结论与 semi-synthetic 机制证据。

## 2. 背景与动机

### 2.1 LLM Agent 请求的内容侧特征

普通聊天请求通常以自然语言问题为主，而 LLM Agent 请求常常混合自然语言、系统提示、工具 schema、工具调用历史、文件内容、shell 输出、测试日志和代码 diff。对于软件工程 Agent，请求中常见内容包括：

- workspace 路径，例如 `/workspace/<owner>__<repo>`；
- GitHub owner/repo、文件路径和模块名；
- package manager、build tool、test framework；
- class、function、error string 和 stack trace；
- CI/CD、cloud、database、auth 或 service hints；
- 多轮 cumulative context 中重复出现的历史状态。

这些字段并不一定是传统意义上的 secret，也不一定包含邮箱、手机号或 API key，但它们仍然可能成为可关联的准标识符。一个 repo slug 可以把请求连接到项目，一个 workspace path 可以把请求连接到 owner-like entity，一段连续增长的上下文可以把请求连接成 workflow。

### 2.2 Broker 去身份化的不足

Broker 或 gateway 可以隐藏显式身份字段，但无法轻易删除完成 Agent 任务所需的所有上下文。过度删除路径、文件名和工具输出会损害任务可用性；保留这些内容又可能留下 linkage surface。因此，本文关注的是一种结构性风险：即使部署没有泄露显式身份，Agent 内容为了任务成功而保留的上下文也可能让 provider 重新发现身份关联。

### 2.3 为什么需要 provider-side 低成本方法

如果攻击方法依赖全量 pairwise embedding 或大型 LLM 分析每一对请求，那么它在海量 provider traffic 上不现实。我们的方法假设 provider 从冷启动开始，没有目标用户画像，也不知道哪个请求属于哪个客户。它必须先用低成本信号从匿名池中挖掘候选关联，再对候选集合做更精细的分析。

这使本文的问题区别于传统的已知目标搜索。provider 不是拿着某个企业名去搜索请求，而是先从混合请求中发现稳定 cluster，再把 cluster 转化为 profile 和 watchlist。

## 3. 威胁模型与问题定义

### 3.1 参与方

我们考虑三个角色：

- 用户或组织使用 LLM Agent 完成软件工程任务；
- broker/gateway 负责隐藏显式 user ID、org ID、trace ID、session ID，并将请求转发给模型 API provider；
- 模型 API provider 负责正常推理，因此能观察 provider-visible request content。

provider 是 honest-but-curious。它不篡改请求，不入侵用户环境，也不获得 broker 内部身份映射。它只利用正常服务过程中可见或可计算的信号进行离线分析。

### 3.2 Provider 可见信息

provider 可以看到：

- 请求消息内容；
- system/user/assistant/tool messages；
- tool schema 和 tool output；
- 请求到达时间或近似顺序；
- tokenized text、长度和罕见 token；
- cache-like bucket 或 prefix overlap proxy；
- 局部 embedding 或轻量语义表示。

provider 看不到：

- broker 内部 user ID；
- broker 内部 org ID；
-真实 trace/session ID；
- evaluation ground truth；
- 数据集 provenance；
- 人工注入标签。

### 3.3 任务定义

给定一个匿名请求集合 `R = {r_1, ..., r_n}`，每个请求只包含 provider-visible fields。攻击目标分为两步。

第一步是 linkage。provider 输出若干 cluster，用于近似恢复：

- session/workflow；
- project/repository；
- owner-like organization；
- 在带有受控真值的 Dataset B/Synthetic A 中的 user。

第二步是 reconstruction/profile。provider 对每个 cluster 恢复：

- workflow turn ordering；
- reconstructed workflow summary；
- 技术 profile fields，例如 languages、frameworks、build tools、package managers、repo names、CI/CD systems、service hints；
- 可用于后续持续跟踪的 watchlist tokens。

### 3.4 Claim 边界

本文从一开始限定以下边界。

第一，Open-SWE 的 `org_id` 是 GitHub owner 或 owner-like label，不是企业组织。因此本文在真实 Open-SWE 结果中使用 owner-like organization 说法，而不宣称恢复真实企业组织。

第二，Open-SWE 不提供可靠真实 user identity ground truth。因此 Open-SWE 上的真实 user-level reconstruction 应报告为 N/A。本文只在 Dataset B 和 Synthetic A 上评估 user-level mechanism。

第三，Open-SWE 不暴露真实 provider cache telemetry。本文的 cache stage 是 provider-view 近似或实现原型，用于研究低成本候选生成逻辑，而不是声称获得真实生产 provider 的 cache hit 数据。

## 4. 方法：CARP 低成本 Provider-Side Reconstruction Pipeline

本文方法围绕 CARP（Cache-Anchored Rarity Percolation）构建。CARP 的核心不是简单堆叠若干已知特征，而是把 provider 在推理中可见或可廉价计算的信号组织成一个受预算约束的稀疏图构建问题：先用 cache-like anchors 缩小候选空间，再用 rare structural tokens 和 context-growth signals 建立候选边，最后在图上进行 percolation 得到 workflow、user、project 和 owner-like clusters。provider 不对所有请求做昂贵全局匹配，而是逐层缩小候选空间。

CARP 可写成一个稀疏边打分过程：

```text
score(i, j) =
  alpha * rarity_lift(i, j)
+ beta  * context_growth(i, j)
+ gamma * tool_schema_match(i, j)
+ delta * time_length_compatibility(i, j)
+ eta   * local_semantic_agreement(i, j)
```

这个 score 不在所有请求对上计算，而只在 cache anchors、倒排索引和 bounded local refinement 产生的候选对上计算。这样，方法的成本主要由候选边数量而非 `n^2` 请求对数量决定。

### 4.1 粗分桶：cache-like 与结构信号

第一层使用低成本 bucket。请求可以按以下信号进入候选桶：

- cache-like prefix bucket；
- 请求长度或 token count；
- tool/schema signature；
- 时间窗口；
- coarse semantic or structural signature。

这些 bucket 的作用不是直接判定同一用户，而是避免全量 pairwise comparison。对于 provider 而言，这些信号要么已在推理中计算，要么可以由 tokenization 和轻量 hash 得到。

### 4.2 候选边生成：罕见 token 与准标识符

在每个候选桶内，方法提取稳定但低频的 token 和结构符号。典型信号包括：

- workspace paths；
- repo slug 和 owner/repo；
- file paths；
- package names；
- code symbols；
- tool names；
- error strings；
- domain/service-like tokens。

当两个请求共享足够稀有的结构 token 时，方法在它们之间建立候选边。这个阶段可以用 hash map 和倒排索引实现，避免全局 dense similarity。

在非代码工具 Agent 中，结构符号不再主要表现为 repo/path，而表现为业务实体锚点。本文实现的 business-entity refinement 将 `customer_ref` 视为 user-level 强锚点，将稳定的 order/reservation/product alias、`queue` 和 `internal_domain` 视为 business-project 强锚点，将 `tenant` 以及从 `account_cache` 解析出的 tenant alias 视为 org-level 强锚点。局部 cache bucket 阶段完成后，CARP 再构造一个只包含强实体锚点的小型图，使同一实体能够跨 user/org/shared cache bucket percolate。若同一 `account_cache` 与多个 `customer_ref` 共现，则将其判定为歧义 alias 并禁止 user-level union。相反，`loyalty_tier`、`region`、单独的 `service_line` 和随机 `case_id` 只适合作为画像证据或弱语境，因为它们的桶过大或跨实体复用，不能作为 union 条件。这个设计提高召回的同时保持 T3 三层链接的高精度。

### 4.3 上下文链式恢复：cumulative context 与 turn ordering

LLM Agent 常将前序消息和工具输出放入后续请求。方法利用 shingle overlap、context growth 和 timestamp ordering 恢复 workflow 内部顺序。对于 cumulative view，同一 workflow 的请求通常具有更强上下文重叠；对于 turn_delta view，这种信号被削弱，因而可以作为负向控制。

### 4.4 轻量语义 refinement

在候选边已经大幅减少搜索空间后，方法可以加入轻量 semantic refinement，例如局部 embedding proxy 或小模型相似度。本文强调语义不是第一步的全局搜索，而是候选集合内的 refinement。这样符合 provider-side 低成本叙事。

### 4.5 Profile reconstruction

完成 linkage 后，provider 将 cluster 内的请求聚合并抽取 profile fields。除原有平面关键词规则外，本文实现 structured-evidence profiler，将 lexical mention、文件扩展名、manifest/config、命令、repository/workspace、service 和 domain detector 的证据按请求聚合；每个预测值保留 request-level evidence、detector source 和 confidence score。

为避免画像阶段只依赖人工规则，本文进一步实现 calibrated dense-semantic profiler。该方法按 message/line 提取有技术线索的 evidence spans，用固定技术 ontology 和 `all-MiniLM-L6-v2` 做 dense retrieval，并通过否定/迁移语境过滤、跨请求支持数和高置信阈值决定是否接受画像值。阈值仅在按 org 隔离的 calibration split 上选择，再在未参与调参的 test orgs 上报告。该方法仍是 evidence retrieval，而不是允许模型自由生成企业属性；所有输出继续绑定 request-level span 和 similarity score。

## 5. 数据集与评估设计

本文使用四层数据，分别回答不同问题。

### 5.1 Open-SWE-Traces Adapted：真实 Agent Trace 证据

Open-SWE-Traces 是本文真实数据主线。我们将其适配为 provider-view API logs，保留 `attack_view.jsonl` 作为 provider 可见内容，将 labels 和 provenance 放在 `ground_truth.jsonl` 与 `request_provenance.jsonl` 中。Open-SWE 支持 workflow、project/repo 和 GitHub owner-like labels，但不支持可靠 user labels。

Open-SWE 用于回答：

- 真实 Agent traces 是否可被重新关联为 workflow/session？
- project/repo 和 owner-like linkage 是否可恢复？
- cumulative context 和 workspace/repo artifacts 分别起什么作用？
- provider_lowcost 是否明显优于 random controls？
- 能否恢复 turn ordering 和部分 technical profile？

### 5.2 Open-SWE User Overlay Dataset B：Trace-Grounded User-Level 机制证据

由于 Open-SWE 没有可靠 user_id，本文构建 Dataset B：在真实 Open-SWE trace substrate 上注入受控 user/profile truth，并按时间混合请求形成 longitudinal snapshots。Dataset B 有两个主要设置：

- U3：multi-signal main setting，保留较多可区分 user-level signals；
- U4 hard-shared：刻意共享或混淆 user-specific signals，用于检验 user-level linkage 的难度边界。

Dataset B 用于回答：

- 如果真实 Agent traffic 中存在稳定 user-level signals，provider_lowcost 能否在混合请求池中恢复 user clusters？
- 随着观察请求从 1k 增加到 4k、8k、12k，linkage 如何变化？
- 当 user-specific signals 被共享化后，user reconstruction 是否下降？

Dataset B 是 semi-synthetic，因此不能被表述为真实用户身份恢复证据。它的作用是填补真实 Open-SWE 缺少 user ground truth 的评估空白。

### 5.3 Synthetic Dataset A：完整真值下的控制实验

Synthetic Dataset A 提供完整 org/user/project/workflow/profile truth，用于控制规模、难度和 profile richness。它不作为真实世界主证据，而用于验证机制、做 difficulty sweep 和 profile evaluation。

### 5.4 tau-bench Historical：非代码工具 Agent 外部有效性

为回应 Open-SWE 偏软件工程、repo/workspace artifacts 过强的问题，本文增加 tau-bench historical trajectories 作为异构非代码数据。tau-bench 包含 airline 和 retail 两类工具 Agent 任务，每条轨迹包含 system policy、用户对话、assistant 响应和 tool observations。我们将 historical trajectories 转换成相同的 provider-view API log schema：每个 assistant turn 之前的累计消息构成一次 provider 可见 LLM 请求，ground truth 和 provenance 仍单独存放。

tau-bench 的作用不是替代 Open-SWE，而是回答一个外部有效性问题：如果没有 GitHub repo、workspace path 和代码文件结构，CARP/provider_lowcost 是否仍能恢复 workflow/session？同时，tau-bench 的 user/project/org 标签与 Open-SWE 不同，project 当前只是业务实体 proxy，org 主要是 airline/retail domain。因此，本文将 tau-bench 结果用于验证非代码 session reconstruction，而不把当前 user/project/org 结果表述为完成的组织画像实验。

需要说明的是，当前使用的是 tau-bench 官方仓库提供的 historical airline/retail trajectories；该仓库 README 已提示这些任务版本过期，最新版迁移到 tau^3-bench。本文因此把该实验定位为真实异构轨迹补充，而不是最新 tau-bench leaderboard 复现实验。

在直接 historical conversion 之外，本文还构建 tau-bench T3 overlay。T3 与 Open-SWE User Overlay 的定位类似：真实 tau-bench 对话和工具轨迹作为基底，额外注入 synthetic tenant/org、customer/user、business project/case-line 三层真值和 provider-visible account/case context。T3 当前包含 24 个 tenant/org、140 个 customer/user、72 个 business project/case-line、660 个 workflow 和 7099 个 provider-view requests，并提供 1000、2500、5000、7099 四个时间快照。T3 不代表真实 tau-bench 用户身份恢复证据，而是用于评估非代码场景下三层组织构建机制。

### 5.5 指标

Linkage 使用 pairwise precision、recall、F1、purity 和 cluster count。Turn ordering 使用 adjacent accuracy 和 pairwise ordering accuracy。Profile reconstruction 使用字段级 precision、recall、F1 和 evidence coverage。我们还报告 bootstrap confidence intervals、runtime、RSS、candidate pairs 和 candidate link events。

## 6. 实验结果

### 6.1 RQ1：匿名 Agent 请求能否被重新关联？

在 Open-SWE sample100 fixed-turn setting 上，provider_lowcost 明显高于 random controls。`provider_lowcost` 在 session level 上达到 precision 0.789、recall 1.000、F1 0.882；project 和 org owner-like level 上 F1 均为 1.000。相比之下，random 在 session/project/org 上的 F1 分别约为 0.016、0.013、0.014，oracle-size random 也只有 0.012、0.008、0.007。

这说明低成本 provider-side pipeline 并不是简单利用 cluster size 或随机碰撞，而确实使用了内容侧信号进行 linkage。

在 Open-SWE 2x2 scaffold/split matrix 中，OpenHands traces 表现出强烈的 workspace/repo artifact leakage。以 OpenHands minimax_m25 1000 workflows 为例，cumulative raw view 中 hybrid session F1 为 0.985，project F1 为 0.996，org F1 为 0.987；去除 workspace 后，project 和 org F1 降为 0。OpenHands qwen35_122b split 也表现出类似模式。SWE-agent splits 中，cumulative session linkage 仍有约 0.700 到 0.711 的 F1，但 project/org reconstruction 在当前 low-cost attacks 下为 0。

这一结果说明 linkability 不是所有 Agent scaffold 都完全相同。OpenHands 暴露了更强的 workspace/repo artifacts；SWE-agent 在当前数据和攻击下主要体现 cumulative session linkage，而没有显著 project/owner-like reconstruction。这种差异加强了论文的可信度：方法不是在所有数据上无条件报喜，而是反映了不同 Agent framework 的暴露面差异。

### 6.2 RQ2：哪些信号在起作用？

Feature ablation 显示，不同 linkage level 依赖不同信号。

在 cumulative view 中，完整 hybrid 的 session F1 为 0.974，project/org F1 为 1.000。去除 repo IDs 后，project F1 降为 0，org F1 降至 0.109，但 session F1 仍保持 0.974。这说明 project/owner-like reconstruction 强烈依赖 repo/workspace artifacts，而 session reconstruction 还可以依赖上下文重叠和时间/长度等信号。

去除 shingles 后，session F1 降为 0，但 project/org F1 仍为 1.000。这说明上下文重叠对 workflow/session reconstruction 是关键，而 repo-like structural tokens 对 project/org linkage 是关键。去除 time/length 后 session F1 从 0.974 降至 0.789，表明时间和长度是辅助信号。

在 turn_delta view 中，session F1 降至 0.107，而 project/org 仍可达到 1.000。这与预期一致：turn_delta 削弱了 cumulative context，因此 workflow/session linkage 变难；但如果 repo/workspace artifacts 仍存在，project/org 仍容易恢复。

Turn ordering 结果进一步支持 cumulative context 的作用。cumulative view 中 timestamp/context pairwise ordering accuracy 为 0.847；去除 shingles 后没有可评估 clusters，ordering accuracy 为 0。turn_delta view 中可评估 clusters 更少，pairwise ordering accuracy 为 0.750，但样本对数显著下降。

因此，本文不应将结论表述为单一的“路径泄露”。更准确的结论是：Open-SWE 中 project/owner-like linkage 主要由 workspace/repo artifacts 驱动；workflow/session reconstruction 则依赖 cumulative context、shingle overlap、时间/长度和结构信号；Dataset B 和 Synthetic A 进一步评估 user-level signals 在有受控真值时的作用。

tau-bench historical sample200 进一步说明，workflow/session reconstruction 不完全依赖软件工程路径。在 2175 个非代码工具 Agent 请求、200 个 workflow 的真实 historical sample 上，provider_lowcost 的 session precision 为 0.523、recall 为 0.407、F1 为 0.458；random session F1 仅为 0.008，oracle-size random session F1 约为 0.006。`no_paths`、`no_repo_ids` 和 `no_tool_schema` 三个 feature ablation 下 session F1 保持 0.458，说明该数据中的 session linkage 主要来自 cumulative dialogue/tool context 与轻量语义/结构重复，而不是 repo/path 或 tool schema。与此同时，直接 historical conversion 的 user/project/org 标签较粗，不能支撑真实非代码组织画像结论；因此我们将三层实体构建放到 T3 overlay 中作为机制评估。

tau-bench T3 first-2500 overlay 进一步把非代码数据补成可评估三层结构。在 2500 个请求、234 个 workflow、108 个 user、66 个 project、24 个 org 的时间快照上，原始 bucket-local business refinement 的 user/project/org F1 为 0.214/0.159/0.297。加入跨 cache 桶强实体 percolation 后，三者提升到 0.771/0.686/0.777，其中 precision 保持为 0.952/0.998/1.000，recall 提升到 0.648/0.522/0.635。该步骤只增加 5,612 条类型化句柄候选边和 1,892 次跨桶 union，并拒绝了 89 个与多个 customer 共现的歧义 account-cache alias。session F1 基本不变，说明改进针对的是跨 workflow 的实体层，而非利用宽字段扩大 session cluster。

跨快照实验进一步验证了持续跟踪路径。使用 first-2500 的 provider_lowcost clusters 建立 entity watchlist，并只在后续请求上进行匹配时，全部后续窗口的 user/project/org precision 为 0.950/1.000/1.000，recall 为 0.557/0.709/0.779，F1 为 0.702/0.830/0.876；可覆盖 98.1%/100%/100% 的已见实体 target。该结果说明 provider 可以把冷启动中发现的 customer/order/queue/tenant 锚点转化为高精度的纵向筛选器，而不需要把 `region`、`loyalty_tier`、单独 `service_line` 或随机 `case_id` 当作强链接依据。

### 6.3 RQ3：CARP/Provider-Lowcost 方法是否具备可扩展路径？

本文区分 high-fidelity baseline 和 scalable provider method。`hybrid` 方法用于诊断和上界式分析，但不是大规模 provider claim 的核心。CARP 的当前实现对应代码中的 `provider_lowcost`，它才是本文的 scalable provider-side method。

在 Open-SWE sample100 上，provider_lowcost 处理 400 evaluated requests 的 feature/attack 时间约为 7.656 秒，session F1 为 0.882，project/org F1 为 1.000。对于 Dataset B，我们进一步运行 cache-bucket streamed provider_lowcost。

在 Dataset B U3 12k streamed run 中，feature extraction 为 195.175 秒，linkage 为 77.458 秒，cache scan 为 17.660 秒，peak RSS 为 1301.168 MB，candidate pairs 为 361,997，candidate pair link events 为 392,634。对应 F1 为：session 0.691、user 0.281、project 0.639、org 0.604。

在 U4 hard-shared 12k streamed run 中，feature extraction 为 153.410 秒，linkage 为 69.836 秒，cache scan 为 9.764 秒，peak RSS 为 1373.973 MB，candidate pairs 为 366,211，candidate pair link events 为 362,943。对应 F1 为：session 0.602、user 0.029、project 0.566、org 0.541。

更重要的是候选对数量。12,000 个请求的 naive all-pairs comparison 需要 71,994,000 个请求对。CARP/provider_lowcost 在 U3 中只考虑 361,997 个候选对，约 30.166 candidate pairs/request，对比 all-pairs 减少约 198.880x；在 U4 中只考虑 366,211 个候选对，约 30.518 candidate pairs/request，减少约 196.592x。按当前单机 prototype 的记录时间线性外推，U3 约为 6.726 CPU-hours / 1M requests，U4 约为 5.399 CPU-hours / 1M requests。该数字不是云成本报价，而是硬件无关性更强的 CPU-time/candidate-pair 量级报告。

U3 materialized budgeted 12k run 的 peak RSS 为 3333.051 MB，而 streamed run 将 U3 12k peak RSS 降至约 1301 MB，并保持同一 provider_lowcost linkage output。这说明 naive materialization 会带来明显内存压力，而 cache-bucket streaming 是更合理的 provider-scale 实现方向。

本文不宣称当前 prototype 已证明互联网级流量处理能力。更准确的说法是：我们实现并测量了一个避免 naive all-pairs comparison 的 provider-style sparse candidate generation pipeline，并在 12k longitudinal overlays 上展示了可扩展实现路径；真实 provider 可以在生产系统中用 cache queues 和 streaming indexes 更高效地实现同类逻辑。

### 6.4 RQ4：User-Level 机制在真实 Trace 基底上是否可评估？

Open-SWE 自身没有可靠 user_id，因此真实 Open-SWE user-level reconstruction 不能评估。Dataset B 用于回答机制问题。

在 U3 multi-signal setting 中，provider_lowcost streamed results 随请求量增加，session F1 从 1k 的 0.240 增至 12k 的 0.691；project F1 从 0.762 降至 0.639，org F1 从 0.685 降至 0.604；user F1 在 0.265 到 0.296 之间，12k 时为 0.281。U3 12k bootstrap CI 显示，session F1 的区间为 [0.669, 0.710]，user F1 为 [0.256, 0.300]，project F1 为 [0.624, 0.655]，org F1 为 [0.589, 0.619]。

在 U4 hard-shared setting 中，session F1 仍随请求量从 0.184 增至 0.602，project/org F1 保持在约 0.54 到 0.61，但 user F1 始终很低，12k 仅为 0.029，bootstrap CI 为 [0.025, 0.034]。这说明当 user-specific signals 被刻意共享或混淆时，user-level reconstruction 不会自然成功。该负向结果很重要：它表明 Dataset B 并不是通过简单注入标签让攻击无条件成功，而是在不同难度下呈现明确边界。

因此，本文的 user-level 结论应写为：Open-SWE-grounded semi-synthetic overlay 显示，在真实 Agent trace substrate 上，如果存在可区分 user-level signals，provider 可以部分恢复 user clusters；但当这些信号被 hard-shared 混淆时，user-level recovery 显著下降。真实 Open-SWE 上的 user-level reconstruction 仍为 N/A。

### 6.5 RQ5：热启动后能否持续跟踪？

冷启动聚类只是 provider 攻击链的第一步。现实 provider 一旦在早期流量中发现 cluster，就可以从 cluster 中抽取 watchlist tokens，在后续流量中进行更低成本的筛选。我们因此增加了 Dataset B warm-start watchlist 评估：用较早 snapshot 的 provider_lowcost clusters 建立 profile-token watchlist，再只在后续新增请求上测试 relinking。

当前结果更适合作为边界证据而非强正结果。使用轻量 profile anchors 时，project/org 的高置信 relinking precision 可以较高，但 coverage 较低。例如 U3 从 first_1000 到 first_4000 的 project-level watchlist precision 为 0.936、recall 为 0.240、F1 为 0.381；org-level precision 为 0.925、recall 为 0.143、F1 为 0.248。U4 同一窗口 project-level precision 为 0.932、recall 为 0.181、F1 为 0.304；org-level precision 为 0.938、recall 为 0.110、F1 为 0.197。相比之下，user-level warm-start precision 和 recall 都较弱。这与 Dataset B 的主 linkage 结果一致：project/org anchors 比 user-specific anchors 更稳定，而 user-level 跟踪在 hard-shared 设置下尤其困难。

因此，warm-start 目前支持一个谨慎结论：provider 可以用 profile-derived watchlist 对部分后续 project/org-like 请求进行高精度、低覆盖筛选，但当前轻量 watchlist 还不能可靠地对所有后续请求做 user-level 归属。它是持续画像风险的下界和边界分析，而不是完整热启动攻击上界。

进一步的 target-centric retrieval 诊断表明，warm-start 本身并非天然不利。用早期真实同实体请求直接构造 `truth_text` watchlist 时，U3 first_1000 到 first_4000 的 user-level precision@50 为 0.444、recall@50 为 0.663、hit@50 为 0.941，候选对相对全量 target-request pair 减少约 74x。用 provider_lowcost 预测簇继承 watchlist 时，同一设置下 user-level precision@50 为 0.382、recall@50 为 0.525、hit@50 为 0.917，仍有攻击价值，但弱于 truth_text 上限。U4 hard-shared 设置下降明显，说明低结果更像是用户信号共享化和预测簇纯度问题，而不是 warm-start 威胁模型本身无效。

### 6.6 RQ6：关联后的画像能恢复到什么程度？

原始 rule profiler 在 Open-SWE turn-delta profile run 的可评估技术字段上，audited micro precision/recall/F1 为 0.829/0.499/0.623。它对 build tools 较强，但会漏掉只通过 `.py`、`pyproject.toml`、`package.json`、`go.mod`、`Cargo.toml`、workspace/repository 等结构证据出现的字段，service names 也几乎无法恢复。

structured-evidence profiler 将多个独立 detector 聚合后，在相同 predicted org clusters 上达到 audited micro precision/recall/F1 0.825/0.794/0.809。具体而言，languages F1 从 0.526 提升到 0.788，frameworks 从 0.659 提升到 0.855，package managers 从 0.787 提升到 0.994，CI/CD 从 0.600 提升到 0.988，service names 从 0.003 提升到 0.562。使用 truth org clusters 时 micro F1 为 0.812，与 predicted-cluster 的 0.809 接近，说明在这组数据上剩余误差主要来自 profile ontology/truth coverage 和 detector precision，而不是 linkage cluster 质量。

Dense-semantic profiler 使用 124 个 calibration org 和 432 个未见 test org。模型在 3,028 条 test requests 上选择阈值 0.58、最少 3 条请求支持；structured 和 semantic predicted-cluster micro F1 均为 0.807，semantic truth-cluster F1 为 0.809。该结果是一个重要负向增量结果：在当前固定 ontology 上，MiniLM 没有进一步提高 benchmark F1。它新增的 4 个预测都属于 `go test`，虽然在固定 profile truth 中被计为 false positive，但对应 span 分别包含 `_test.go` 文件、Go `testing.go` 栈或明确的测试文件错误，因此具有显式 provider-visible artifact 支持。这说明语义模型主要暴露了 truth proxy 的覆盖缺口，而不是当前 linkage 或 structured detector 的明显缺口。

成本上，语义实验从 4,000 个请求提取 31,950 个 spans，其中 21,507 个唯一 spans；MiniLM CPU embedding 用时约 106.7 秒，峰值 RSS 约 2.27 GB。由于该步骤只在 CARP 已形成的 cluster 上运行，并且 embedding 可以缓存，这一成本符合第二阶段允许更高预算的设定，但明显高于结构化 detector。

这表明 Open-SWE 支持的是部分 technical profile reconstruction，而不是完整企业画像。工具链、包管理器、构建系统和 repo names 更稳定；service names 等更接近业务或内部环境字段，在当前数据中较弱。

Synthetic Dataset A 的 controlled matrix 显示，在 full-truth synthetic setting 中，profile_micro_f1 可达到约 0.905 到 0.930，user F1 为 1.000。这一结果不应作为真实世界主证据，而说明当 profile truth 完整且信号可控时，linkage 后的 profile reconstruction 机制是可行的。

Qualitative redacted profile examples 可用于论文中展示 provider 能从 cluster 中看到的技术线索类型，但定量结论应以 profile table 为准。

### 6.7 RQ7：哪些防御有效，代价是什么？

我们将防御实验表述为 content-side linkage defense frontier，而不是完整生产防御系统。目标是映射哪些内容侧准标识符必须被打断，以及对应 utility proxy 代价。Defense utility frontier 显示，单纯 secret filtering 几乎不影响 linkage。M1 后 hybrid session/project/org F1 与 M0 基本相同，说明攻击不依赖传统 secrets。

Entity redaction M2 将 session F1 从 0.974 降至 0.165，并使 project/org F1 降至 0，但 tool_char_retention 仍为 0.858。Context minimization M3 保持 session/project/org F1 约为 0.974/1.000/1.000，但 token_retention 降至 0.131，说明仅压缩部分上下文未必能消除稳定结构信号。Combined M6 将 session F1 降至 0.030，project/org F1 为 0，但 tool_char_retention 仅为 0.043。

Selective workspace/path mitigation 更能说明问题。M7_WORKSPACE_STABLE 将 project/org F1 降至 0，但 session F1 仍为 0.974，说明稳定占位符或其他上下文信号仍可保持 session linkability。M8_WORKSPACE_SESSION 将 session F1 降至 0.593，project/org 为 0。M9_PATH_TYPE_ONLY 将 session F1 降至 0.529，project/org 为 0。

这些结果支持一个现实防御结论：仅删除显式身份字段不够；防御必须处理稳定 workspace/repo/path quasi-identifiers，并同时考虑 cumulative context 的保留策略。过强的 redaction 可以降低 linkage，但会损害任务 utility；稳定 redaction placeholder 也可能形成新的 linkability。

## 7. 讨论

### 7.1 这不是“语义泄露万能论”

本文的真实数据结果显示，Open-SWE 中 project/owner-like reconstruction 很大程度上由 workspace/repo artifacts 驱动。我们不应把结果包装成“任意语义内容都足以恢复组织”。更严谨的说法是，LLM Agent 请求暴露的是 multi-signal linkage surface，其中路径、repo、代码符号、上下文重叠、tool/schema、时间/长度和语义线索共同作用。不同任务和 Agent scaffold 中，主导信号不同。

### 7.2 为什么 Open-SWE 的限制反而重要

Open-SWE 没有真实 user_id，org label 也只是 GitHub owner。这看似削弱论文，但如果主动承认，反而让实验设计更可信。真实 Open-SWE 用于证明真实 Agent traces 中存在 workflow/project/owner-like linkability；Dataset B 用于补充 user-level mechanism；Synthetic A 用于完整 truth 控制实验。三者分工明确，避免把半合成证据冒充真实证据。

### 7.3 Provider 的持续画像风险

一次请求的泄露可能有限，但 provider 的优势在于持续观察。只要它能把后续请求关联到已有 cluster，就可以不断补全 profile，并维护 watchlist tokens。长期看，风险从单次 prompt privacy 变为 longitudinal profile accumulation。

### 7.4 对系统设计的启示

如果系统只依赖 broker 隐藏显式身份，仍然会留下内容侧关联面。更合理的设计需要同时考虑：

- 路径和 repo identifiers 的最小化；
- workspace placeholders 是否稳定；
- cumulative context 的长度和内容选择；
- tool outputs 中环境状态的脱敏；
- broker mixing 是否只影响时间信号而无法影响内容信号；
- privacy/utility frontier，而不是单点 redaction。

### 7.5 伦理与治理含义

本文研究的是 provider-as-attacker 威胁模型，因此伦理边界必须明确。我们不尝试识别真实个人，也不把 Open-SWE 的 GitHub owner-like label 表述为真实企业身份。Dataset B 的 user labels 是受控注入的 synthetic overlay，只用于机制评估。公开结果应以聚合表和 redacted examples 为主，不发布可反查个人或组织敏感信息的原始片段。

从治理角度看，本文结果说明 broker-side identity stripping 需要配合 provider-side log governance。模型 API provider 应限制原始 Agent logs 的保留时间和访问范围，审计内部聚类/画像分析，明确禁止未授权 customer re-identification，并在 broker/provider 合同中规定 content-side profiling 的用途边界。这些措施不能替代技术防御，但可以降低 provider 正常服务权限被扩展为持续画像能力的风险。

## 8. 相关工作占位

正式论文需要补充以下方向的引用：

- LLM privacy 和 prompt leakage；
- membership inference / data reconstruction；
- traffic analysis 和 metadata-based linkage；
- browser fingerprinting / quasi-identifier linkage；
- code model privacy 和 repository leakage；
- LLM Agent security、tool-use risks、prompt injection；
- privacy-preserving inference gateway、broker、confidential computing；
- log anonymization 和 k-anonymity/differential privacy 的局限。

本文与这些工作的区别在于，我们关注的是 LLM Agent API provider 的冷启动内容侧重建：攻击者不是外部窃听者，而是正常模型服务方；目标不是单条 prompt 中的 secret，而是跨请求 workflow linkage 和 profile accumulation。

## 9. 局限性

本文存在以下局限。

第一，Open-SWE 的 owner-like org label 不能代表企业组织。本文所有真实数据组织级结论都应表述为 GitHub owner-like linkage。

第二，Open-SWE 缺少可靠 user_id，因此真实 user-level reconstruction 不能在该数据集上评估。Dataset B 只是 trace-grounded semi-synthetic benchmark。

第三，cache-like signal 是 provider-view approximation，而非真实生产 provider cache telemetry。

第三点补充，tau-bench historical 使用的是官方 historical trajectories，而不是最新 tau^3-bench 任务版本。它适合证明非代码工具 Agent 中也存在 session-level content linkage。T3 overlay 的 entity percolation 和 watchlist 已显著提高 user/project/org 覆盖，但其三层标签仍是 trace-grounded semi-synthetic mechanism evidence，不支撑“恢复真实 tau-bench 用户身份或真实企业组织”的强 claim。

第四，当前 runtime/cost instrumentation 已覆盖 sample100、Dataset B streamed scale rows 和部分 reservoir timing，但 older original Open-SWE longitudinal rows 仍缺少完整 wall-clock 和 candidate-edge instrumentation。

第五，structured-evidence profiler 已明显强于平面规则基线。MiniLM semantic profiler 提供了按 org 隔离的 NLP 对照，但没有提高固定 benchmark F1，并揭示了若干 truth proxy 未覆盖的显式测试 artifact。两者都使用固定技术 ontology，不能代表生成式 LLM profiler 的上界，也不能代表完整企业业务画像。

第六，defense evaluation 当前是 content-side linkage defense frontier，使用 token retention、message retention 和 tool character retention 等 utility proxies，尚未包含真实 task success、latency、用户体验和部署成本。

第七，warm-start watchlist 当前是轻量 profile-token 下界实验。它显示 project/org-like 后续请求可以被高精度、低覆盖筛选，但还不能代表最强 provider 热启动攻击，也不能支撑强 user-level 持续跟踪结论。

第八，tau-bench T3 的 customer/order/queue/tenant entity percolation 和跨时间 watchlist 已将高精度冷启动簇扩展为更高覆盖的持续筛选结果，但这种提升依赖 overlay 中受控出现的稳定业务锚点。真实业务系统中的实体格式、生命周期、共享账户和字段缺失会更复杂，仍需在更新的真实非代码 Agent 数据上验证。

## 10. 结论

本文研究了 broker 去身份化条件下 LLM Agent API logs 的 provider-side reconstruction 风险。我们发现，去除显式 user/org/session identifiers 并不足以防止内容侧关联。Agent 请求中的 workspace/repo artifacts、代码符号、tool outputs、时间/长度和 cumulative context 可以形成稳定 linkage surface，使冷启动 provider 能够重建 workflow、project、owner-like organization，并进一步抽取技术画像。

我们的四层评估显示：真实 Open-SWE traces 支持 workflow/session reconstruction、project/repo linkage、owner-like linkage、turn ordering 和部分 technical profile reconstruction；tau-bench historical 与 T3 overlay 说明非代码工具 Agent 也存在 session-level content linkage，并且 provider-visible business anchors 可以通过跨 cache 实体 percolation 和 watchlist 形成高精度、较高覆盖的 tenant/customer/business-project linkage；Open-SWE-grounded Dataset B 在受控 user/profile truth 下揭示 user-level mechanism 及其边界；Synthetic Dataset A 提供完整 truth 下的控制验证。实验同时表明，攻击能力具有明显信号依赖性和数据集边界：Open-SWE 的 project/owner-like linkage 主要来自 workspace/repo artifacts，user-level recovery 只有在存在可区分 user signals 时才成立；T3 的增强结果仍属于 semi-synthetic 机制证据。

因此，LLM Agent 隐私防护不能只停留在删除显式身份字段。系统设计需要把稳定内容侧准标识符、cumulative context 和 tool environment exposure 纳入威胁模型，并在隐私降低与任务可用性之间进行系统权衡。

## 附：正式写作时的建议标题

可选中文标题：

1. 去身份化并不等于不可关联：模型 API 提供商视角下的 LLM Agent 请求重建风险
2. 匿名 Agent 请求池中的工作流重建：LLM API Provider 的内容侧关联风险
3. Broker 隐藏身份之后：LLM Agent API 日志的 Provider-Side Linkage 与画像重建

可选英文标题：

1. De-Identified Does Not Mean Unlinkable: Provider-Side Reconstruction of LLM Agent API Logs
2. Reconstructing Anonymous LLM Agent Workflows from Provider-Visible API Logs
3. Content-Side Linkage Risks in Brokered LLM Agent API Logs

## 附：正式论文表格映射

| 论文位置 | 当前 artifact |
| --- | --- |
| Main Open-SWE matrix | `docs/tables/open_swe_2x2_attack_matrix.md` |
| Provider-lowcost chain | `docs/tables/open_swe_provider_lowcost.md` |
| Controls and CI | `docs/tables/open_swe_controls_sample100.md`; `docs/tables/open_swe_controls_sample100_bootstrap_ci.md` |
| Feature ablation | `docs/tables/open_swe_gap_feature_ablation.md` |
| Turn ordering | `docs/tables/open_swe_gap_ordering.md` |
| Profile reconstruction | `docs/tables/open_swe_gap_profile.md`; `docs/tables/open_swe_profile_risk_levels.md` |
| Structured profile comparison | `docs/tables/open_swe_structured_profile_comparison.md` |
| Dense semantic profile comparison | `docs/tables/open_swe_semantic_profile_comparison.md`; `docs/tables/open_swe_semantic_profile_novel_evidence.md` |
| Runtime/cost | `docs/tables/open_swe_runtime_cost.md`; `docs/tables/open_swe_provider_lowcost_cost_model.md` |
| Dataset B linkage | `docs/tables/open_swe_user_overlay_linkage_summary.md` |
| Dataset B CI | `docs/tables/open_swe_user_overlay_12k_bootstrap_ci.md` |
| Dataset B warm-start watchlist | `docs/tables/open_swe_user_overlay_warm_start_watchlist.md`; `docs/tables/open_swe_user_overlay_warm_start_retrieval.md` |
| Dataset B profile | `docs/tables/open_swe_user_overlay_profile_reconstruction.md` |
| tau-bench historical non-code Agent | `docs/tables/tau_bench_historical_sample200_provider_lowcost.md`; `docs/tables/tau_bench_historical_provider_view_audit.md` |
| tau-bench T3 three-layer overlay | `docs/tables/tau_bench_overlay_t3_first_2500_provider_lowcost.md`; `docs/tables/tau_bench_overlay_t3_provider_view_audit.md` |
| tau-bench T3 entity percolation/watchlist | `docs/tables/tau_bench_t3_entity_percolation.md`; `docs/tables/tau_bench_t3_entity_watchlist.md` |
| Synthetic A | `docs/tables/synthetic_matrix_summary.md` |
| Appendix mitigation probes | `docs/tables/open_swe_defense_utility_frontier.md` |
