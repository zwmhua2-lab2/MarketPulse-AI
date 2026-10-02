[AI Development Workflow｜UI-I01-DESIGN-01-FIX-01 v0.1｜Rules 0.1.0｜Rule Load: PASS]

# UI-I01 Implementation Requirements Candidate v0.1.1

**Result：`DESIGN CLARIFICATION COMPLETE / READY FOR FOCUSED INDEPENDENT RE-REVIEW`**

本 Candidate 仅在本回复中交付。`Repository Changes: NONE`。未持久化、未 Freeze、未授权 Implementation。

## 1. Candidate Identity

| 项目 | 值 |
|---|---|
| Design Task | `UI-I01-DESIGN-01-FIX-01` |
| Parent Design Task | `UI-I01-DESIGN-01` |
| Review Source | `UI-I01-DESIGN-R01-RERUN-01` |
| Candidate | `UI-I01 Implementation Requirements Candidate v0.1.1` |
| Work Package | `UI-I01｜Global Shell + System` |
| Project | `MarketPulse-AI` |
| Repository | `zwmhua2-lab2/MarketPulse-AI` |
| Role | `Designer` |
| Mode | `STRICT DESIGN FIX / READ_ONLY REPOSITORY / NO IMPLEMENTATION` |
| Candidate Authority | `CANDIDATE / NOT ACCEPTED / NOT FROZEN` |
| Candidate Carrier | 本回复正文；未生成 repository artifact |
| Implementation Authorization | `NOT GRANTED` |

Parent 原始文件已实际读取并精确核验：

```text
Parent: UI-I01 Implementation Requirements Candidate v0.1
Input: C:\Users\hua\Downloads\UI-I01-Implementation-Requirements-Candidate-v0.1.txt
Bytes: 27750
Logical Lines: 565
SHA-256:
96425e35afff9d5e9d7427049ea8e81feb403063003f72352baec87e3cdf331d
Input Identity: MATCH
```

前序 Review 绑定采用任务给定的 `PASS WITH NON-BLOCKING FINDINGS / READY FOR HUMAN DESIGN CONFIRMATION`，Blocking Findings = `0`。本轮仅澄清 NB-01～NB-07，不把该 Review 改判为 FIX REQUIRED、Design Rejected、Requirement Frozen 或 Human Accepted。

任务推荐执行配置为 `GPT-6.1 Sol / Medium / ChatGPT Web`。本轮实际运行于 Codex desktop；不把推荐值作为实际 Model SKU 或 Reasoning 的实测声明。

## 2. Governance Binding

| Binding | 当前核实值 |
|---|---|
| Governance Repository | `zwmhua2-lab2/ai-dev-workflow` |
| Governance Accepted Main | `16d260fad1d4580d90468c2b0cab6dd807d9f7a9` |
| Governance Version | `0.1.0` |
| Rule Pack Version | `0.1.0` |
| Rule Manifest | `fd00-rule-manifest/0.1.0` |
| Governance Mode | `SELF_HOSTED` |
| Required Active Rules | 六份已完整读取 |
| Execution Routing Profile | `EMRP-1.1 / ACTIVE` |
| Legacy `ai-dev-protocol` | `REFERENCE ONLY / NON-AUTHORITATIVE` |

本轮绑定用户当前指令、已接受 Workflow、Frozen UI 设计及当前 accepted implementation。Designer 只生成 Candidate，不执行 Acceptance 状态转换。

**用户补充决定已纳入合同：**

> lint tooling 另走 Foundation 任务，作为 UI-I01 Implementation 前置条件。

该决定不授权本轮创建 Foundation 任务或修改 tooling。

```text
Lint Foundation: SEPARATE TASK
Design Review: NOT BLOCKED
Requirement Freeze: NOT BLOCKED
Implementation Authorization:
BLOCKED UNTIL LINT FOUNDATION ACCEPTED
```

Lint acceptance 不得被写成 Freeze 前置。

## 3. Repository Binding

开始与结束均通过 `git ls-remote origin refs/heads/main` 核实：

| Repository | Remote `main` | 与任务要求 |
|---|---|---|
| MarketPulse-AI | `8c94ea338f500e2ea4dd2f8a5ccc81a65502468e` | MATCH |
| ai-dev-workflow | `16d260fad1d4580d90468c2b0cab6dd807d9f7a9` | MATCH |

MarketPulse 本轮读取基线：

```text
Accepted Main SHA / Design Task Base:
8c94ea338f500e2ea4dd2f8a5ccc81a65502468e

Accepted Main Tree:
941a52985bc16fe054bbd9cb4e2f43739333817b
```

当前 cwd 的实际状态：

```text
Branch:
prb-01-product-requirements-baseline

HEAD:
d47313a1cb41996410606fe92b286a5046ed4fce

Local main:
d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b
```

本地 checkout 明显落后于任务基线，并包含既有 modified/deleted/untracked 内容。已检查 `git log`、`git diff`；本轮通过 `git show origin/main:<path>` 读取与 remote 完全匹配的 immutable objects，未切换或修改 checkout。

**未来 Implementation 不得直接使用该旧 checkout。** Design Task Base 不自动成为届时 Implementation Task Base。

**Implementation Baseline Rebind Gate（NB-07）：**

Implementation Authorization 前必须提供 `Latest-main currency / delta reconciliation` evidence，逐项记录实际身份/值、来源、delta、判定及未决事项：

