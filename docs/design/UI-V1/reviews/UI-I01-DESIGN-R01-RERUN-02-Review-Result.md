# UI-I01-DESIGN-R01-RERUN-02｜Focused Independent Re-Review Result v0.2

| Field | Value |
|---|---|
| Review ID | `UI-I01-DESIGN-R01-RERUN-02` |
| Workline | MarketPulse-AI / Frontend Product UI |
| Review Target | `UI-I01 Implementation Requirements Candidate v0.1.1` |
| Parent Review | `UI-I01-DESIGN-R01-RERUN-01` |
| Parent Fix | `UI-I01-DESIGN-01-FIX-01` |
| Role | Independent Reviewer |
| Mode | STRICT READ ONLY / FOCUSED RE-REVIEW / NO CANDIDATE MUTATION / NO PERSISTENCE / NO FREEZE / NO IMPLEMENTATION |
| Harness | WorkBuddy |
| Reviewer | DeepSeek V4.1 Flash |
| Date | 2026-10-03 |
| Repository | `zwmhua2-lab2/MarketPulse-AI` |
| Governance Repository | `zwmhua2-lab2/ai-dev-workflow` |
| Supersedes | `UI-I01-DESIGN-R01-RERUN-02 v0.1`（`BLOCKED / INPUT_IDENTITY_MISMATCH`）— 仅作 **input-layer failure history**，不作为本 Candidate 的质量判断 |

---

## 1. Verdict

```text
UI-I01-DESIGN-R01-RERUN-02
PASS WITH NON-BLOCKING FINDINGS
READY FOR HUMAN DESIGN CONFIRMATION
```

- **Blocking Findings = 0**。
- **Non-Blocking Findings = 3**；Observations = **2**。
- NB-01～**NB-07 closure 独立复核为 CLOSED**（7/7）。
- No regression = **PASS**（15/15 语义核对项）。
- No scope expansion = **PASS**（9/9 越界术语均处排除语境）。
- 本 VERDICT **不是** DESIGN ACCEPTED / FROZEN / IMPLEMENTATION AUTHORIZED / IMPLEMENTED。

---

## 2. Rule Load

```text
[MarketPulse-AI｜UI-I01-DESIGN-R01-RERUN-02｜Rules 0.1.0｜Rule Load: PASS]
```

| 项 | 值 |
|---|---|
| Governance Version | `0.1.0` |
| Rule Pack Version | `0.1.0` |
| Manifest | `fd00-rule-manifest/0.1.0` |
| Governance Mode | `SELF_HOSTED`（Self-Hosting ACTIVE / CUTOVER-1 PASS / Temporary Bootstrap Controls RETIRED） |
| Required Active Rules | **6/6 FULL read**：KERNEL-01-03 `AUTHORITY_RULES`、KERNEL-05 `TASK_CONTRACT_RULES`、KERNEL-06 `ROLE_AUTHORITY_RULES`、KERNEL-07 `RISK_AND_ACCEPTANCE_RULES`、KERNEL-02 `CONTEXT_AND_HARNESS_RULES`、KERNEL-08 `SELF_HOSTING_RULES` |
| Active EMRP | **EMRP-1.1**（ACTIVE on accepted main；ER-3 = GPT-6.1 Sol Medium/High/XHigh） |
| Bootstrap + workflow PROJECT_STATE | 完整读取 |
| Legacy `ai-dev-protocol` | REFERENCE ONLY / NON-AUTHORITATIVE（禁止隐式回退） |

读取基点：治理仓 accepted main **`cbc1a221646a9f4703a65e626e58cf192ed96426`**（实读）。

> **治理仓 main 已推进说明（本轮独立发现）**：任务卡与 Candidate §2 绑定 `16d260fad1d4580d90468c2b0cab6dd807d9f7a9`，而本轮实读为 `cbc1a221…`。已用 `gh api .../compare/16d260fa...cbc1a221` 机械核实：`ahead_by=3 / behind_by=0`（严格祖先），3 个 commit 全部为 **AWB 工作线**（`docs/awb/tasks/AWB-FIRST-LOOP-A-IMPL-01/**` + `PROJECT_STATE.md`）。**未触碰任何规则文件**（`governance/`、`KERNEL-*`、`MANIFEST`、`EMRP`、profiles 变更集为空），`WORKFLOW_RULE_MANIFEST.md` 在 `cbc1a221` 上仍为 `Governance 0.1.0 / Rule Pack 0.1.0 / fd00-rule-manifest/0.1.0`，6× REQUIRED_ACTIVE 全部 `ACTIVE`。**对本轮 focused re-review 无 material 影响**；但构成本轮 **NB-03**（见 §16）。

---

## 3. Repository Binding

| Repo | 任务卡 / Candidate 预期 | 独立实读（会话开始与结束各一次） | 结果 |
|---|---|---|---|
| MarketPulse-AI `refs/heads/main` | `8c94ea338f500e2ea4dd2f8a5ccc81a65502468e` | `8c94ea338f500e2ea4dd2f8a5ccc81a65502468e` | **MATCH** |
| ai-dev-workflow `refs/heads/main` | `16d260fad1d4580d90468c2b0cab6dd807d9f7a9` | `cbc1a221646a9f4703a65e626e58cf192ed96426` | **ADVANCED / NON-MATERIAL**（见 §2 与 NB-03） |

Candidate §3 三项自述声明，独立复核：

| Candidate 声明 | 独立实测（命令） | 结果 |
|---|---|---|
| Accepted Main SHA = `8c94ea338f500e2ea4dd2f8a5ccc81a65502468e` | `git ls-remote origin refs/heads/main` | **MATCH** |
| Accepted Main Tree = `941a52985bc16fe054bbd9cb4e2f43739333817b` | `git rev-parse 8c94ea33^{tree}` | **MATCH** |
| Local main = `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b` | `git rev-parse refs/heads/main` | **MATCH** |
| HEAD = `d47313a1cb41996410606fe92b286a5046ed4fce`（脏 worktree `prb-01-product-requirements-baseline`） | `git rev-parse HEAD` | **MATCH** |

MarketPulse 无 drift。Candidate 关于「本地 checkout 落后于任务基线且含既有脏改动，故一律通过 `git show origin/main:<path>` 读取 immutable objects」的处理方式与 Reviewer 本次采用的方法一致，且**未**切换或修改 checkout（会话前后 `git status --porcelain` 条目数恒为 32）。

---

## 4. Candidate Identity

```text
Candidate Identity: MATCH
```

| 项 | 期望值 | 独立实测值 | 结果 |
|---|---|---|---|
| Candidate | `UI-I01 Implementation Requirements Candidate v0.1.1` | 标题逐字一致（L3） | **MATCH** |
| Bytes | `41170` | `41170` | **MATCH** |
| Logical Lines | `692` | `692` | **MATCH** |
| SHA-256 | `f3b5ff12b99f82bc2a37ac488c70d7efea719582b454a0f0fde37e0c33f0c834` | `f3b5ff12b99f82bc2a37ac488c70d7efea719582b454a0f0fde37e0c33f0c834` | **MATCH** |
| Git blob SHA-1（内容身份） | — | `22a4b75c5abc416ed9b4cfd888c70bfe31594849` | 已建立 |
| 行尾 | — | CRLF=691 / loneLF=0 / loneCR=0 / 无尾换行 | 洁净 |
| 完整性 | — | 完整、无截断（末行为闭合代码围栏 + `Human Accepted: NO / Requirement Frozen: NO / Implementation Authorized: NO / UI-I01 Implemented: NO` 收尾块） | **PASS** |
| Parent Task | `UI-I01-DESIGN-01`（Candidate §1 L14） | 一致 | **MATCH** |
| Review Source | `UI-I01-DESIGN-R01-RERUN-01`（L15） | 一致 | **MATCH** |
| Candidate Authority | `CANDIDATE / NOT ACCEPTED / NOT FROZEN`（L22） | 未伪称 | **PASS** |
| Implementation Authorization | `NOT GRANTED`（L24） | 未伪称 | **PASS** |
| Repository Changes | `NONE`（L7 / L659） | 独立确认：仓库不存在 UI-I01 工件；会话前后 tracked 集合一致 | **PASS** |

