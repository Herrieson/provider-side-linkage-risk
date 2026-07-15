# LLM Agent API 场景下的内容侧去匿名化研究方案

## 0.研究初步思考

1. 目前LLM Agent已经被广泛使用了，绝大多数个人和企业并不自己部署模型，而是使用模型提供商的LLM  API服务，这就导致一点，即模型提供商可以看到发送给 LLM 的完整上下文，提供商可以通过聚合单一用户的所有 LLM 请求，按照时  间顺序或者上下文增加的变化，还原出一个 Agent 工作期间的完整上下文（这个是显然容易的），进而通过分析该 Agent 工作间的上下文（可能要聚合分析多个 Agent 的上下文），推断出 Agent 工作环境的信息，甚至是部署和使用Agent的用户的信息（公司的业务，环境等）。模型提供商通常宣称不会用于这些信息于训练，但是这些关键信息存在于外部实体，会对企业或个人造成极大的安全隐患，如果黑客攻破模型提供商数据库或者模型提供商自己愿意，就有可以根据推断出的信息来执行一些明显不利于用户的行为（例  如通过推断的系统环境来进行网络攻击，这在之前是需要漫长而隐蔽的主动扫描，非常容易暴露，或者在竞争中获得有利地位，因为知道了公司的关键内部信息）。

2. 我们默认采用的是这种架构（注意实际上情况并没有这么复杂，中转站B不一定存在，但是我们假设最复杂的情况，如果不考虑该情况，可以直接跳到第 5 段），多了一个中转站，分为三个实体：用户A，中转站B，模型提供商C；中转站负责收集用户A的请求，然后发送给模型提供商C，但是信息是加密的，中转站看不到具体的内容，中转站B只负责建立一一对应关系，它负责管理哪个LLM回复是应该发送给哪个用户，它接收用户的API KEY 和User ID 并验证，确保发送给C的请求已经是合法的；模型提供商C具有解密信息的能力，但是它不知道LLM输入对应的哪个用户，只能发给中转站B，这样中转站只有加密内容，提供商C得到的是被混在一起的海量LLM请求，这不保证提供商C不能继续分析，但是一定程度上加大了其成本和难度。

3. 接下来探讨一种让提供商能从海量LLM请求中以较低成本聚类特定用户的请求的方法（显然直接进行关键词或者向量匹配是成本极高的，而且我们默认是冷启动，即提供商初始没有建立任何用户画像，因此必须要先聚类挖掘）：提供商C可以根据缓存命中率来初步分组（提供商将缓存命中率在同一区间的归为一组，因为缓存命中率是常规LLM推理中被计算的，因此成本可以计为0），接下来提供商对同一组的文本，转成文本向量（这一步成本也是0，因为是LLM推理的一步），接着提供商可以通过对其中的向量进行统计，将含有同一罕见向量的文本聚类（这一步的计算量也不大，只需要一个散列算法即可），接着对每一文本组重复该步骤N次（视提供商心情而定），这样每一组的文本间有很大几率存在实际的关联。接下来提供商使用小的NLP模型或者LLM分析进行语义聚类，进一步关联特定文本。最后结合文本的时序以及上下文递增（第二轮对话包含第一轮的上下文）特定罕见Token，还原某一用户的Agent流。因此正如前文所说“提供商可以通过聚合单一用户的所有 LLM 请求，按照时间顺序或者上下文增加的变化，还原出一个 Agent 工作期间的完整上下文（这个是显然容易的）”

4. 提供商得到了单一用户的LLM请求序列后，就可以还原出 Agent 工作期间的完整工作流。提供商可以根据其关注的点（用户画像等），预设一些正则提取模板，构建一个环境重建器，环境重建器可以是一个小语言模型或者纯规则驱动，根据完整工作流补全模板的内容。之后提供商根据其兴趣（是否关注该用户），记录关键的Token，以便快捷的从后续的LLM请求中筛选到该用户的LLM请求，并持续补全画像。此外提供商可以进一步关联各个画像，将多个不同画像关联到同一实体。