| 必核项 | 机械检查与 evidence |
|---|---|
| Current MarketPulse `origin/main` | 实时读取 remote main 并核对 remote-tracking ref；记录 SHA/tree、Design Task Base → current main 的 log/diff 与 proposed Implementation Task Base |
| Current Workflow `origin/main` | 实时读取 remote main；核验 bootstrap、manifest、六份 active rules 与适用 profile 的身份/版本及 governance delta |
| Frozen Requirement identity | 核验届时 Human-confirmed、persisted/frozen 的 exact carrier、version、bytes、SHA-256、Git blob/commit（适用时）及 Review/Confirmation/Freeze evidence；当前 v0.1.1 仍是 Candidate |
| Accepted lint Foundation identity | exact accepted candidate/commit、Acceptance evidence、lint config/manifest/lockfile identity 与正式可复现命令；tooling 存在或测试绿不能代替 Accepted |
| `API/generated.ts` compatibility | 核对实际 `frontend/src/api/generated.ts` 身份、System endpoint/DTO/enums/query/error compatibility 与 API drift evidence；不得手改或静默 regenerate 消除冲突 |
| Relevant Frontend Foundation delta | 核对 Shell、router/routes/default route、Auth/session、QueryClient、transport/readiness/retry 及相关测试的 baseline diff，确认本合同仍可由既有接口实现 |
| Parallel mutation status | 记录适用协调/dispatch/lock evidence、并行任务及重叠修改状态；remote SHA 不变不证明没有并行 mutation；未确认的重叠冲突不能通过 |
| Dirty workspace protection | 记录实施 workspace HEAD/branch/status/diff、已有 modified/deleted/untracked 及归属；区分 PREEXISTING_DELTA / TASK_DELTA，确认不会覆盖已有修改 |

current main 与 Design Task Base 不同，**不得自动判 stale failure，也不得自动通过**。先完成 reconciliation，再分类：

- `NON_MATERIAL`：证据确认 Frozen semantics、Scope、API compatibility 与 ownership 等当前契约仍成立；记录理由并显式 rebind 最新实施基线。
- `MATERIAL`：相关契约、Foundation 或 authority binding 有实质变化，需独立 currency/rebind review 或授权 amendment；停止受影响实施，不自行改设计。
- `BLOCKING`：关键身份/证据缺失或冲突、lint 未 Accepted、API 不兼容、并行修改冲突或脏改动无法保护；不得授权 Implementation。

全部必核项有可复核证据、material delta 已正式解决、current implementation contract 确认仍成立且无 unresolved blocking，才可进入独立 Implementation Authorization。授权前再次核验两库 remote main；新变化回到 reconciliation。Rebind 不自动授予实施权限，不授权 reset/rebase/clean、覆盖脏改动或扩大本 Fix Scope。

## 4. Authority Inputs

按用途及已接受 amendment 处理：

| 输入 | 本合同使用范围 |
|---|---|
| `PRODUCT_REQUIREMENTS.md` | Paper、只读产品边界及安全原则 |
| `DECISIONS.md`、`PROJECT_STATE.md`、相关 `dev_log` | 已接受决策、当前能力与历史状态调和 |
| `UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md` | 五页 IA、System 职责、状态、时区、可访问性及实施顺序 |
| `UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md` | typed readiness、session request ownership 等修订 |
| `UI-RD01-Product-Read-API-Formal-Design.md` | DTO、partial、failure、snapshot、认证与 generated-types 边界 |
| 当前 `UI-RD01-I01` 源码和测试 | `SystemIncidentRead` 实际可消费接口 |
| 当前 `UI-F01` 源码和测试 | 唯一 Shell、Router、Query、Auth、Transport 与测试基础 |

Parent Design 中“尚未实现”的历史描述不覆盖后续 accepted implementation。当前源码及 closeout 记录确认：

- `UI-F01 = ACCEPTED / COMPLETE`；
- `UI-RD01-I01 = ACCEPTED / COMPLETE`；
- CR-01、CR-02、CR-05 remediation 已接受完成；
- 正式 `/system` Product UI 仍为 Foundation placeholder。

## 5. Scope

未来 UI-I01 仅实施：

1. 在现有 `ProductShell` 内集成 `/system` 正式页面。
2. 保留唯一 navigation、route metadata、AuthSessionProvider 与 QueryClient。
3. 消费 `GET /api/v1/product/system` 的 12 个正式 section。
4. 实施 DTO 驱动的 loading、数据状态、partial、failure 与安全提示呈现。
5. Incident 的筛选、cursor 翻页和当前 row 详情展开。
6. 手动刷新、可访问性、响应式布局及确定性测试。

**未来允许修改面：**

- `/system` 页面及其局部组件、query、presentation mapping；
- `ProductShell.tsx` 仅限下述 Global Shell Allowed Change Boundary；
- `router.tsx` 中 `/system` placeholder 的替换；
- System 所需局部样式和最小展示 primitives；
- 相关 frontend fixtures、focused tests，以及必要既有回归调整；
- Implementation 完成后的最小状态记录，需由届时合同明确路径。

**Global Shell Allowed Change Boundary（NB-06）：**

- 在现有 authenticated Shell 的 `Outlet` 内接入 System；`router.tsx` 仅替换 `/system` 的 placeholder。
- 保持五页 navigation IA、顺序、title/path/ownerBatch、route metadata、Auth wrapper 与默认路由。
- `ProductShell.tsx` 仅允许 System 进入既有 Shell 所必需的最小文案/语义标记/accessibility 修正；每处差异必须追溯至 System integration 或既有 accessibility AC。
- System 布局/样式限制在 System route 内容与局部组件；最小展示 primitives 不得改变其它四页行为/ownership 或共享 Shell 布局。