Parent 身份亦经复核：Candidate §1 L31-35 自述 Parent = 27750 B / 565 行 / `96425e35…`，与本 Reviewer 在前次 RERUN-01 中独立实测的 v0.1 身份**逐项一致**。

不伪称其为 Repository Artifact：候选载体为 dispatch 附件正文，**未**持久化于任一仓库（独立确认：MarketPulse accepted main 的 `docs/design` 树无任何 `UI-I01*` 工件）。

---

## 5. NB-01 Closure

```text
NB-01: CLOSED
```

**要求**：Timezone Presentation Contract 已正确纳入 —— browser local timezone + visible timezone / technical trace UTC ISO 8601 / backend timestamp authority 保持 / 不改变 ordering-freshness / AC 与 Verification 已覆盖。

**独立核验**：

| 子项 | Candidate 位置 | 独立证据 | 结果 |
|---|---|---|---|
| browser local timezone + **visible timezone indication** | §9 L294 `Timezone Presentation Contract (NB-01)`：「所有展示时间使用浏览器本地时区，并带可见时区指示；不得固定为部署或用户推定时区」 | 冻结 UI-V1-D01 §34 L1052：「主 UI：浏览器本地时区，并带时区指示（timezone indication）」 | **MATCH（逐字对齐冻结源）** |
| technical trace = UTC ISO 8601 | §9 L295：「Technical trace 使用 UTC ISO 8601，明确标识 UTC。同一字段两种呈现表示同一 instant」 | 冻结 §34：「Technical trace：UTC ISO 8601」 | **MATCH** |
| backend timestamp authority 保持 | §9 L296-298：时间事实全部来自 backend DTO（逐字段枚举）；「不以浏览器读取/渲染时间替换 backend 时间」；「nullable 时间显示未提供，不补当前时间」 | Product Read 正式设计 §20 L865-866：「所有 timestamps 为 UTC-aware datetime；API 使用 RFC 3339 UTC」；`system.py` L568-569 注释「projection instant 即 Host snapshot，不在此重新 mint」 | **MATCH** |
| 不改变 ordering / freshness | §9 L298：「不得改变 event ordering、Incident 排序/cursor、freshness、ProjectionState 或 backend timestamp authority」 | 与 §13 L429 backend `(opened_at DESC, incident_id DESC)`、§10 L350「TanStack cache stale ≠ Product STALE」一致 | **MATCH** |
| 自定义范围 `[start,end)` | §9 L299：沿用 `[start,end)`，本地边界转 UTC；明确「UI-I01 不因此新增时间范围筛选」 | 冻结 §34：「自定义时间范围 `[start, end)`；前端将本地边界转换为 UTC 后再发起 API 查询」 | **MATCH** |
| **AC 已覆盖** | **AC-09**（L550）：「§9 主 UI 浏览器本地时区并有时区指示、trace UTC ISO 8601；仅 formatting，backend 时间/排序/freshness authority 不变；无 global ACID 声明」 | AC 文本独立读取 | **MATCH（AC 已覆盖）** |
| **Verification 已覆盖** | §17 L508 `Timezone` 行：「固定 DTO instant/clock，两个浏览器时区及 DST 场景验证主 UI 本地时间+时区指示、trace 同一 instant 的 UTC ISO 8601；覆盖 §9 所有时间/null；原始 DTO、排序/cursor/freshness 不因格式化改变」 | §17 表独立读取 | **MATCH（含测试矩阵，且超出 RERUN-01 建议的最低要求）** |

**NB-01 = CLOSED。** 修复不仅补齐了 RERUN-01 指出的「正文与 AC 均无明确时间戳/时区要求」缺口，还额外覆盖了 DST 场景与 null 时间边界。

---

## 6. NB-02 Closure

```text
NB-02: CLOSED
```

**要求**：`DEGRADED` ≠ ProjectionState enum member，且 ProjectionState / Capability / Request lifecycle / Health / Readiness / Runtime lifecycle 正确分轴。

**独立核验**：

| 子项 | Candidate 位置 | 独立证据（main `8c94ea33`） | 结果 |
|---|---|---|---|
| `DEGRADED ≠ ProjectionState` 明文 | §10 L321：**「`DEGRADED ≠ ProjectionState enum member`」** | `backend/src/marketpulse/api/product/models.py`：`class ProjectionState(StrEnum)` 恰 **5** 成员（FRESH/STALE/EMPTY/UNAVAILABLE/CAPABILITY_NOT_INTEGRATED）；`models.py` 全文 `DEGRADED` 出现 **0** 次 | **MATCH** |
| DEGRADED 所属轴正确 | §10 L321：「它可出现在既有 `HostReadinessStatus`、`HostLifecycleState` 及 backend Health status」 | `generated.ts` L392 `HostLifecycleState: ... \| "DEGRADED" \| ...`；L398 `HostReadinessStatus: "READY" \| "NOT_READY" \| "DEGRADED" \| "FAIL_CLOSED"`（全文 `DEGRADED` 仅此 **2** 处，**均在 axis enum 内，无一处属 ProjectionState**） | **MATCH** |
| 不联动改写其它轴 | §10 L321：「UI 注明所属对象/轴，不把 DEGRADED 转成 projection state，不联动改写其它轴，不新增 authority enum」 | `system.py` L365 `("DEGRADED" if readiness.status is HostReadinessStatus.DEGRADED else "FAIL_CLOSED")` —— backend 自身亦将其置于 readiness 轴 | **MATCH** |
| 状态表已标轴（RERUN-01 原 NB-02 的直接诉求） | §10 L311：**「下表包含不同状态轴和组合条件，**不是一个 enum**」**；L313-319 表头首列为「**状态轴**」，逐行标注 Product Projection State / Capability / Request lifecycle / Health-readiness / Runtime lifecycle-business state | 表结构独立读取 | **MATCH（已机械化）** |
| `DEGRADED` 行为行亦标注轴 | §10 L328：「DEGRADED（Health/readiness 或 Runtime lifecycle 条件）→ 展示对应 backend 字段与原因；**不是 ProjectionState**，不改写其它对象或轴」 | — | **MATCH** |
| AC 已覆盖 | **AC-06**（L547）：「capability 两轴、ProjectionState、request lifecycle、Health/readiness/lifecycle 分离；DEGRADED 不作为 ProjectionState 成员，所属对象/轴明确」 | AC 文本 | **MATCH** |
| Verification 已覆盖 | §17 L503 `DEGRADED axis` 行：「Ready/Health DEGRADED 与 section FRESH 共存；注明对应轴，不改变 ProjectionState、capability/request/lifecycle」；L500 `数据状态` 行：「ProjectionState 精确保持五个值」 | §17 表 | **MATCH** |