5. 接下来我们继续来展开讨论其中最关键的推断用户画像的具体实现，提供商C获得用户完整Agent工作流后，可以根据关键词匹配，LLM模型辅助等方法将其快速分类到不同的桶中（不同的桶例如，个人开发者，企业开发环境，金融企业），对于不同的桶，有一套具体的处理方式，其中包含一些启发式构建方法。之后对于提供商感兴趣的用户，其可以长期维护。

6. 这就是我的大概思路，然后我打算发篇论文就是验证攻击存在（两阶段：1. 聚类为用户/组织级工作流；2. 通过工作流构建用户/组织的画像）+ 缓解方法。预计推出：1. 一个数据集，里面模拟了提供商收到的流量（后续研究可以使用这个作为 Benchmark）；2. 一个综合的防御方法；3. 详细的攻击方法；

## 1. 研究动机

当前 LLM Agent 已经被广泛用于软件开发、运维、数据分析、安全排查和办公自动化等任务。绝大多数个人和企业并不自行部署大模型，而是通过模型提供商的 LLM API 使用模型能力。这种架构带来一个核心隐私问题：模型提供商在推理阶段可以看到发送给 LLM 的完整上下文。

即使模型提供商承诺不会将用户数据用于训练，推理日志本身仍然可能成为高价值情报源。LLM Agent 的请求通常包含工作目录、代码片段、工具调用结果、错误日志、配置文件、内部服务名、项目路径、业务术语、数据库结构、部署信息和安全相关上下文。通过长期聚合这些请求，提供商或者攻破提供商日志系统的攻击者，可能还原 Agent 工作期间的完整工作流，并进一步推断出用户或组织画像。

本研究关注的问题不是“模型是否训练了用户数据”，而是：

> 在 LLM Agent API 使用中，模型提供商即使不知道显式用户身份，是否仍能通过请求内容、上下文递增关系、罕见环境特征、工具调用结构和时序信号，重建用户/组织级工作流，并进一步构建用户或组织画像。

## 2. 核心研究问题

### RQ1：匿名混合 LLM Agent 请求是否可以被聚类为用户级或组织级工作流？

在移除 API key、用户 ID、组织 ID、账单 ID、IP 等显式身份信息后，攻击者是否仍能仅凭明文上下文和低成本元数据，将混合请求池中的请求聚类为 session、user、organization 三个层级？

### RQ2：哪些信号对工作流重建最有贡献？

候选信号包括：

- 上下文递增关系；
- prompt / response / tool result 的重叠；
- 罕见 token、路径、域名、服务名、项目名、表名、代码符号；
- system prompt 和 tool schema 指纹；
- 请求时间序列和长度序列；
- 缓存相关侧信号；
- 语义 embedding 或主题相似度。

### RQ3：从重建出的工作流中能恢复多少用户/组织画像？

画像字段包括技术栈、项目结构、内部服务、业务领域、云平台、数据库、CI/CD、认证系统、内部域名、安全相关线索等。

### RQ4：哪些缓解方法有效，代价是什么？

评估上下文最小化、实体脱敏、工具输出过滤、请求混洗、延迟扰动、长度 padding、多提供商分片、缓存隔离等方法对聚类成功率、画像恢复率、任务成功率、token 成本和延迟的影响。

## 3. 威胁模型

### 3.1 参与实体

- **用户/企业 A**：使用 LLM Agent 完成开发、运维、数据分析、安全排查等任务。
- **中转站 B**：负责认证、计费、路由、请求响应映射。B 知道用户身份，但在理想化设定中看不到明文内容。
- **模型提供商 C**：执行模型推理，能看到明文 prompt、response、工具调用文本和部分推理侧元数据。
- **攻击者**：C 自身，或者攻破 C 日志系统的外部攻击者。

### 3.2 部署设定

#### D0：用户直连模型提供商

用户 A 直接调用模型提供商 C。C 可见：