**Global Shell Forbidden Change Boundary（NB-06）：**

- 不改变其它四页 placeholder、ownership 或页面实现。
- 不改变 `DEFAULT_PRODUCT_ROUTE=/overview`、index/unknown-route redirect、`/login` 或 route topology。
- 不新增/删除/重排 navigation，不重新设计 navigation 或全局视觉/布局。
- 不新增第二套 Shell/provider/Auth/QueryClient/API client/router，不改 sign-out/session/transport/readiness/global retry 所有权。
- 不使 Shell 或其它四页产生 System query，不触发 UI-I02～I06 实现。

复用的 auth、transport、readiness、provider 与全局 retry 所有权保持现状。

## 6. Out of Scope

不实施：

- Overview、Market、Opportunity、Trading、Edge Lab；
- Real AI、live `G2→G3`、Gate A/B/C、Live 或 Live Trading 激活；
- Backend Product API redesign、新 endpoint 或 DTO 扩展；
- Schema、migration、index、数据库或服务状态变更；
- `UI-RD01-I04 / EdgeAggregateRead`；
- 第二套 Shell、API client、Auth、Routing、QueryClient 或全局 store；
- 全局 UI redesign；
- lint tooling、lint dependency/configuration 或对应 manifest/lockfile 修改。

禁止业务 mutation controls，包括 `Enable AI`、`Activate Gate`、`Start Live`、Pause、Resume、Emergency Stop、Block、Unblock、Resolve Incident、Repair 及交易动作。

## 7. Current Implementation Facts

| 对象 | 当前源码事实 |
|---|---|
| Shell | `ProductShell` 使用现有 `NavLink`、`Outlet`、`signOut()` |
| Routes | 五条产品 route；`/login` 独立；默认 route 为 `/overview` |
| `/system` | 当前仍渲染 `FoundationPlaceholder` |
| Query | 单一 TanStack QueryClient；无全局 polling；focus 不自动 refetch；reconnect 可 refetch |
| Retry | NetworkError / retryable 5xx 最多两次 retry；401、普通 4xx、UnexpectedResponse 不 retry |
| Transport | `openapi-fetch` + generated `paths` + `requestData()` |
| Auth | bearer 存于既有 session boundary；本地 ephemeral generation 对 protected 401 fencing |
| `/ready` | typed `200 READY`、typed `503 NOT_READY`；矛盾响应进入 UnexpectedResponse |
| System API | 一个 authenticated endpoint，返回 12 个 section |
| Incident | 支持 status/type、limit、opaque cursor；没有独立 detail endpoint |
| Tests | Vitest、RTL、user-event、MSW；未处理请求作为测试错误 |
| lint | `package.json` 无 lint script；无现有 ESLint configuration |

当前 System Health 的 `overall_status` 由 backend projection 生成。UI 分离 Live、Ready、Health 的展示与数据读取，不改变 backend 内部算法。

## 8. UI Contract

页面按以下顺序分解：

| 区域 | 内容 |
|---|---|
| 页面上下文 | 系统、只读标识、Runtime mode、instance、snapshot、刷新状态 |
| 需关注 | 权威 blocking incident count、明确安全问题、partial/unavailable 提示 |
| 运行基础状态 | **Live、运行就绪 Ready、Health 三个独立区域** |
| Runtime / Operator | lifecycle、gates、运行遥测；Operator Intent 与 System Derived State 分开 |
| 行情 / Provider / Lanes | Market quality、Provider、Scanner lane、Safety lanes 分开 |
| Database / Singleton | DB resource facts 与 singleton fence facts 分开 |
| Recovery / Reconciliation | 两个独立区域；Reconciliation 标明 detector-only |
| Incidents | 默认 OPEN、完整可翻页列表入口、row 详情 |
| AI / Advisory | 当前激活字段与已接受设计背景分别呈现 |

Shell 保留五页 IA、现有默认 route 与退出登录行为。其它四页继续使用 placeholder。Shell 集成不使其它页面额外请求 System API。

产品边界“纸面 / 现货 / 仅做多”与 Runtime mode 分开。Runtime mode 使用后端值：

```text
LIVE_PAPER → 实时纸面
REPLAY     → 回放
TEST       → 测试
```

不得把 Live 卡片的“进程存活”表述为 Live Trading 已开启。

## 9. Data / DTO Mapping

唯一数据请求：

```text
GET /api/v1/product/system
```

类型来自：

```text
components["schemas"]["SystemIncidentReadResponse"]
SystemIncidentReadResponse["data"]
SystemIncidentDataDTO 的各 section
```

ViewModel 只允许生成展示标签、格式化文本、样式与局部交互状态；保留原始 DTO 值及来源引用，不建立重复 authority DTO。