**NB-02 = CLOSED。** RERUN-01 指出的「并列未标轴」问题已通过表头显式命名为「状态轴」+ 首句否定式断言 + AC-06 + 专用测试行四重机械化。

---

## 7. NB-03 Closure

```text
NB-03: CLOSED
```

**要求**：Product `/system` endpoint-level 503 只对应正式 `SNAPSHOT_FAILED` contract；`SOURCE_UNAVAILABLE` 保持 section-level failure，不得扩成 endpoint-level 503。

**独立核验（本轮最关键的核对）**：

| 子项 | Candidate 位置 | 独立证据（main `8c94ea33`） | 结果 |
|---|---|---|---|
| endpoint-level 503 仅 `SNAPSHOT_FAILED` | §11 L358：「当前 endpoint-level failure **仅为** SNAPSHOT_FAILED；…**不称为** endpoint SOURCE_UNAVAILABLE 或 /ready NOT_READY」 | `system.py` L264-275 `_product_snapshot_failure()`：「Endpoint-wide `503 SNAPSHOT_FAILED`: the required Product snapshot was not obtained」→ 唯一制造 endpoint 503 的路径，`reason=ReadFailureReason.SNAPSHOT_FAILED` | **MATCH** |
| SOURCE_UNAVAILABLE 保持 section-level | §11 L364：「Incident source 不可用或 Recovery snapshot 缺失保留为 `200 + is_partial=true`，对应 section `state=UNAVAILABLE` 与正式 failure reason」 | `system.py` L406-414：`incident_page is None` ⇒ `_section(None, …, state=ProjectionState.UNAVAILABLE, read_failure_reason=ReadFailureReason.SOURCE_UNAVAILABLE)`，**留在 200 投影内**；L567 `partial = recovery_data is None or incident_page is None` | **MATCH** |
| 不扩成 endpoint-level 503 | §10 L332：「partial … Incident SOURCE_UNAVAILABLE、Recovery SNAPSHOT_FAILED 为 section-level failure，**不升格为 endpoint 503**」；§17 L502：「不接受 SOURCE_UNAVAILABLE 为该 endpoint 正式 503」 | 代码中 `SOURCE_UNAVAILABLE` 仅出现于 section builder（L413）与 import/openapi 说明，**无任何 503 路径引用它** | **MATCH** |
| 共享枚举 ≠ 双 503 实现 | §11 L364 末句：「共享 ReadFailureReason 包含两种值**不意味着**该 endpoint 实现了两种 endpoint 503」 | `models.py` `ReadFailureReason` 确为 2 值共享枚举；`system.py` L282-288 openapi 说明亦指出 503 model 保留「the frozen distinction between SOURCE_UNAVAILABLE and SNAPSHOT_FAILED」 | **MATCH** |
| 措辞采用「**当前**」限定，未与正式设计冲突 | §11 L358 用「当前 endpoint-level failure 仅为…」 | Product Read 正式设计 §18 L804-805 确列两种 503 **分类**；§17 L768-769 矩阵记为「503**或**partial 200」；§18 L817「整体 projection 无法形成可信结果时才返回 503」。**契约允许两类；当前实现只产生一类。** Candidate 以「当前」限定描述**实现事实**，措辞**准确、不与 accepted 设计冲突** | **MATCH（无 authority conflict）** |
| AC 已覆盖 | **AC-08**（L549）：「partial 200 保留可用 sections；section SOURCE_UNAVAILABLE/SNAPSHOT_FAILED 与 endpoint 503 SNAPSHOT_FAILED 分开；不套用 /ready 例外，不呈现 zero/empty」 | AC 文本 | **MATCH** |
| Verification 已覆盖 | §17 L501 `部分可用` + L502 `Endpoint 503` 两行分别为 section 与 endpoint 建独立 fixture | §17 表 | **MATCH** |

**NB-03 = CLOSED。** RERUN-01 的措辞精度问题已通过「当前…仅为」限定词 + 共享枚举澄清句 + AC-08 + 两条独立测试行完整消除。经独立判读，**未**构成与 accepted Product Read 正式设计的 authority conflict。

---

## 8. NB-04 Closure

```text
NB-04: CLOSED
```

**要求**：422 invalid cursor —— 不造 cursor / 不当 NetworkError / 不 retry / 不 reset auth-session / 可显式 reset 到合法第一页。

**独立核验**：

| 子项 | Candidate 位置 | 独立证据 | 结果 |
|---|---|---|---|
| 不造 cursor | §13 L423：「不得创建替代 cursor，后续 cursor 只来自合法响应」；§11 L360：「不造 cursor」 | `cursor.py`：`ProductCursorError` 在 payload/endpoint/filters/sort tuple 任一不匹配时 raise（L81-92 等） | **MATCH** |
| 不当 NetworkError | §11 L360：「不转 NetworkError」 | `transport.ts` `transportErrorForStatus`：非 2xx 且非 401 ⇒ `HttpError(status, body)`；422 **不会**落入 `sendRequest` 的 `NetworkError` 分支（该分支仅捕获抛出异常） | **MATCH** |
| 不自动 retry | §11 L360：「不自动 retry」；§13 L423：「422 不作为网络故障 retry」 | `queryClient.ts` L20-27 `shouldRetryQuery`：`HttpError` ⇒ `return error.status >= 500`，故 **422 不重试** | **MATCH** |
| 不 reset auth/session | §11 L360：「不重置 auth/session」；§13 L423：「不清 token、不 reset session generation、不清全局 authenticated cache、不跳 Login」 | `errors.ts`：仅 `UnauthorizedError` 文档标注「the only category that is allowed to invalidate a session」；422 ⇒ `HttpError` ⇒ 不触发 `endSession()` | **MATCH** |
| 可显式 reset 到合法第一页 | §13 L423：「UI 提供显式 reset：筛选与 pagination 回到 OPEN、不限定 type、limit=100、无 cursor；清除旧 next_cursor/分页状态」 | backend `system.py` L174-177 `ProductCursorError` ⇒ `HTTPException(status_code=422)` | **MATCH（行为与 backend 契约对齐）** |
| AC 已覆盖 | **AC-11**（L552）：「invalid/malformed cursor 422 可 reset 到合法第一页，不造 cursor、不当网络错误、不 reset auth/session」 | AC 文本 | **MATCH** |
| Verification 已覆盖（RERUN-01 原 NB-04 的直接诉求） | §17 L507 `Invalid cursor 422` 行：**新增独立测试行**，「invalid/malformed、filter-mismatch 返回 backend-contract 422；不造 cursor、不按 NetworkError retry、不 reset auth/session/token/cache 或跳 Login；用户 reset 后默认合法参数/无 cursor，第一页成功，后续 cursor 仅取自响应」 | §17 表 | **MATCH（已补齐 RERUN-01 所缺的显式用例）** |

**NB-04 = CLOSED。**

---

## 9. NB-05 Closure

```text
NB-05: CLOSED
```

**要求**：Backend API default `incident_status = None` 与 UI-I01 UX default `incident_status = OPEN` 两者不得混淆。

**独立核验**：