- API key；
- account id / organization id；
- billing id / project id；
- IP、请求头、SDK 信息；
- 完整 prompt、response 和工具调用内容；
- token 长度、时间戳、模型参数、缓存指标等。

该设定是 baseline。在 D0 中，C 已经拥有显式身份，不需要复杂的内容侧聚类。

#### D1：通过匿名中转站 B 调用模型提供商

用户 A 通过中转站 B 调用 C。B 负责身份验证和请求映射，但不读取明文内容。C 能看到明文内容，但只看到来自 B 的混合流量，不直接知道请求属于哪个用户或组织。

该设定是本文核心场景。它用于验证：

> 即使显式身份被中转站隐藏，LLM Agent 请求内容本身是否仍然可链接。

### 3.3 提供商行为

#### A0：诚实但好奇的模型提供商

提供商正常提供模型服务，不篡改响应，不主动诱导用户泄露更多信息，也不直接攻击用户系统。但它会访问、保留并离线分析请求日志，用于用户画像、产品分析、商业情报、风险评估或内部研究。

本文主实验应优先聚焦该设定，因为它最克制，也最有说服力：

> 即使提供商只是被动观察正常请求，也可能重建用户/组织工作流。

#### A1：恶意或自适应模型提供商

恶意提供商除了被动分析，还可能主动操控模型响应，诱导 Agent 查询更多环境信息，例如目录结构、配置文件、Git remote、环境变量、依赖版本、内部文档等。

该设定可作为扩展实验或 upper bound，不应作为主贡献。

### 3.4 攻击者知识

- **Cold-start**：攻击者没有用户画像、组织名单、历史请求或 seed 线索，只能从混合日志中无监督聚类。
- **Warm-start**：攻击者已有少量 seed，例如某个公开域名、repo 名、项目名、组织名或历史请求片段。
- **Longitudinal**：攻击者可以长期观察请求流，并持续更新画像。

主实验建议采用 **D1 + A0 + cold-start**。

### 3.5 非目标

本研究不关注：

- 模型训练阶段的数据泄露；
- 模型记忆化用户 prompt 后泄露给其他用户；
- 网络层流量分析；
- 攻破用户本地机器；
- B 自身恶意且直接滥用身份信息；
- 通过 API key、IP、billing id 等显式身份直接关联用户。

## 4. 两阶段攻击框架

### 4.1 阶段一：Workflow Reconstruction

输入是混合匿名 LLM Agent 请求日志。攻击者不可见真实 org_id、user_id、session_id、turn_id。

攻击目标：

- 聚类为 session-level 工作流；
- 合并为 user-level 行为簇；
- 合并为 organization-level 行为簇；
- 在每个 session 内恢复 turn 顺序。

候选特征：

- **上下文包含关系**：后一轮 prompt 是否包含前一轮 prompt、response 或 tool result。
- **prefix overlap**：token 前缀重叠、最长公共前缀、rolling hash。
- **罕见离散特征**：路径、域名、URL、repo 名、服务名、表名、环境变量、错误栈、代码符号。
- **tool schema 指纹**：Agent 框架、工具名称、自定义工具参数结构。
- **system prompt 指纹**：固定系统提示词、企业规范、Agent 模板。
- **代码/日志指纹**：函数名、类名、包名、测试名、异常栈。
- **时间序列**：请求间隔、工作时间、burst pattern。
- **长度序列**：上下文递增导致的 token 长度增长曲线。
- **缓存侧信号**：cache hit tokens、prefix reuse、缓存命中模式。
- **语义特征**：embedding 近邻、主题相似度、任务类型分类。

推荐主攻击方法是图聚类：

```text
node = request
edge_weight(i, j) =
  w1 * rare_feature_overlap
+ w2 * prefix_overlap
+ w3 * semantic_similarity
+ w4 * temporal_closeness
+ w5 * tool_schema_similarity
+ w6 * cache_signal_similarity
```