| DTO 路径 | UI 映射与限制 |
|---|---|
| `meta` | projection、contract version、双轴 capability、projection state、partial、snapshot |
| `operational_context` | run_mode、instance、host_state、provenance、context timestamp |
| `live.data` | `alive`、run_mode、local_only、instance_id、host_state；不推断 Ready |
| `ready.data` | `ready`、`status`、`reasons`、`evaluated_at`；不推断 Health 或 risk admission |
| `health.data` | `overall_status`、checks 的 name/status/reason/updated_at |
| `runtime.data` | lifecycle、uptime、instrument arrays、children、四个 gates、timestamps |
| `market_provider.data` | provider 状态与计数、subscriptions；逐 instrument present/fresh/quality |
| `lanes.data` | Scanner 与 Safety 分组；size/capacity/high_water/processed/rejected/overflow |
| `database_singleton.data` | application_name、engine ownership/disposal、singleton 三个显式事实 |
| `recovery.data` | status/ok、开始/结束/ready 时间、reason、final states、reconciliation_ok |
| `reconciliation.data` | startup_ok、last_ok、last_result、diagnostics、latch 与时间；不提供修复 |
| `operator_system_state.data` | operator_state、system_state、blocking_incident_count |
| `incidents.data` | items 与 next_cursor；保留每条实际 run_mode |
| `ai_activation.data` | activated、reevaluation_enabled、status、note |

每个 section 展示自己的 `state`、`snapshot_at`、`source`、`read_failure_reason`。不宣称全页面 global ACID snapshot。

**Timezone Presentation Contract（NB-01）：**

严格沿用 Frozen UI-V1 §34：

- System 主 UI 的所有展示时间使用**浏览器本地时区，并带可见时区指示**；不得固定为部署或用户推定时区。
- Technical trace 使用 **UTC ISO 8601**，明确标识 UTC。同一字段两种呈现表示同一 instant。
- 时间事实全部来自 backend DTO：`meta.snapshot_at/observed_at`、`operational_context.context_snapshot_at`、各 section 的 `snapshot_at/source.snapshot_at`、Ready `evaluated_at`、Health checks `updated_at`、Runtime 的各 timestamps、Recovery `started_at/finished_at/ready_at`、Reconciliation `snapshot_at/last_reconciliation_at`、Incident `opened_at/resolved_at`。
- ViewModel 仅做 presentation formatting，保留原始 DTO 时间及来源；不以浏览器读取/渲染时间替换 backend 时间。nullable 时间显示未提供，不补当前时间或推断 Recovery。`uptime_seconds` 是 backend duration，不作为日期套用时区。
- 显示“距快照时间”只能作为注明来源的年龄展示；不得改变 event ordering、Incident 排序/cursor、freshness、ProjectionState 或 backend timestamp authority。
- Frozen 自定义范围仍为 `[start,end)`、本地边界转 UTC 后查询；UI-I01 不因此新增时间范围筛选。

**字段不足边界：**

- Incident DTO 没有逐条 `blocking` 字段，不伪造该字段或将总 count 分摊到 rows。
- 可对已冻结的 `POSITION_UNPROTECTED` 等明确事实应用既有展示严重度；不创建新的 blocking 判定算法。
- 当前 DTO 不提供完整 Position Protection 投影，不增加“所有仓位均受保护”结论。
- `market_provider.provider` 不得被标注为 Real AI Provider。
- 未知字符串状态保留原始 code 并显示“未识别状态”，不猜测成正常。

## 10. State Model

Request lifecycle、Product capability、Projection state、Health/readiness 与业务运行状态分别处理。下表包含不同状态轴和组合条件，**不是一个 enum**。

| 状态轴 | 本页消费与限制 |
|---|---|
| Product Projection State | `FRESH / STALE / EMPTY / UNAVAILABLE / CAPABILITY_NOT_INTEGRATED`，来自 `meta.projection_state` 或 section `state` |
| Capability | `read_surface_class` 与 `operational_availability` 两轴，不由请求成功或 Health 推断 |
| Request lifecycle | loading/refetching/error 等由既有 Query lifecycle 表达 |
| Health / readiness | Ready `status/reasons`、Health `overall_status/checks` 分别表达 backend 条件 |
| Runtime lifecycle / business state | Runtime lifecycle、Host state、Operator/System 继续使用各自字段 |

`DEGRADED ≠ ProjectionState enum member`。它可出现在既有 `HostReadinessStatus`、`HostLifecycleState` 及 backend Health status。System Ready/Health 可呈现 DEGRADED，同时对应 section 仍为 FRESH。UI 注明所属对象/轴，不把 DEGRADED 转成 projection state，不联动改写其它轴，不新增 authority enum。

| 状态 | 必须行为 |
|---|---|
| 首次 loading | 显示加载；不显示默认 healthy、false、0 或空列表 |
| success / FRESH | 按 DTO 展示；FRESH 仅说明 projection，不代表 Runtime 健康 |
| legal EMPTY | 仅在成功、权威 EMPTY 的 section 显示空态 |
| DEGRADED（Health/readiness 或 Runtime lifecycle 条件） | 展示对应 backend 字段与原因；不是 ProjectionState，不改写其它对象或轴 |
| STALE | 可保留后端 last-known 数据，显式标记陈旧及来源时间 |
| UNAVAILABLE | 显示暂不可用与正式 failure reason；不替换为 zero/empty |
| CAPABILITY_NOT_INTEGRATED | 显示尚未接入；不当作暂时故障或无记录 |
| partial | HTTP 200 保留可用 sections；Incident SOURCE_UNAVAILABLE、Recovery SNAPSHOT_FAILED 为 section-level failure，不升格为 endpoint 503 |
| refetching | 保留旧结果但标明正在更新及旧 snapshot |
| refetch failure | 标明更新失败、当前为上次成功读取；不得继续声称是最新结果 |
| invalid response | 进入响应格式错误边界；不填充缺失业务事实 |

Host absent 的合法结果：

