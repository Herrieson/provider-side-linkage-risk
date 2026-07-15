# 论文叙事提纲

## 一句话主线

协议层去掉 user/session/org ID 并没有验证“请求因此不可关联”这一隐含假设。LLM Agent 流量中存在两种跨域根因：持续出现的内容句柄（代码域的 repository/workspace，工具域的 user/email/order/reservation/tenant）和重复发送的历史上下文。本文的贡献是发现、拆分并系统测量这两个机制；CARP 只是受预算约束的参考攻击。

## 故事结构

### 第一幕：匿名请求池

用户通过 broker 调用 LLM Agent。broker 去掉 user ID、org ID、trace ID 和 session ID。provider 表面上只看到混在一起的匿名请求。

论文问题：

> 去掉显式身份后，这些 Agent 请求真的不可关联吗？

### 第二幕：两个跨域根因

Agent 请求包含：

- persistent content handles：workspace/repo path、user/email、order/reservation、queue/tenant；
- context replay：cumulative dialogue、tool output 和历史状态。

文件路径只是第一类机制在代码域中的实例，不是论文的唯一根因。

### 第三幕：用成对控制定位机制

通过 direct parser、strict removal、turn delta、rephrasing、concurrency、alias rotation 和
collision 控制，分别回答每条通道何时存在、依赖什么、何时消失。

### 第四幕：参考攻击证明风险可实现

provider 不知道用户是谁，也没有画像。它先用低成本信号缩小候选空间：

1. cache-like bucket、长度、时间、tool/schema；
2. 罕见 token、路径、repo、代码符号；
3. cumulative context 和 shingle overlap；
4. 候选集合内的轻量语义 refinement。

这形成 `provider_lowcost`/CARP reference attack，但论文不以其算法新颖性为中心。

### 第五幕：从 linkage 到 workflow reconstruction

请求被聚类后，provider 可以恢复：

- 哪些请求属于同一 workflow；
- workflow 内 turn ordering；
- project/repo；
- GitHub owner-like organization。

Open-SWE 真实 trace 用来证明这一层。

### 第六幕：从 workflow 到画像

聚合请求后，provider 可以抽取：

- languages；
- frameworks；
- build tools；
- package managers；
- CI/CD；
- repo names；
- service hints。

Open-SWE 支持部分 technical profile；Dataset B 和 Synthetic A 补足更完整 profile truth 的机制证据。

### 第七幕：分层证据而不是混淆 claim

三层数据各回答不同问题：

- Open-SWE：真实 Agent traces，证明 workflow/project/owner-like linkage 和部分 technical profile。
- tau-bench historical：真实非代码工具轨迹，验证结构化 stable handles 和语义连续性。
- T3/Dataset B：真实 trace substrate + 受控分层 truth，评估纵向传播机制。
- Synthetic A：完整 ground truth，做规模和碰撞控制实验。

关键边界：

- Open-SWE org 是 GitHub owner-like，不是企业组织。
- Open-SWE user-level 是 N/A。
- Dataset B 是 semi-synthetic，不是真实用户身份恢复。

### 第八幕：缓解启示

删除 user ID 不够。需要处理：

- stable workspace/repo/path identifiers；
- cumulative context；
- tool output 中的环境状态；
- stable placeholder 造成的新 linkability；
- provider log retention/governance。

## 推荐 RQ

1. RQ1：identifier stripping 后仍直接暴露什么？
2. RQ2：还剩多少 workflow continuity？
3. RQ3：stable handles 能否支持跨 workflow 和纵向传播？
4. RQ4：这些风险能否在受限候选预算下测量？

## 不能写过强的地方

不要写：

- “我们恢复真实企业组织。”
- “Open-SWE 证明真实 user-level reconstruction。”
- “语义泄露单独足够。”
- “已证明互联网级 provider 流量可扩展。”

建议写：

- “GitHub owner-like linkage。”
- “Open-SWE user-level reconstruction is N/A。”
- “multi-signal linkage surface；Open-SWE project/owner-like linkage mainly driven by workspace/repo artifacts。”
- “12k-request longitudinal overlays show a scalable implementation path。”