之后使用 connected components、community detection 或 hierarchical clustering 得到候选簇，并在簇内根据时间戳和上下文包含关系恢复工作流顺序。

### 4.2 阶段二：Profile Reconstruction

输入是阶段一恢复出的 workflow clusters。

输出是结构化用户/组织画像：

```json
{
  "actor_type": "individual | startup | enterprise | unknown",
  "industry": [],
  "organization_clues": [],
  "project_names": [],
  "repo_names": [],
  "programming_languages": [],
  "frameworks": [],
  "package_managers": [],
  "databases": [],
  "cloud_providers": [],
  "internal_domains": [],
  "service_names": [],
  "file_paths": [],
  "environment_variables": [],
  "ci_cd_systems": [],
  "auth_systems": [],
  "business_clues": [],
  "customer_or_vendor_clues": [],
  "security_clues": [],
  "active_tasks": [],
  "confidence": {}
}
```

画像构建器可以分三档：

- **Rule-based profiler**：正则、字典、路径解析、URL/domain 提取、代码符号提取。
- **Small-model profiler**：轻量分类模型，用于行业、任务类型、技术栈分类。
- **LLM-assisted profiler**：使用 LLM 填充结构化 JSON，但实验中不能让其看到 ground truth。

画像字段按敏感等级分层：

- **L1 一般技术信息**：语言、框架、包管理器。
- **L2 项目信息**：项目名、repo 名、模块名、测试名。
- **L3 组织信息**：行业、业务线、内部术语、供应商/客户线索。
- **L4 安全环境信息**：内部域名、认证系统、部署环境、服务拓扑、漏洞线索。
- **L5 高危信息**：API key、token、连接串、客户数据。

研究重点不应依赖 L5。即使只恢复 L2-L4，也足以构成严重组织情报泄露。

## 5. 数据集设计

### 5.1 Dataset A：合成组织级 Agent 日志

主数据集，用于保证 ground truth 完整。

建议初始规模：

```text
Organizations: 20
Users per organization: 5-10
Projects per organization: 2-4
Workflows per user: 20-50
Turns per workflow: 5-15
Total requests: 50k-150k
```

每个组织应有独立但可控的环境指纹：

- 行业：finance、healthcare、ecommerce、SaaS、security、logistics；
- 内部域名：`*.corp.local`、`*.internal`、`*.prod`；
- repo 名：`risk-engine`、`billing-core`、`auth-gateway`；
- 服务名：`payment-router`、`fraud-score`、`claims-api`；
- 数据库：PostgreSQL、MySQL、ClickHouse、Redis；
- 云平台：AWS、GCP、Azure、自托管；
- CI/CD：GitHub Actions、GitLab CI、Jenkins；
- 路径风格：`/home/user/work/org/project/...`；
- 工单 ID：JIRA-like 或 Linear-like 编号；
- 日志格式：组织特有 trace id、service prefix。

任务类型：

- bug fixing；
- test failure diagnosis；
- dependency upgrade；
- API integration；
- database migration；
- deployment config update；
- security review；
- incident debugging；
- documentation update；
- data analysis；
- CI failure repair；
- auth / permission logic change。

每个 workflow 生成多轮 Agent 上下文：

```text
turn 1: user task + project background
turn 2: assistant plan + tool result: ls / tree / grep
turn 3: file snippet + error log
turn 4: patch discussion + test output
turn 5: new error + config detail
turn 6: final fix + summary
```

保存两份数据：

```text
attack_view.jsonl   # 攻击者能看到的匿名日志
ground_truth.jsonl  # org_id / user_id / project_id / session_id / turn_id
```

### 5.2 Dataset B：开源项目半真实 Agent 日志

使用公开 GitHub 项目构造更真实的代码和错误日志。

方法：

- 选择 30-50 个开源项目；
- 每个项目模拟一个组织或组织内项目；
- 从 issue、README、tests、CI error、commit diff 中构造 Agent 任务；
- 生成多轮请求；
- 保留 ground truth。