```text
HTTP 200
read_surface_class = A
operational_availability = NOT_ACTIVATED
projection_state = UNAVAILABLE
read_failure_reason = null
data = null
```

显示“运行能力未激活，本次没有可展示的 System projection”，不伪造 source failure。

TanStack Query 的 cache `stale` 不映射为 Product `STALE`。显示年龄时使用 section 权威时间并注明“距该快照时间”；不得据浏览器时间重新判定 backend freshness。

## 11. Error Model

| Error | UI 行为 |
|---|---|
| `UnauthorizedError` | 交由既有 session boundary；不显示空数据 |
| `NetworkError` | 请求未完成；继承 Foundation bounded retry |
| Product `/system` `503` | HttpError；当前 endpoint-level failure 仅为 SNAPSHOT_FAILED；消费正式 ProductUnavailableResponse identity/failure/correlation ID，不称为 endpoint SOURCE_UNAVAILABLE 或 /ready NOT_READY |
| `500` | 脱敏通用错误；仅展示可用 correlation ID |
| `422` | 参数/cursor 无效的 HttpError；显式 reset 筛选/pagination 后读取合法第一页；不造 cursor、不转 NetworkError、不自动 retry、不重置 auth/session |
| UnexpectedResponse | 响应格式/协议错误；不自动改写为网络故障 |
| 非预期其它 HTTP | 保留 HTTP 分类，使用安全通用文案 |

当前 System endpoint 无法取得所需 Host snapshot（异常或 None）才返回 `503 SNAPSHOT_FAILED`。Incident source 不可用或 Recovery snapshot 缺失保留为 `200 + is_partial=true`，对应 section `state=UNAVAILABLE` 与正式 failure reason。共享 ReadFailureReason 包含两种值不意味着该 endpoint 实现了两种 endpoint 503。503 reason 若不符合当前 contract，保留 HTTP/协议异常展示，不接受为新产品语义。

不渲染 arbitrary error body、stack、SQL、connection detail、token 或内部 exception 文本。

`GET /api/v1/ready` 的合法 503 继续由 `readReadiness()` 解释为 NOT_READY，不 retry。**此例外不得扩展至 Product System 的 503。**

## 12. Auth / Session Boundary

- `/system` 位于现有 `RequireAuth` 内。
- 使用 `useApiClient()`；由既有 client 注入 bearer。
- 不读取、解析或持久化新的 auth identity。
- 当前 generation protected 401 清 session/cache 并进入 Login，保留安全 intended route。
- 旧 generation 或已卸载 Provider 的 401 不清新 session/cache。
- Login 401 保持 invalid credentials，不产生重定向循环。
- System query 消费 Query 的 cancellation signal，不引入第二套 ownership fence。
- sign-out 后不得继续展示 authenticated System data。

## 13. Query / Refresh Boundary

Query key 统一为：

```text
[
  "product",
  "SystemIncidentRead",
  {
    incident_status,
    incident_type,
    limit,
    cursor
  }
]
```

所有请求参数进入 key；不加入 token、password、session_generation 或未发送的伪参数。

**策略：**

- 首次进入 `/system` 发起读取；
- UI-I01 Product UX 默认显式发送 `incident_status=OPEN`、不限定 type、`limit=100`、无 cursor；
- 手动“刷新”重置到首个 cursor page 并请求最新结果；
- 无 timer polling；沿用 Foundation reconnect、focus 与 bounded retry；
- 同 key 请求由现有 QueryClient 去重；
- filter/cursor 切换不把旧参数结果呈现为新参数结果；
- 只读取已有 endpoint，不新增 `/runtime` 或其它弱读面补数据。

**API default 与 UI default ownership（NB-05）：**

```text
Backend API default: incident_status = None
UI-I01 Product UX default: incident_status = OPEN
```

API 参数省略时不限定 status；UI 首次 query 主动发送 OPEN。选“全部”时省略 status filter，不发送自造 ALL enum。OPEN 不是 Backend endpoint default；不修改 Backend、DTO 或 generated types。

筛选可使用 URL / Router；row 展开状态使用局部 React state。

**422 invalid cursor reset（NB-04）：**

invalid/malformed 或与筛选不匹配的 cursor 由 backend 返回 422。UI 提供显式 reset：筛选与 pagination 回到 OPEN、不限定 type、limit=100、无 cursor；清除旧 next_cursor/分页状态，使用相应 query key 请求合法第一页。不得创建替代 cursor，后续 cursor 只来自合法响应。422 不作为网络故障 retry，不清 token、不 reset session generation、不清全局 authenticated cache、不跳 Login。

**Incident 边界：**

- 提供 OPEN / RESOLVED / 全部和 generated `IncidentType` 筛选；
- cursor 原样传递，不解析、不改造成 offset；
- 保持 backend `(opened_at DESC, incident_id DESC)` 顺序；
- 每页独立呈现，不无界累积；
- 有 next_cursor 时显示“还有更多”，不称首个 100 rows 为全部；
- 没有 total count，不编造总数；
- 详情只展开当前 DTO 的八个字段；不调用不存在的 detail endpoint；
- 翻页不声明跨请求历史 snapshot 固定。

## 14. Component Decomposition

建议最小模块：