| 子项 | Candidate 位置 | 独立证据（main `8c94ea33`） | 结果 |
|---|---|---|---|
| Backend API default = None | §13 L410-415 专用代码块：`Backend API default: incident_status = None`；L417：「API 参数省略时不限定 status；OPEN **不是** Backend endpoint default」 | `system.py` L300：`incident_status: IncidentStatus \| None = Query(default=None)` —— **逐字 MATCH** | **MATCH** |
| UI-I01 UX default = OPEN | §13 L410-415：`UI-I01 Product UX default: incident_status = OPEN`；L416：「UI 首次 query 主动发送 OPEN」 | — （属 UI 层设计决定，不与 backend 冲突） | **MATCH** |
| 选「全部」的语义 | §13 L417：「选『全部』时省略 status filter，**不发送自造 ALL enum**」 | `IncidentStatus` 枚举来自 `g4/models.py`；无 `ALL` 成员 | **MATCH** |
| 不修改 Backend/DTO/generated | §13 L417：「不修改 Backend、DTO 或 generated types」 | 与 §6 Out of Scope 一致 | **MATCH** |
| AC 已覆盖 | **AC-11**（L552）：「首次 UI query 显式 OPEN ≠ API default=None」 | AC 文本 | **MATCH** |
| Verification 已覆盖 | §17 L506 `Query default` 行：「首次请求显式发送 OPEN；API default 仍为 None；『全部』省略 status filter；key 与实际参数一致，**不声称 OPEN 是 API default**」 | §17 表 | **MATCH** |

**NB-05 = CLOSED。** RERUN-01 的 naming clarity 问题已通过专用标题「API default 与 UI default ownership（NB-05）」+ 代码块对照 + 否定式澄清 + AC-11 + 专用测试行消除。

---

## 10. NB-06 Closure

```text
NB-06: CLOSED
```

**要求**：Global Shell allowed / forbidden change boundary 已经机械化，并且不会扩成 global shell redesign。

**独立核验**：

| 子项 | Candidate 位置 | 独立判读 | 结果 |
|---|---|---|---|
| allowed boundary 已机械化（脱离「必要」定性限定） | §5 L174-179 **`Global Shell Allowed Change Boundary（NB-06）`** 四条：(a) 在既有 authenticated Shell 的 `Outlet` 内接入 System，`router.tsx` 仅替换 `/system` placeholder；(b) 保持五页 navigation IA/顺序/title-path-ownerBatch/route metadata/Auth wrapper/默认路由；(c) `ProductShell.tsx` **仅允许 System 进入既有 Shell 所必需的最小文案/语义标记/accessibility 修正**，且**每处差异必须追溯至 System integration 或既有 accessibility AC**；(d) System 布局/样式限制在 System route 内容与局部组件 | 三条 (a)(b)(d) 为可机械核对的**枚举式**约束；(c) 保留「最小/必要」措辞但**新增可机械检查的追溯要求**（每处差异须可追溯至 System integration 或既有 accessibility AC）—— 该追溯要求即是机械化护栏 | **PASS（已机械化）** |
| forbidden boundary 已机械化 | §5 L181-187 **`Global Shell Forbidden Change Boundary（NB-06）`** 五条：不改其它四页 placeholder/ownership/实现；不改 `DEFAULT_PRODUCT_ROUTE=/overview`、index/unknown redirect、`/login`、route topology；不新增/删除/重排 navigation、不重新设计 navigation 或全局视觉/布局；不新增第二套 Shell/provider/Auth/QueryClient/API client/router、不改 sign-out/session/transport/readiness/global retry 所有权；不使 Shell 或其它四页产生 System query、不触发 UI-I02～I06 | 五条全部为**可机械核对的否定式枚举**，与 repo truth 实读一致：`routes.ts` `DEFAULT_PRODUCT_ROUTE = "/overview"`、`PRODUCT_ROUTES` 恰 5 条（`/system` ownerBatch=`UI-I01`）、`LOGIN_ROUTE = "/login"`；`router.tsx` index 与 `*` 均 `Navigate to DEFAULT_PRODUCT_ROUTE` | **PASS（与 repo truth 对齐）** |
| 不扩成 global shell redesign | §6 L200-202 排除「第二套 Shell…」「全局 UI redesign」；§20 L602 Stop Condition 9「实际变更跨越 approved file boundary」 | 三重约束（§5 forbidden + §6 Out of Scope + §20 Stop Condition 9） | **PASS** |
| AC 已覆盖 | **AC-02**（L543）：「§5 Shell allowed/forbidden boundary 逐项满足；五页 IA、navigation、route metadata、默认 route、其它四页 ownership/placeholder 保持；无第二套 Shell/provider」 | AC 文本 | **MATCH** |
| Verification 已覆盖 | §17 L495 `路由 / Shell` 行：「/system 正常加载；**按 §5 精确 allowed/forbidden boundary 核对 diff**；五页 IA、navigation、其它四页 ownership/placeholder、默认 /overview、index/unknown redirect 不变；无第二套 Shell/provider、其它页 System query」 | §17 表 | **MATCH** |

**NB-06 = CLOSED。** RERUN-01 指出「§5 允许修改 `ProductShell.tsx` 的『必要』为定性限定词」；successor 已将其拆为 allowed/forbidden 两个显式具名小节，并新增「每处差异必须可追溯」的机械判据。**残余**：措辞中仍存在「最小/必要」限定词（可量化性未达 100%），记为 **OBS-02**，非阻塞。

---

## 11. NB-07 Closure

```text
NB-07: CLOSED
```

**要求**：Implementation Authorization 前存在完整的 Latest-main currency / delta reconciliation Gate，至少覆盖 8 项，并有 `NON_MATERIAL / MATERIAL / BLOCKING` 分类规则。

**独立核验**：

`§3 Implementation Baseline Rebind Gate（NB-07）` L110-131 提供了机器化的八项核验表：

| # | 任务卡要求的必核项 | Candidate §3 对应行 | 覆盖 |
|---|---|---|---|
| 1 | MarketPulse current main | L116：实时读取 remote main + remote-tracking ref；记录 SHA/tree、Design Task Base → current main 的 log/diff、proposed Implementation Task Base | **COVERED** |
| 2 | Workflow current main | L117：实时读取 remote main；核验 bootstrap、manifest、六份 active rules 与适用 profile 的身份/版本及 governance delta | **COVERED** |
| 3 | Frozen Requirement identity | L118：核验 Human-confirmed / persisted-frozen 的 exact carrier、version、bytes、SHA-256、Git blob/commit 及 Review/Confirmation/Freeze evidence；并声明「当前 v0.1.1 仍是 Candidate」 | **COVERED** |
| 4 | Accepted lint Foundation identity | L119：exact accepted candidate/commit、Acceptance evidence、lint config/manifest/lockfile identity 与正式可复现命令；「tooling 存在或测试绿**不能代替** Accepted」 | **COVERED** |
| 5 | `API/generated.ts` compatibility | L120：核对实际 `generated.ts` 身份、System endpoint/DTO/enums/query/error compatibility 与 API drift evidence；「不得手改或静默 regenerate 消除冲突」 | **COVERED** |
| 6 | Frontend Foundation delta | L121：核对 Shell、router/routes/default route、Auth/session、QueryClient、transport/readiness/retry 及相关测试的 baseline diff，确认合同仍可由既有接口实现 | **COVERED** |
| 7 | Parallel mutation status | L122：记录协调/dispatch/lock evidence、并行任务及重叠修改状态；「**remote SHA 不变不证明没有并行 mutation**；未确认的重叠冲突不能通过」 | **COVERED** |
| 8 | Dirty workspace protection | L123：记录 workspace HEAD/branch/status/diff、已有 modified/deleted/untracked 及归属；区分 `PREEXISTING_DELTA` / `TASK_DELTA` | **COVERED** |