该数据集用于验证攻击不是只在人工模板数据上成立。

### 5.3 Dataset C：受控人工实验

小规模现实验证：

```text
Participants: 5-10
Sandbox projects: 5-10
Workflows per participant: 5-10
```

参与者必须知情同意，项目不包含真实秘密或真实客户数据。

## 6. 实验设计

### 6.1 实验一：匿名聚类可行性

设定：

```text
D1 + A0 + cold-start + M0
```

目标：验证中转站隐藏显式身份后，攻击者是否仍可通过内容侧信号重建 session/user/org 级工作流。

### 6.2 实验二：特征消融

比较以下方法：

- Temporal baseline；
- Semantic baseline；
- Rare-feature baseline；
- Prefix-overlap baseline；
- Tool/system-prompt baseline；
- Hybrid attack。

消融设置：

- Hybrid - rare features；
- Hybrid - prefix overlap；
- Hybrid - temporal；
- Hybrid - tool schema；
- Hybrid - response text；
- Hybrid - cache signal；
- Hybrid - semantic embedding。

预期结论：

> embedding 不是最关键的；上下文递增、罕见环境特征、工具/路径指纹更强、更便宜、更稳定。

### 6.3 实验三：规模与噪声敏感性

变量：

```text
Number of organizations: 5, 20, 100
Users per organization: 1, 5, 20
Workflows per user: 5, 20, 100
Turns per workflow: 3, 8, 15
Noise requests: 0%, 25%, 50%
Shared templates across users: low / medium / high
Shared open-source projects: yes / no
Time mixing window: 0 min, 10 min, 1 hour, 24 hours
Entity redaction rate: 0%, 50%, 90%, 100%
```

### 6.4 实验四：画像恢复

对阶段一恢复出的簇运行 profiler，评估以下字段恢复率：

- 技术栈；
- 项目名和 repo；
- 内部服务；
- 内部域名；
- 数据库；
- 云平台；
- CI/CD；
- 认证系统；
- 业务线索；
- 安全线索。

### 6.5 实验五：缓解方法评估

防护等级：

```text
M0 No protection
原始 Agent 上下文完整发送。

M1 Secret filtering
只过滤 API keys、tokens、passwords、connection strings。

M2 Entity redaction
替换路径、域名、项目名、服务名、表名、用户名、内部 URL。

M3 Context minimization
只发送当前任务必要片段；历史本地摘要；工具输出裁剪。

M4 Broker mixing
B 做批处理、随机延迟、请求混洗、统一参数、长度分桶。

M5 Multi-provider splitting
不同 workflow / turn / sensitivity level 分发给不同 provider。

M6 Combined defense
M1 + M2 + M3 + M4。
```

对每个防护等级重新运行阶段一和阶段二。

### 6.6 实验六：Warm-start 扩展

给攻击者少量 seed，例如：

- 一个内部域名；
- 一个 repo 名；
- 一个项目名；
- 一个公开组织名；
- 一条历史请求片段。

目标：验证少量公开线索是否显著提升聚类和画像恢复能力。

### 6.7 实验七：恶意提供商扩展

该实验可选。模拟模型响应主动诱导 Agent 查询更多环境信息，例如：

- 目录结构；
- 配置文件；
- Git remote；
- 依赖版本；
- 环境变量；
- 测试日志；
- 部署文件。

该实验作为 upper bound，不作为主贡献。

## 7. 评估指标

### 7.1 聚类指标

Session-level：

- Pairwise Precision / Recall / F1；
- Adjusted Rand Index；
- Normalized Mutual Information；
- Cluster Purity。

User-level：

- Pairwise F1；
- B-cubed F1；
- user cluster purity；
- user split rate；
- user merge rate。

Organization-level：

- org-level F1；
- org purity；
- cross-org contamination rate。

Workflow ordering：

- turn ordering accuracy；
- Kendall tau；
- predicted chain 与 true chain 的 edit distance。