| 模块 | 职责 |
|---|---|
| `SystemPage` | 页面组合、query 参数与刷新 |
| `systemQuery` | 唯一 typed GET、query key/options |
| `systemPresentation` | DTO → label/format/style 的纯映射 |
| `SystemSection` | section state、source、timestamp 与局部 fallback |
| `SystemRuntimeSummary` | Live / Ready / Health、Runtime、Operator |
| `SystemInfrastructure` | Market/Provider、Lanes、DB/Singleton |
| `SystemRecovery` | Recovery 与 Reconciliation |
| `SystemIncidents` | 筛选、cursor page、row 展开 |
| `SystemAIState` | API 激活事实与明确标注的设计背景 |
| `SystemErrorBoundary` | System render failure containment |

这些是组件职责，不要求逐行或逐字段拆组件。

System render error boundary 放在 `/system` route 内容边界，保留 Shell/navigation/sign-out。Query error 由页面状态处理；不把网络错误转成 render exception。fallback 不展示错误内部细节，允许重新尝试。

**`API/generated.ts`：**

- 直接依赖当前 generated types；
- 不手改、不复制 authority DTO；
- 本 UI-only 批次预期 generated artifact 零变化；
- drift 失败时停止，不能通过修改 Backend 或静默 regenerate 消除基线冲突。

## 15. Accessibility

- 简体中文主 UI、一个页面主标题、明确 section 标题层级；
- navigation 保留 `aria-current`；
- severity/state 同时提供文字，不能只用颜色；
- loading、刷新结果、局部失败使用合适的 live/status 语义，避免每个计数变化都触发强通知；
- 筛选、刷新、翻页、row 展开支持键盘，具有名称和可见 focus；
- 展开控件提供 `aria-expanded`；
- 表格保留 header；长文本换行，不只依靠 hover；
- 正文与控件满足 WCAG AA 对比度要求；
- 不因刷新自动抢走焦点。

## 16. Responsive Requirements

- 主验收视口：`1440 × 900`；
- 最低支持：`1280 × 720`；
- 较小窗口允许滚动、section 单列重排、导航换行；
- Live/Ready/Health 始终各自有清晰标签；
- critical state、reason、刷新与分页控件不能重叠或裁切；
- 长 instance/incident ID、diagnostics、reason 可换行；
- 局部宽表允许自身横向滚动，不使全页面关键状态不可达；
- 不引入 3D、WebGL、GPU-heavy animation 或装饰性 canvas。

## 17. Test / Verification Contract

**以下为未来 Implementation 验证合同；Authorization 前置为独立 lint Foundation 已 Accepted、提供正式 lint command/config，且 §3 Rebind Gate 满足。该前置不阻塞当前 Design Review 或 Requirement Freeze。**

Implementation 在精确 Candidate 上实际执行：

| 验证组 | 最低案例 |
|---|---|
| 路由 / Shell | /system 正常加载；按 §5 精确 allowed/forbidden boundary 核对 diff；五页 IA、navigation、其它四页 ownership/placeholder、默认 /overview、index/unknown redirect 不变；无第二套 Shell/provider、其它页 System query |
| 请求 / Auth | bearer 实际附加；无 session 进入 Login；当前 401 清 token/cache |
| Ownership | G1 晚到 401 不影响 G2；Provider unmount fencing；StrictMode 回归 |
| Lifecycle | 延迟响应 loading；成功；更新中；首次失败；更新失败保留带标记的旧结果 |
| Readiness | Product Ready 展示；既有 `/ready` 200/503 正常解析；矛盾 body 的 UnexpectedResponse |
| 数据状态 | FRESH、STALE、legal EMPTY、UNAVAILABLE、CAPABILITY_NOT_INTEGRATED、Host absent；ProjectionState 精确保持五个值 |
| 部分可用 | 200 + partial：Incident SOURCE_UNAVAILABLE 或 Recovery SNAPSHOT_FAILED，仅失败 section UNAVAILABLE，其它 sections 保留 |
| Endpoint 503 | snapshot acquisition 抛异常/返回 None 的正式 fixture：503 ProductUnavailableResponse + SNAPSHOT_FAILED + correlation ID；不接受 SOURCE_UNAVAILABLE 为该 endpoint 正式 503，不套用 /ready NOT_READY 例外 |
| DEGRADED axis | Ready/Health DEGRADED 与 section FRESH 共存；注明对应轴，不改变 ProjectionState、capability/request/lifecycle |
| 语义分离 | Live ≠ Ready ≠ Health；Risk gate 使用显式字段；Operator ≠ System；Recovery 不由时间推断 |
| Incident | 筛选、cursor 原样传递、同时间排序、下一页、EMPTY、row 展开 |
| Query default | 首次请求显式发送 OPEN；API default 仍为 None；“全部”省略 status filter；key 与实际参数一致，不声称 OPEN 是 API default |
| Invalid cursor 422 | invalid/malformed、filter-mismatch 返回 backend-contract 422；不造 cursor、不按 NetworkError retry、不 reset auth/session/token/cache 或跳 Login；用户 reset 后默认合法参数/无 cursor，第一页成功，后续 cursor 仅取自响应 |
| Timezone | 固定 DTO instant/clock，两个浏览器时区及 DST 场景验证主 UI 本地时间+时区指示、trace 同一 instant 的 UTC ISO 8601；覆盖 §9 所有时间/null；原始 DTO、排序/cursor/freshness 不因格式化改变 |
| AI | NOT_ACTIVATED 为 U0；与 Design Accepted 分开；不从行情 Provider 或 ingress 推断 AI |
| Read-only | 无禁止 controls；业务请求仅 GET；Login POST 保留 |
| Render error | System render throw 后 fallback；Shell/navigation/sign-out 仍可使用 |
| Accessibility | role/name、键盘、focus、非颜色状态、展开语义 |
| Responsive | 实际浏览器验证两个必需视口及较小窗口 |
| Types / Build | typecheck、focused tests、frontend full tests、build、API drift |
| lint | 独立 Foundation 提供的正式 lint gate |
| Baseline rebind | Authorization 前 §3 八项 evidence 完整；两库 current-main diff/classification/disposition 明确；current main 不同但 NON_MATERIAL 可显式 rebind，MATERIAL 未解决/BLOCKING 不可授权；脏改动/并行状态有证据 |