**8/8 COVERED。**

**分类规则**（L125-131）：

| 类别 | Candidate 定义 | 判定 |
|---|---|---|
| `NON_MATERIAL` | 证据确认 Frozen semantics / Scope / API compatibility / ownership 等当前契约仍成立；记录理由并**显式 rebind** 最新实施基线 | **PRESENT** |
| `MATERIAL` | 相关契约 / Foundation / authority binding 有实质变化，需独立 currency-rebind review 或授权 amendment；**停止受影响实施，不自行改设计** | **PRESENT** |
| `BLOCKING` | 关键身份/证据缺失或冲突、lint 未 Accepted、API 不兼容、并行修改冲突或脏改动无法保护；**不得授权 Implementation** | **PRESENT** |

附加机械化条款（L125、L131）：
- 「current main 与 Design Task Base 不同，**不得自动判 stale failure，也不得自动通过**」 —— 双否定式护栏，消除两个方向的误判。
- 「全部必核项有可复核证据、material delta 已正式解决、current implementation contract 确认仍成立且**无 unresolved blocking**，才可进入独立 Implementation Authorization」 —— 入口判据显式。
- 「授权前**再次**核验两库 remote main；新变化回到 reconciliation」 —— 重入条款。
- 「Rebind 不自动授予实施权限，不授权 reset/rebase/clean、覆盖脏改动或扩大本 Fix Scope」 —— 越权护栏。

| 其它 | 位置 | 结果 |
|---|---|---|
| AC 已覆盖 | **AC-18**（L559）：「Implementation Authorization 前 lint Foundation 已 Accepted，§3 八项 reconciliation evidence 完整、分类/处置明确、current contract 仍成立；lint 不阻塞 Design Review/Freeze」 | **MATCH** |
| Verification 已覆盖 | §17 L516 `Baseline rebind` 行：「Authorization 前 §3 八项 evidence 完整；两库 current-main diff/classification/disposition 明确；current main 不同但 NON_MATERIAL 可显式 rebind，MATERIAL 未解决/BLOCKING 不可授权；脏改动/并行状态有证据」 | **MATCH** |
| Stop Condition 已覆盖 | §20 L595 第 2 条：「§3 evidence 缺失或 HEAD/remote/Task Base delta 未 reconciliation；main 不同本身不是 stale failure，未解决 MATERIAL/BLOCKING 阻止受影响实施」 | **MATCH** |
| Future path 已覆盖 | §21 L621：「§3 Latest-main currency / delta reconciliation Gate」列于两条线汇合后、Implementation Authorization 之前 | **MATCH** |

**NB-07 = CLOSED。** RERUN-01 的「建议在 Implementation 合同时把 Task Base 必须重新解析为届时 accepted remote main 写成可机械检查的前置项」已超预期实现：不再是「建议」，而是带 8 项核验列、3 级分类、双否定护栏、重入条款与越权护栏的**独立 Gate 小节**。

---

## 12. Lint Foundation Disposition

```text
Lint Foundation Disposition: PASS（时序合理，未变成 Freeze blocker）
```

| 阶段 | 任务卡 §5 要求 | Candidate 位置 | 独立判读 | 结果 |
|---|---|---|---|---|
| Lint Foundation | `SEPARATE TASK` | §2 L60-65 代码块 `Lint Foundation: SEPARATE TASK`；L62「该决定不授权本轮创建 Foundation 任务或修改 tooling」 | 与任务卡逐字一致 | **MATCH** |
| Design Review | `NOT BLOCKED` | §2 L66 `Design Review: NOT BLOCKED` | 一致 | **MATCH** |
| Requirement Freeze | `NOT BLOCKED` | §2 L67 `Requirement Freeze: NOT BLOCKED`；L72「Lint acceptance **不得被写成 Freeze 前置**」 | 一致，且有显式否定句 | **MATCH** |
| Implementation Authorization | `BLOCKED UNTIL LINT FOUNDATION ACCEPTED` | §2 L68-69 `Implementation Authorization: BLOCKED UNTIL LINT FOUNDATION ACCEPTED` | 一致 | **MATCH** |
| 其它一致性 | — | §17 L489：「Authorization 前置为独立 lint Foundation 已 Accepted…**该前置不阻塞当前 Design Review 或 Requirement Freeze**」；§20 L594 Stop Condition 1 含同一「不阻塞 Design Review/Freeze」限定；§21 L632：「lint Foundation 不阻塞 Design Review/Requirement Freeze；Implementation Authorization 等待其 Accepted」；AC-18 同上 | 四处独立复述同一时序，**无内部矛盾** | **MATCH** |

**独立事实核验**：`frontend/package.json` 的 `scripts` 恰为 `build / typecheck / test / test:run / generate:api / check:api-drift` —— **无 `lint` script**；devDependencies 中**无 eslint** —— 与 Candidate §7 L221 自述一致。

**未发现新的 repository contradiction**，故任务卡 §5 的例外条款**不触发**，任务卡 §8 的「lint sequencing 重新变成 Freeze blocker」判据 **NOT TRIGGERED**。

---

## 13. Regression Check

```text
Regression Check: PASS
```

任务卡 §6 的 15 项核心语义（`LIVE ≠ READY ≠ HEALTH` 计为 1 项复合断言）在 successor 中**全部保留**，且**未发现被修坏**：

| # | 核心语义 | Candidate 位置 | 结果 |
|---|---|---|---|
| 1 | `LIVE ≠ READY ≠ HEALTH` | §8 L233：「**Live、运行就绪 Ready、Health 三个独立区域**」；§9 L275-277 分别限定「不推断 Ready」「不推断 Health 或 risk admission」；AC-05 | **PRESERVED** |
| 2 | one ProductShell | §8 L241；§5 L177-178；AC-02；§17 L495 | **PRESERVED** |
| 3 | one auth/session ownership | §12 L370-379；§5 L189「复用的 auth、transport、readiness、provider 与全局 retry 所有权保持现状」 | **PRESERVED** |
| 4 | one QueryClient | §3/§13；§5 L186「不新增第二套…QueryClient」；§17 L495 | **PRESERVED** |
| 5 | one typed API transport | §9 L258 唯一数据请求；§17 L495「无第二套 …provider」；AC-03 | **PRESERVED** |
| 6 | no mutation controls | §6 L204 逐项列举禁止；§17 L510「无禁止 controls；业务请求仅 GET；Login POST 保留」；AC-14 | **PRESERVED** |
| 7 | Incident cursor remains opaque | §13 L428：「cursor 原样传递，不解析、不改造成 offset」；§17 L505 | **PRESERVED** |
| 8 | no fake total | §13 L432：「没有 total count，不编造总数」；§9 L303；AC-11 | **PRESERVED** |
| 9 | no fabricated per-row blocking | §9 L303：「Incident DTO 没有逐条 `blocking` 字段，不伪造该字段或将总 count 分摊到 rows」；AC-11 | **PRESERVED** |
| 10 | Query cache stale ≠ Product STALE | §10 L350：「TanStack Query 的 cache `stale` 不映射为 Product `STALE`」 | **PRESERVED** |
| 11 | AI Design Accepted ≠ Runtime Activated | §9 L239；§17 L509「NOT_ACTIVATED 为 U0；与 Design Accepted 分开」；AC-12 | **PRESERVED** |
| 12 | Market Provider ≠ Real AI Provider | §9 L306：「`market_provider.provider` 不得被标注为 Real AI Provider」 | **PRESERVED** |
| 13 | Recovery not inferred from timestamps | §9 L297：「nullable 时间显示未提供，不补当前时间或**推断 Recovery**」；§17 L504「Recovery 不由时间推断」 | **PRESERVED** |
| 14 | Reconciliation remains detector-only | §8 L237：「Reconciliation 标明 detector-only」；§9 L283「不提供修复」 | **PRESERVED** |
| 15 | `/system` remains read-only | §8 L231「系统、只读标识」；§17 L510 | **PRESERVED** |