### 7.2 画像指标

- Field Precision / Recall / F1；
- Entity exact match；
- Entity fuzzy match；
- Industry classification accuracy；
- Tech-stack recovery rate；
- Internal-domain recovery rate；
- Service-name recovery rate；
- Security-clue recovery rate；
- Profile completeness score；
- Privacy risk score；
- Top-k Sensitive Clue Recovery。

### 7.3 缓解指标

- clustering F1 drop；
- profile recovery F1 drop；
- sensitive clue recovery drop；
- task success rate；
- token overhead；
- latency overhead；
- manual usability score。

## 8. 缓解思路

### 8.1 客户端侧

- 上下文最小化；
- 本地摘要替代原始历史；
- 路径、域名、项目名、服务名、表名脱敏；
- secret / token / connection string 检测；
- 工具输出过滤；
- session reset，减少长期上下文递增；
- 高敏任务走本地模型或私有部署。

### 8.2 中转站 B 侧

- 请求批处理；
- 时间混洗和延迟扰动；
- 统一模型参数、headers、SDK 标识；
- 标准化 system prompt 和 tool schema；
- token 长度 padding 或分桶；
- 多提供商分片；
- 禁止或隔离跨用户缓存；
- 内容重写和脱敏代理。

### 8.3 提供商 C 侧

- zero retention；
- prompt / response 日志最小化；
- 企业租户级日志隔离；
- 企业租户级缓存隔离；
- 原始日志访问审计；
- 可验证删除；
- 明确禁止跨请求画像分析。

## 9. 预期贡献

1. **提出威胁模型**：定义 LLM Agent API 场景下的内容侧去匿名化风险。
2. **提出两阶段攻击框架**：先聚类匿名请求为用户/组织级工作流，再从工作流中构建结构化画像。
3. **构建评测基准**：包含合成和半真实 Agent 工作流，支持 session/user/org 三层聚类与画像恢复评估。
4. **系统评估缓解方法**：量化上下文最小化、脱敏、混洗、缓存隔离、多提供商分片等方案的安全收益和任务代价。

## 10. 论文结构建议

1. Introduction；
2. Background and Motivation；
3. Threat Model；
4. Attack Overview；
5. Workflow Clustering；
6. Profile Reconstruction；
7. Datasets and Experimental Setup；
8. Evaluation；
9. Mitigations；
10. Discussion；
11. Conclusion。

## 11. 题目备选

- Context-Side De-anonymization of LLM Agent Workflows
- Reconstructing Anonymous LLM Agent Workflows from API Contexts
- Who Is Behind the Prompt? Workflow Clustering and Profile Reconstruction in LLM Agent APIs
- Beyond API Keys: Content-Based User and Organization Profiling in LLM Agent Services
- Anonymous but Linkable: Reconstructing User Workflows from LLM Agent Requests

中文定位：

> LLM Agent API 场景下的内容侧去匿名化与组织画像重建。

## 12. 最小可行实验版本

为了快速验证论文主张，可以先实现 MVP：

```text
Dataset:
20 orgs × 5 users × 20 workflows × 8 turns ≈ 16,000 requests

Attack:
rare feature + prefix overlap + temporal + embedding baseline + hybrid

Evaluation:
session/user/org clustering F1
profile field F1
mitigation M0/M1/M2/M3/M4

Main claim:
在 D1 + A0 + cold-start 下，匿名中转隐藏显式身份后，
hybrid attack 仍能显著恢复 user/org workflow，
并提取可用组织画像。
```

## 13. 一句话总结

身份匿名化只能隐藏 API key、user id、org id 等显式身份，但 LLM Agent 上下文本身包含大量准标识符。只要模型提供商能看到明文上下文，就可能通过内容指纹、上下文递增、罕见环境特征、工具调用结构和时序模式，重建用户/组织级工作流，并进一步推断出有价值的技术、业务和安全画像。有效缓解必须减少和变换发送给模型的内容，而不只是隐藏请求来源。