使用现有 Vitest / RTL / MSW，fixture 以 generated types 约束，固定 timestamp、IDs、顺序和错误分类。loading 用可控 promise；时钟测试用 fake clock。不得依赖真实 provider 或真实市场时机。

未来标准命令：

```text
npm run typecheck
npm run test:run -- <本批实际 focused test paths>
npm run test:run
npm run build
npm run check:api-drift
<accepted lint Foundation 定义的命令>
git diff --check
```

JS DOM 测试不作为真实 viewport 布局证明。保存实际浏览器布局、focus 与 console/network 证据；任何无法执行的项标记 `NOT VERIFIED`。

本轮设计没有执行上述 Implementation 验证，也不引用历史测试数量作为当前 PASS。

## 18. Acceptance Criteria

未来 UI-I01 至少逐项满足：

| ID | 验收要求 |
|---|---|
| AC-01 | `/system` 在唯一 authenticated ProductShell 中正常展示 |
| AC-02 | §5 Shell allowed/forbidden boundary 逐项满足；五页 IA、navigation、route metadata、默认 route、其它四页 ownership/placeholder 保持；无第二套 Shell/provider |
| AC-03 | 唯一 typed transport + generated DTO；不新增读取 endpoint |
| AC-04 | 12 个 section 均可追溯到正式 DTO 字段 |
| AC-05 | Live、Ready、Health 独立，无互相推断 |
| AC-06 | capability 两轴、ProjectionState、request lifecycle、Health/readiness/lifecycle 分离；DEGRADED 不作为 ProjectionState 成员，所属对象/轴明确 |
| AC-07 | loading/empty/stale/unavailable/not-integrated 不混用 |
| AC-08 | partial 200 保留可用 sections；section SOURCE_UNAVAILABLE/SNAPSHOT_FAILED 与 endpoint 503 SNAPSHOT_FAILED 分开；不套用 /ready 例外，不呈现 zero/empty |
| AC-09 | source/snapshot 可查看；§9 主 UI 浏览器本地时区并有时区指示、trace UTC ISO 8601；仅 formatting，backend 时间/排序/freshness authority 不变；无 global ACID 声明 |
| AC-10 | Recovery/Operator/System/Reconciliation 使用已有权威事实 |
| AC-11 | Incident 筛选/分页可用；首次 UI query 显式 OPEN ≠ API default=None；invalid/malformed cursor 422 可 reset 到合法第一页，不造 cursor、不当网络错误、不 reset auth/session；无假 total 或逐条 blocking |
| AC-12 | AI NOT_ACTIVATED 为 U0；Design Accepted 不表示 activated |
| AC-13 | 当前与旧 session 401 行为符合 Foundation ownership |
| AC-14 | 无业务 mutation controls、请求或激活副作用 |
| AC-15 | 手动刷新与缓存边界符合 §13；无 timer polling |
| AC-16 | System render failure 不破坏 Shell |
| AC-17 | 可访问性、必需 viewport、较小窗口符合 §15–16 |
| AC-18 | Implementation Authorization 前 lint Foundation 已 Accepted，§3 八项 reconciliation evidence 完整、分类/处置明确、current contract 仍成立；lint 不阻塞 Design Review/Freeze |
| AC-19 | focused/full frontend tests、typecheck、lint、build、drift、diff check 实际通过 |
| AC-20 | 证据绑定 exact Candidate；未验证项如实保留；独立 review 与 Human Acceptance 未绕过 |

验收通过不授权 Real AI、Gate、Live 或下一 UI 页面。

## 19. Risk Classification

Candidate 建议 **L2**，保持任务 `L1–L2` 上界，不自行降为 L1。

主要风险：

- 将读取成功、Ready、Health 或 risk admission 混为一体；
- 将 source failure 显示为空或正常；
- auth/cache ownership 回归；
- 陈旧结果伪装为当前状态；
- AI design acceptance 被误呈现为 runtime activation；
- 分页首屏被误称为完整活动事件。

Risk Tags：`AUTH`、`AUTHORIZATION`、`PUBLIC_CONTRACT`。保护边界为现有 Auth/Transport、Runtime、安全/恢复、Incident 与 AI activation authority；仅消费，不修改其语义。

**Performance / render budget：**

- 保留 backend 默认 `limit=100`；
- 每次只呈现一个 Incident page；
- 不自动拉取全部 history；
- 不按 widget 重复请求；
- 不使用逐 row timer、高频 polling 或无界缓存累积。

当前没有已接受 numeric render/latency SLA。本合同不发明阈值；记录代表性 page 的请求数、row 数与浏览器渲染观察，发现阻塞再走独立处理。

## 20. Implementation Stop Conditions

以下任一项发生时停止受影响实施：