**独立事实交叉核验**（successor 引用的事实未被修坏）：
- `ProjectionState` 仍恰 5 成员，无 `DEGRADED`（models.py）。
- `IncidentDTO` 仍恰 **8** 字段（incident_id / incident_type / run_mode / instrument_id / status / reason / opened_at / resolved_at），无 `blocking`；`IncidentPageDTO` 仍仅 `items` + `next_cursor`，**无 total**。
- endpoint 仍唯一（`GET /system`）；无 detail endpoint。
- `queryClient.ts` 仍 `MAX_QUERY_RETRIES=2`、`refetchInterval:false`、`refetchOnWindowFocus:false`、`refetchOnReconnect:true`、`HttpError ⇒ status>=500`。
- `transport.ts` 仍为单点 `requestData()`；`/ready` 503 仍为**唯一**例外（`readiness.ts` 明确「No other module may take this shortcut」）。
- `ProductShell.tsx` 仍只读（唯一交互 = `signOut`）；`AuthSessionProvider.tsx` 仍持有 generation + providerActive 双 fencing。
- `generated.ts` 30/30 schema 名在册、`/api/v1/product/system` 与 `/api/v1/ready` 路径字面量在册。

**无 semantic regression。**

---

## 14. Scope Check

```text
Scope Check: PASS（无 scope expansion）
```

任务卡 §7 的 10 类越界项机械扫描结果（对 Candidate 全文）：

| 越界项 | 全文是否出现 | 出现处所在章节 | 语境判定 | 结果 |
|---|---|---|---|---|
| UI-I02～I06 implementation | 出现（L636） | **§21 Future Review / Freeze Path** | 仅列**未解锁的产品顺序**（`… → UI-I02 → … → UI-I06`），紧接 L639「**本轮不派发以上后续任务**」 | **NO EXPANSION** |
| Backend API change | 未新增 | — | §6 L197 显式排除「Backend Product API redesign、新 endpoint 或 DTO 扩展」；§20 L599 Stop Condition 6 | **NO EXPANSION** |
| DTO extension | 未新增 | — | 同上；§9 L269「不建立重复 authority DTO」 | **NO EXPANSION** |
| Schema / Migration | 出现（L198） | **§6 Out of Scope** | 「Schema、migration、index、数据库或服务状态变更」列为**不实施** | **NO EXPANSION** |
| EdgeAggregateRead | 出现（L199） | **§6 Out of Scope** | 「`UI-RD01-I04 / EdgeAggregateRead`」列为**不实施** | **NO EXPANSION** |
| lint tooling implementation | 出现（L60、L202） | §2 L60（**SEPARATE TASK** 声明）；§6 L202（列为**不实施**） | 两处均为排除/外置语境 | **NO EXPANSION** |
| AI activation | 出现（L204） | **§6 Out of Scope** 的 mutation controls 禁止清单 | 禁止，非授权 | **NO EXPANSION** |
| Gate activation | 出现（L196、L204） | **§6 Out of Scope**（`Gate A/B/C`）与禁止清单（`Activate Gate`） | 禁止，非授权 | **NO EXPANSION** |
| Live | 出现（L196） | **§6 Out of Scope**（「Live 或 Live Trading 激活」） | 禁止，非授权 | **NO EXPANSION** |
| Trading mutation | 出现（L204） | **§6 Out of Scope**（「…及交易动作」） | 禁止，非授权 | **NO EXPANSION** |

**结构面独立核验**：
- **AC 编号未变**：RERUN-01 的 v0.1 与 successor v0.1.1 均为 **AC-01～AC-20**，`new AC = NONE` —— 未新增验收项，未扩大验收面。
- **章节数未变**：均 **21 个 `##` 小节**（§1…§21），successor 未新增顶层章节。
- **允许修改面未扩大**：§5 允许修改面六项与 Parent 一致（`/system` 页面 + 局部组件/query/presentation、`ProductShell.tsx`（受 NB-06 boundary 约束）、`router.tsx` 的 `/system` placeholder 替换、System 局部样式/最小 primitives、相关 fixtures/focused tests、完成后最小状态记录）；`frontend/src/app/routes.ts`（五页 IA 单一声明源）**仍未列入可改面** —— 正确。

**无 scope expansion。**

---

## 15. Blocking Findings

```text
Blocking Findings = 0
```

任务卡 §8 逐项判定：

| 判据 | 结果 | 依据 |
|---|---|---|
| Candidate identity mismatch | **NOT TRIGGERED** | Bytes / Logical Lines / SHA-256 三项全 MATCH（§4） |
| 任一 NB-01～07 未真正关闭 | **NOT TRIGGERED** | 7/7 CLOSED（§5–§11） |
| 修复引入 semantic regression | **NOT TRIGGERED** | 15/15 语义 PRESERVED，且事实交叉核验无漂移（§13） |
| scope expansion | **NOT TRIGGERED** | 10/10 越界项均处排除语境；AC 与章节数未变（§14） |
| authority conflict | **NOT TRIGGERED** | NB-03 措辞与 Product Read 正式设计 §18/§17 经独立判读**不冲突**（§7）；Frozen UI-V1 §34/§30/§8/§7.2 逐项一致 |
| lint sequencing 重新变成 Freeze blocker | **NOT TRIGGERED** | 四处独立复述均保持「不阻塞 Freeze」；未发现新 repository contradiction（§12） |
| baseline/rebind Gate 不可机械执行 | **NOT TRIGGERED** | 8/8 必核项 + 3 级分类 + 双否定护栏 + 重入/越权条款（§11） |
| Candidate 与 Frozen UI / accepted API 冲突 | **NOT TRIGGERED** | §9/§10/§11/§15/§16 对 Frozen UI-V1 §34/§30/§8/§7.2/§35 逐项对齐；§9/§13 对 accepted API 契约逐项对齐 |

**Blocking Findings = 0 ⇒ 允许 PASS。**

---

## 16. Non-Blocking Findings

```text
Non-Blocking Findings = 3
```

| ID | 类别 | 内容 | 独立证据 | 处置 |
|---|---|---|---|---|
| **NB-R2-01** | process / evidence hygiene | Candidate §2 与 §3 绑定 `ai-dev-workflow` main = `16d260fad1d4580d90468c2b0cab6dd807d9f7a9`，但本轮实读为 `cbc1a221646a9f4703a65e626e58cf192ed96426`（advanced 3 commits）。Candidate 自述「开始与结束均通过 `git ls-remote origin refs/heads/main` 核实」，故其 binding 在**产出时刻为真**；差异源于产出之后的治理仓推进。 | `gh api .../compare/16d260fa...cbc1a221` ⇒ `ahead_by=3 / behind_by=0`（严格祖先）；变更集仅 `PROJECT_STATE.md` + 3 个 `docs/awb/tasks/AWB-FIRST-LOOP-A-IMPL-01/**`；**无任何规则文件改动**；`WORKFLOW_RULE_MANIFEST.md` 在 `cbc1a221` 上仍 `0.1.0` / 6× `ACTIVE` | **NON-BLOCKING**（无 material 影响：规则面零变更，Rule Pack 版本不变，CUTOVER-1 状态不变）。建议：若 Human 决定继续，按 §21 路径，届时 Freeze/Implementation 前由 NB-07 的 rebind Gate 二次核验治理 main —— 该 Gate 已内建「授权前再次核验两库 remote main；新变化回到 reconciliation」条款，故本条可被既有机制自然吸收。**不阻断本轮 Design Review / Human Confirmation。** |
| **NB-R2-02** | precision of wording（verification contract） | §17 L508 `Timezone` 行要求「两个浏览器时区及 DST 场景验证」。「两个时区」未枚举具体时区对，也未说明 DST 场景的构造方式（如固定 instant 落在 DST 边界前后）。 | §17 表 L508 独立读取 | **NON-BLOCKING**（测试可执行性提示，非语义缺口）。建议 Implementation 合同中枚举具体时区对与 DST 用例构造方式，避免执行时选择漂移。 |
| **NB-R2-03** | decomposition / boundary explicitness | §5 `Global Shell Allowed Change Boundary` 第 3 条仍含「**最小**文案/语义标记/accessibility 修正」的定性限定词；虽有「每处差异必须追溯至 System integration 或既有 accessibility AC」的机械护栏，但「最小」本身不可机械判定。 | §5 L178 独立读取 | **NON-BLOCKING**（RERUN-01 NB-06 的残余部分，已由追溯要求大幅收敛，但未达 100% 可量化）。建议 Implementation 合同阶段以 diff 白名单方式固化。 |

**Observations（非 finding）**

| ID | 内容 |
|---|---|
| **OBS-R2-01** | Candidate 首行前缀为 `[AI Development Workflow｜UI-I01-DESIGN-01-FIX-01 v0.1｜Rules 0.1.0｜Rule Load: PASS]`，Workflow Name 取治理域名称，而 §1 的 Project 为 `MarketPulse-AI`。仅命名/呈现层面 —— Rules 版本与 Rule Load 结论均与本次独立加载一致。（同 RERUN-01 OBS-01） |
| **OBS-R2-02** | §15 的可访问性要求（`aria-current`、`aria-expanded`、键盘/focus、WCAG AA、live-region 语义、不抢焦点）超出冻结 §35 的范围（§35 仅要求「状态/严重度/数据质量绝不可仅依赖颜色」+ 桌面视口），属 additive 的设计增强。非冲突且有益，属可接受 design choice —— 建议表述上与冻结项区分，避免被后人误读为冻结值。（同 RERUN-01 OBS-02） |

---

## 17. Changes

```text
NONE
```

- 未修改 Candidate（NO CANDIDATE MUTATION）✅
- 未持久化 Candidate（NO PERSISTENCE）✅
- 未 Freeze ✅
- 未创建 lint tooling ✅
- 未开始 Implementation ✅
- 未修改任何仓库文件、配置、数据库、Git 状态或服务运行状态：会话前后 MarketPulse `git status --porcelain` 条目数恒为 **32**；MarketPulse remote main 恒为 `8c94ea33…`；治理仓 remote main 恒为 `cbc1a221…`（会话期间未变）✅
- 临时证据仅写入 `C:/Users/hua/AppData/Local/Temp/`（仓库外）与 `E:/Documents/AI-Developer/review-evidence/UI-I01-DESIGN-R01-RERUN-02/`（证据目录，非仓库）✅

---

## 18. Verification

| 项 | 手段 | 结果 |
|---|---|---|
| Rule Load | 读治理仓 main `cbc1a221` 的 Bootstrap / Manifest / 6× REQUIRED_ACTIVE / PROJECT_STATE / EMRP profile | 6/6 FULL，**PASS** |
| MarketPulse remote main | `git ls-remote origin refs/heads/main`（会话前后各一次） | `8c94ea33…` **MATCH** |
| Workflow remote main | `git ls-remote origin refs/heads/main`（会话前后各一次） | `cbc1a221…` **ADVANCED / NON-MATERIAL**（NB-R2-01） |
| 治理推进 material 性 | `gh api .../compare/16d260fa...cbc1a221`（ahead/behind/files）+ 读 `cbc1a221` 上 manifest | 规则面零变更；Rule Pack `0.1.0`；6× `ACTIVE` |
| Candidate 字节身份 | `fs.readFileSync` + SHA-256 + git-blob-SHA1 + CRLF/孤立符统计 + 逻辑行数 | 41170 B / `f3b5ff12…` / 692 行 —— **三项全 MATCH** |
| Candidate 完整性 | 首 12 行 + 末 16 行检查（闭合围栏 + 四 NO 收尾块） | 完整、无截断 |
| Candidate §3 tree/local-main/HEAD 三项 | `git rev-parse <sha>^{tree}` / `refs/heads/main` / `HEAD` | 三项全 **MATCH** |
| NB-01 冻结源 | 读 UI-V1-D01 §34（L1052-1056） | 逐条对齐 |
| NB-02 枚举与轴 | 读 `models.py`（`ProjectionState` 5 成员 / `DEGRADED` 0 次）+ `generated.ts`（`DEGRADED` 仅 2 处，均在 `HostLifecycleState` / `HostReadinessStatus`） | **MATCH** |
| NB-03 endpoint vs section 失败 | 读 `system.py` L264-275（`_product_snapshot_failure`）、L276-313（openapi + docstring）、L406-414（incident section）、L380-388（recovery section）、L567（partial）+ Product Read 正式设计 §17/§18 | **MATCH**（无 authority conflict） |
| NB-04 422 路径 | 读 `cursor.py`（`ProductCursorError`）+ `system.py` L174-177（422）+ `queryClient.ts`（不 retry 4xx）+ `errors.ts`（仅 UnauthorizedError 可失效 session）+ `transport.ts` | **MATCH** |
| NB-05 默认值 | 读 `system.py` L300 `Query(default=None)` + L302 `Query(default=100, ge=1, le=500)` + Product Read §13.2 L548（`limit = 100`） | **MATCH** |
| NB-06 Shell boundary | 读 `routes.ts`（5 路由 / `DEFAULT_PRODUCT_ROUTE=/overview` / `LOGIN_ROUTE=/login` / `/system` ownerBatch=`UI-I01`）+ `router.tsx`（index 与 `*` 均 Navigate 至默认）+ `ProductShell.tsx` | **MATCH** |
| NB-07 rebind Gate | 逐行读 §3 L110-131 + 任务卡 8 项逐一对照 | **8/8 COVERED** |
| Lint 时序 | 读 §2 L60-72 / §17 L489 / §20 L594 / §21 L632 / AC-18；实测 `frontend/package.json` 无 `lint` script、无 eslint | **MATCH（时序合理，不阻断 Freeze）** |
| Regression 15 项 | 文本断言扫描 + 对 main `8c94ea33` 的 `models.py` / `system.py` / `cursor.py` / `queryClient.ts` / `transport.ts` / `readiness.ts` / `errors.ts` / `ProductShell.tsx` / `AuthSessionProvider.tsx` / `generated.ts` 事实交叉核验 | **15/15 PRESERVED** |
| Scope 10 类越界 | 全文术语扫描 + 逐处章节语境判定 + AC/章节数结构比对 | **10/10 NO EXPANSION** |
| generated types | 30/30 schema 名在册；`/api/v1/product/system` 与 `/api/v1/ready` 路径字面量在册 | **PASS** |
| 仓库零变更 | 会话前后 `git status --porcelain` + 双仓 `ls-remote` | 未变更 |