1. Implementation Authorization 前 lint Foundation 未 Accepted 或无正式 lint gate；本条件不阻塞 Design Review/Freeze。
2. §3 evidence 缺失或 HEAD/remote/Task Base delta 未 reconciliation；main 不同本身不是 stale failure，未解决 MATERIAL/BLOCKING 阻止受影响实施。
3. governance/Frozen authority 变化，其身份/影响未完成 reconciliation，current binding 未确认有效。
4. DTO/generated types 不能支持 AC，需要 Backend/schema 扩展。
5. 需要修改 auth generation、transport、readiness 或全局 retry semantics。
6. 需要新增 endpoint、mutation、activation 或实现其它页面。
7. 缺失数据只能依赖前端猜测恢复、保护、blocking 或 AI 事实。
8. API drift 无法通过，且原因需要超出 scope 修复。
9. 实际变更跨越 approved file boundary 或覆盖既有脏改动。
10. 必需验证失败、证据失效或真实布局无法验证。

处理方式为保留证据、报告冲突并申请正式 amendment；不得静默扩大 scope 或修改 AC。

## 21. Future Review / Freeze Path

```text
本 successor Candidate v0.1.1
→ UI-I01-DESIGN-R01-RERUN-02 focused independent re-review
  （exact successor identity / NB-01～07 closure /
   no regression / no scope expansion）
→ Human Design Confirmation
→ 独立授权的 Persistence / Freeze

独立 Lint Foundation（SEPARATE TASK）
→ Accepted

两条线在 Freeze 后汇合
→ §3 Latest-main currency / delta reconciliation Gate
→ 绑定精确 Implementation Baseline、Frozen Requirement identity、
  Verification Profile 与 Required Evidence
→ 独立 Implementation Authorization
→ scoped Implementation / self-check
→ exact-candidate verification
→ Independent Implementation Review
→ Human Acceptance
→ authorized final closeout / accepted-baseline integration
```

lint Foundation 不阻塞 Design Review/Requirement Freeze；Implementation Authorization 等待其 Accepted 及 Rebind Gate 满足。两者分别验收，不改变已冻结产品顺序：

```text
UI-F01 → UI-RD01 → UI-I01 → UI-I02
→ UI-I03 → UI-I04 → UI-I05 → UI-I06
```

本轮不派发以上后续任务。

---

**Fix Summary**

| Finding | Closure |
|---|---|
| NB-01 | CLOSED IN CANDIDATE：§9/17、AC-09，冻结时区 presentation 与 timestamp authority |
| NB-02 | CLOSED IN CANDIDATE：§10/17、AC-06，DEGRADED 与 ProjectionState 分轴 |
| NB-03 | CLOSED IN CANDIDATE：§10/11/17、AC-08，endpoint 503 与 section failure |
| NB-04 | CLOSED IN CANDIDATE：§11/13/17、AC-11，cursor 422/reset path |
| NB-05 | CLOSED IN CANDIDATE：§13/17、AC-11，UI OPEN ≠ API None |
| NB-06 | CLOSED IN CANDIDATE：§5/17、AC-02，精确 Shell allowed/forbidden boundary |
| NB-07 | CLOSED IN CANDIDATE：§3/17/20/21、AC-18，八项 rebind Gate 与 delta 分类 |

AC-01～AC-20 保持原编号；未新增 AC。以上为 Designer 文本修订声明，仍待独立 re-review。

**Changes**

`Repository Changes: NONE`。无代码、配置、文档、数据库、服务、branch、commit、push 或 Candidate persistence 变更。结束时 MarketPulse Git 状态条目与开工时一致。

**Verification**

本轮完成 Parent 原始文件 identity、remote SHA 前后核实、HEAD/delta、active governance 完整加载，及七项对应 Frozen design/源码/DTO/generated-types/既有测试的只读核对；完整 successor 做章节、AC 编号与非目标内容文本自检。Implementation 测试、lint、build、浏览器/runtime：`NOT RUN / NOT VERIFIED`。文本自检不等于 independent re-review 或 Acceptance。

**Remaining / Blockers**

等待 `UI-I01-DESIGN-R01-RERUN-02` focused independent re-review，通过后才进入 Human Design Confirmation。未来 Implementation 需精确 Requirement Freeze、独立 lint Foundation Accepted、§3 Rebind Gate 和独立 Implementation Authorization。

**Evidence**

以下均指向本轮核实的 immutable baseline：

- [UI-V1 Frozen Design](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md)
- [Accepted UI Amendment](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md)
- [Product Read Formal Design](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md)
- [System DTO](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/backend/src/marketpulse/api/product/models.py) · [System endpoint](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/backend/src/marketpulse/api/product/system.py)
- [Frontend Foundation source](https://github.com/zwmhua2-lab2/MarketPulse-AI/tree/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/frontend/src) · [package.json / lint 缺口](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/8c94ea338f500e2ea4dd2f8a5ccc81a65502468e/frontend/package.json)
- [Active Workflow Manifest](https://github.com/zwmhua2-lab2/ai-dev-workflow/blob/16d260fad1d4580d90468c2b0cab6dd807d9f7a9/governance/WORKFLOW_RULE_MANIFEST.md)

```text
UI-I01-DESIGN-01-FIX-01
DESIGN CLARIFICATION COMPLETE
Candidate: UI-I01 Implementation Requirements Candidate v0.1.1
Blocking Findings: 0
NB-01..NB-07: ADDRESSED IN SUCCESSOR CANDIDATE
READY FOR FOCUSED INDEPENDENT RE-REVIEW

Human Accepted: NO
Requirement Frozen: NO
Implementation Authorized: NO
UI-I01 Implemented: NO
```