---

## 19. Remaining

1. 本 successor Candidate **可进入 Human Design Confirmation**（`READY FOR HUMAN DESIGN CONFIRMATION`）。
2. NB-01～NB-07 已全部独立复核为 **CLOSED**；RERUN-01 的 7 项 NB 均已闭环，**无遗留未关闭项**。
3. 本轮新增 3 项 NON-BLOCKING（NB-R2-01 治理 main 已推进 / NB-R2-02 时区测试用例未枚举 / NB-R2-03 Shell「最小」限定词残余），**均不阻断** Design Review / Human Confirmation，可在 Freeze 或 Implementation 合同阶段收敛。
4. Implementation 的明确前置（依 §21 路径）：独立 lint Foundation Accepted → §3 Rebind Gate（含本轮 NB-R2-01 的治理 main 复验）→ 绑定精确 Implementation Baseline / Frozen Requirement identity / Verification Profile / Required Evidence → 独立 Implementation Authorization。
5. 本轮 **不派发**任何后续任务；`UI-I05` 等仍为 **NOT AUTHORIZED**；Design Acceptance / Freeze / Implementation Authorization 均**未被本轮解锁**。

---

## 20. Evidence

**Review Target（本次 dispatch 附件）**
- `C:\Users\hua\Downloads\UI-I01-Implementation-Requirements-Candidate-v0.1.1.txt`
- 41170 B / SHA-256 `f3b5ff12b99f82bc2a37ac488c70d7efea719582b454a0f0fde37e0c33f0c834` / git-blob-SHA1 `22a4b75c5abc416ed9b4cfd888c70bfe31594849` / CRLF=691、loneLF=0、loneCR=0、无尾换行 / 692 逻辑行

**Parent 参照物**
- `C:\Users\hua\Downloads\UI-I01-Implementation-Requirements-Candidate-v0.1.txt`（27750 B / `96425e35…` / 565 行）
- `E:\Documents\AI-Developer\review-evidence\UI-I01-DESIGN-R01-RERUN-01\UI-I01-DESIGN-R01-RERUN-01-RESULT-v0.1.md`（50140 B；NB-01…NB-07 = OPEN；Blocking = 0）
- `E:\Documents\AI-Developer\review-evidence\UI-I01-DESIGN-R01-RERUN-02\UI-I01-DESIGN-R01-RERUN-02-RESULT-v0.1.md`（前次 `BLOCKED / INPUT_IDENTITY_MISMATCH`，仅作 input-layer failure history）

**远端 refs（实读）**
- `MarketPulse-AI`：`8c94ea338f500e2ea4dd2f8a5ccc81a65502468e refs/heads/main`；tree `941a52985bc16fe054bbd9cb4e2f43739333817b`
- `ai-dev-workflow`：`cbc1a221646a9f4703a65e626e58cf192ed96426 refs/heads/main`（任务卡/Candidate 预期 `16d260fa…`；compare ⇒ ahead 3 / behind 0，规则面零变更）

**MarketPulse 实读文件（main `8c94ea33`，经 `git show` 读取 immutable objects）**
- `backend/src/marketpulse/api/product/{models.py,system.py,cursor.py,context.py}`
- `backend/src/marketpulse/g4/models.py`
- `frontend/src/api/{transport.ts,readiness.ts,errors.ts,client.ts,generated.ts}`
- `frontend/src/app/{routes.ts,router.tsx,ProductShell.tsx,queryClient.ts}`
- `frontend/src/auth/AuthSessionProvider.tsx`
- `frontend/package.json`
- `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（§7 / §8 / §30 / §34 / §35）
- `docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`（§5 / §6 / §13.2 / §17 / §18 / §19 / §20）

**治理文件（main `cbc1a221`）**
- `AI_WORKFLOW_BOOTSTRAP.md`、`governance/WORKFLOW_RULE_MANIFEST.md`（Rule Pack `0.1.0`，6× `REQUIRED_ACTIVE` / `ACTIVE`）
- 6× REQUIRED_ACTIVE：`AUTHORITY_RULES` / `TASK_CONTRACT_RULES` / `ROLE_AUTHORITY_RULES` / `RISK_AND_ACCEPTANCE_RULES` / `CONTEXT_AND_HARNESS_RULES` / `SELF_HOSTING_RULES`
- `PROJECT_STATE.md`、`governance/profiles/EXECUTION_MODEL_ROUTING_PROFILE.md`（EMRP-1.1）

**本轮生成的证据工件**
- `E:\Documents\AI-Developer\review-evidence\UI-I01-DESIGN-R01-RERUN-02\UI-I01-DESIGN-R01-RERUN-02-RESULT-v0.2.md`（本文件）

---

**Fix Summary 复核（Designer 自述 vs Reviewer 独立判定）**

| Finding | Designer 自述 | Reviewer 独立判定 | 一致 |
|---|---|---|---|
| NB-01 | CLOSED IN CANDIDATE：§9/17、AC-09 | **CLOSED**（§5；另超出最低要求覆盖 DST / null 边界） | ✅ |
| NB-02 | CLOSED IN CANDIDATE：§10/17、AC-06 | **CLOSED**（§6；ProjectionState 5 成员 / DEGRADED 在 axis enum） | ✅ |
| NB-03 | CLOSED IN CANDIDATE：§10/11/17、AC-08 | **CLOSED**（§7；未构成 authority conflict） | ✅ |
| NB-04 | CLOSED IN CANDIDATE：§11/13/17、AC-11 | **CLOSED**（§8；422 路径与 backend 契约对齐） | ✅ |
| NB-05 | CLOSED IN CANDIDATE：§13/17、AC-11 | **CLOSED**（§9；`Query(default=None)` 逐字核实） | ✅ |
| NB-06 | CLOSED IN CANDIDATE：§5/17、AC-02 | **CLOSED**（§10；残余「最小」限定词 → NB-R2-03） | ✅ |
| NB-07 | CLOSED IN CANDIDATE：§3/17/20/21、AC-18 | **CLOSED**（§11；8/8 COVERED） | ✅ |

「AC-01～AC-20 保持原编号；未新增 AC」经独立核实为 **真**（`new AC = NONE`）。

---

**Acceptance Boundary**

本结果 = **Review Verdict only**。**NOT** DESIGN ACCEPTED、**NOT** FROZEN、**NOT** IMPLEMENTATION AUTHORIZED、**NOT** IMPLEMENTED。不解除任何 Gate，不派发下游任务。
