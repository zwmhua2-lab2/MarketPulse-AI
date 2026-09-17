# UI-RD01 Formal Proposal — Revision 02

文档状态：`ACCEPTED / FROZEN`
执行模式：`FORMAL DESIGN / READ_ONLY`
本轮范围：仅关闭 `UI-RD01-R5` 至 `UI-RD01-R8`。
`R1–R4 = CLOSED`，其已接受结论保持不变。

## Acceptance Record

Human Design Acceptance：

CONFIRMED — 2026-09-17

Final Design Re-Review：

PASS

## 1. Repository Reality

本轮已重新执行只读核对：

- Global Protocol：
  - Version：`1.1.0`
  - Status：`ACCEPTED`
- 实时 remote：
  - `origin/main = de0f8d83c4a917f3fa801e1ef5c703cd9d9a5a84`
  - 与导航 SHA 一致，无 baseline drift。
- 当前工作区仍包含既有 modified/deleted/untracked 内容；本轮未修改、清理、暂存、切换或覆盖任何文件。
- Frozen UI Contract 确认：
  - Axis A：`A | B | C`
  - Axis B：`ACTIVE | ACCEPTED_NOT_INTEGRATED | NOT_ACTIVATED`
  - 两轴相互独立。
  - 五个 NONE 概念不得合并。
  - Market/Opportunity range 默认 `1h`。
  - Operational Market & Opportunity 使用 `FORWARD_PAPER`。
- 实际现有路由确认：
  - `/api/v1/market/instruments`
  - `/api/v1/universe`

## 2. Existing Read Surface Inventory

| SurfaceAuthorization当前边界     |               |                            |
| ---------------------------- | ------------- | -------------------------- |
| `/api/v1/live`               | Public        | Process liveness           |
| `/api/v1/ready`              | Public        | Runtime readiness          |
| `/api/v1/health`             | Public        | Runtime health             |
| Login/session                | Public entry  | Typed session boundary     |
| `/api/v1/runtime`            | Authenticated | Runtime telemetry，当前为弱字典响应 |
| `/api/v1/market/instruments` | Authenticated | Instrument metadata        |
| `/api/v1/universe`           | Authenticated | Universe read              |
| `/api/v1/protected/ping`     | Authenticated | Session verification       |

更正：

- Revision 01 中的 `/api/v1/market/universe` 不符合 repository truth。
- 正确现有路径是 `/api/v1/universe`。
- 本项仅为文档纠正，不修改现有 API。

Frontend Foundation 已接受：

- `openapi-fetch`
- `requestData()`
- `npm run generate:api`
- `npm run check:api-drift`
- OpenAPI 派生 `generated.ts`

## 3. Missing Product Read Surface Gap Analysis

当前仍缺少：

1. 五个正式 Product Read API。
2. Nullable `ProductReadContext`。
3. 正式 typed projection metadata/state DTO。
4. Scanner durable history Product projection。
5. Opportunity 双分支 trace projection。
6. SE-02D aggregate Product adapter。
7. Trading typed economic audit projection。
8. System/Incident/recovery typed projection。
9. Product collection keyset pagination。
10. Product API 对应 OpenAPI/generated.ts contract。

现有 backend truth 不等于已有正式 HTTP Read Contract；应继续使用 Frozen `ReadSurfaceClass` 表达该差异。

## 4. Read Projection Architecture

```
Authenticated Product Request
  → Product API Router
  → Nullable ProductReadContext
  → Projection Read Service
      ├─ Host-owned PostgreSQL sessions
      ├─ RuntimeHost telemetry snapshot
      ├─ current market snapshot/accessor
      ├─ recovery snapshot
      └─ accepted projection/aggregation functions
  → Explicit Pydantic Response DTO
  → OpenAPI
  → generated.ts
  → Accepted Frontend transport boundary
```

约束：

- Read Projection 不是 business authority。
- 不改变状态机、Risk、Order、Position、Ledger、Recovery 或 Reconciliation。
- 不按 Widget 建 endpoint。
- 不创建第二套 DB、provider 或 runtime authority。
- 不把 ORM record、raw payload 或内部 dataclass 直接作为 HTTP contract。

## 5. Frozen Capability Model

### 5.1 Axis A — Read Surface

正式名称：

```
ReadSurfaceClass =
  A | B | C
```

定义严格保持 Frozen Contract：

```
A = Current formal HTTP Read Contract exists
B = Accepted backend truth exists but Product Read API is needed
C = No current consumable formal Read Truth
```

不得使用 `INTEGRATED / NOT_INTEGRATED` 替换或重新解释 Axis A。

### 5.2 Axis B — Operational Availability

正式名称：

```
OperationalAvailability =
  ACTIVE
  | ACCEPTED_NOT_INTEGRATED
  | NOT_ACTIVATED
```

不得增加 `FAILED`。

DB/source/snapshot 读取失败不属于 Axis B；它们由：

```
ProjectionState = UNAVAILABLE
ReadFailureReason =
  SOURCE_UNAVAILABLE
  | SNAPSHOT_FAILED
```

表达。

### 5.3 两轴独立

合法组合包括但不限于：

```
A + ACTIVE
A + NOT_ACTIVATED
B + ACTIVE
B + ACCEPTED_NOT_INTEGRATED
C + NOT_ACTIVATED
C + ACTIVE
```

不得由 Axis A 推断 Axis B，也不得反向推断。

当前关键分类保持 Frozen：

| CapabilityReadSurfaceClassOperationalAvailability |     |                           |
| ------------------------------------------------- | --- | ------------------------- |
| Runtime Live/Ready/Health                         | `A` | `ACTIVE`                  |
| Runtime Telemetry                                 | `A` | `ACTIVE`                  |
| Market freshness                                  | `A` | `ACTIVE`                  |
| Scanner Event                                     | `B` | `ACTIVE`                  |
| Strategy Candidate                                | `B` | `ACTIVE`                  |
| Formal live Opportunity Evidence                  | `B` | `ACCEPTED_NOT_INTEGRATED` |
| Forward Outcome automatic production              | `B` | `ACCEPTED_NOT_INTEGRATED` |
| SE-02D Aggregate Product consumption              | `B` | `ACCEPTED_NOT_INTEGRATED` |
| Trading durable facts                             | `B` | `ACTIVE`                  |
| Incident durable facts                            | `B` | `ACTIVE`                  |
| Real AI                                           | `C` | `NOT_ACTIVATED`           |
| live G2→G3 Advisory                               | `C` | `NOT_ACTIVATED`           |
| Live Trading                                      | `C` | `NOT_ACTIVATED`           |

Product API 实施后，相应正式 endpoint 的 Read Surface 才可由 `B` 变为 `A`；本 Proposal 本身不会改变该事实。

## 6. ProductReadContext Contract

概念结构：

```
ProductReadContext
├─ host: RuntimeHost | None
├─ sessions: Host-owned async session factory | None
├─ runtime_snapshot accessor | None
├─ market_snapshot accessor | None
└─ recovery_snapshot accessor | None
```

生命周期与所有权：

- Nullable、read-only、non-owning facade。
- 只借用 active RuntimeHost 已拥有的资源。
- 不创建、关闭或 dispose `DatabaseResources`。
- 不允许调用 `create_database_resources()` 补建数据库资源。
- 不允许创建 provider 补数据。
- 不允许创建第二个 engine、session factory owner、RuntimeHost 或 authority。

Host Active：

- 可借用 Host-owned session factory。
- 可读取 runtime、market 与 recovery snapshot。

Host Disabled/Absent：

```
ReadSurfaceClass = A
OperationalAvailability = NOT_ACTIVATED
ProjectionState = UNAVAILABLE
ReadFailureReason = null
HTTP = 200
```

这里同时出现 `NOT_ACTIVATED` 与 `UNAVAILABLE`，但它们属于不同维度：

- `NOT_ACTIVATED`：运行能力未启用。
- `UNAVAILABLE`：本次 projection 没有可返回的 authoritative data。

不得改写为 `CAPABILITY_NOT_INTEGRATED`，也不得伪造 `SOURCE_UNAVAILABLE`。

## 7. MarketScannerRead Contract

Projection 内容：

- current Market Summary/Quote
- durable Scanner Event history
- query-level Operational Context
- keyset pagination metadata

`ScannerEventDTO` 只允许：

```
event_id
instrument_id
symbol
market_type
event_type
event_time
received_time
strength
priority
state_version
config_version
producer_source
runtime_binding_status = NOT_RECORDED
```

规则：

- `producer_source` 来自 durable `MarketEventRecord.source`。
- Scanner row 不返回 `run_mode`。
- Scanner row 不返回 `runtime_instance_id`。
- Scanner row 不返回通用 `data_quality`。
- 当前 market quality 只存在于 Current Quote/Market Summary DTO。
- query runtime 不等于 historical row runtime binding。
- 不为补字段授权 schema/migration。

Operational MarketScanner：

- 只使用当前 operational runtime/database context。
- 其产品语义为 `FORWARD_PAPER` operational context。
- 不得在数据不足时静默读取 `HISTORICAL_REPLAY` 作为替代。
- durable row 自身仍只声明可证明的 `producer_source` 与 `NOT_RECORDED` runtime binding。

## 8. OpportunityTraceRead Contract

Canonical trace：

```
Market Event
  → Strategy Candidate
  → Opportunity + canonical Evidence head
       ├─ Forward Outcome branch
       └─ Trading Decision branch
```

规则：

- 两个分支平行。
- Forward Outcome 不是 AI/Decision 前置。
- canonical Evidence/Outcome revision 由 backend 选择。
- frontend 不自行选择 revision。
- 不允许按时间相近、instrument 相同或 payload 相似发明关联。
- 无 durable relation 时返回明确 `TraceNodeState`。

Operational Opportunity：

```
source_type = FORWARD_PAPER
```

如果 `FORWARD_PAPER` 不可用：

- 不回退至 `HISTORICAL_REPLAY`。
- 按实际能力或读取状态返回 not integrated/unavailable。
- 不伪装为 `EMPTY`。

Historical Replay：

- 只有显式请求 research/historical provenance 时才可返回。
- 必须清晰标记：
  - `source_type = HISTORICAL_REPLAY`
  - `source_identity`
- 不得作为 current operational truth 呈现。

## 9. EdgeAggregateRead Contract

Exact Population Key：

```
family_id
family_version
instrument_id
market_type
source_type
source_identity
evidence_contract_version
```

Aggregate Identity：

```
(Population Key, horizon)
```

响应必须包含：

- `available_populations`
- `selected_population_key`
- `horizon`
- `status`
- expectancy
- uncertainty
- `evidence_sufficient`
- `sufficiency_reasons`
- coverage
- `worst_observation`
- `worst_decile_mean`
- measurement signature facts
- `source_type`
- `source_identity`
- `as_of`
- calculability/limitations/integrity facts

Horizon：

- Primary：`5m`
- Secondary：`30s`、`15m`、`1h`
- 每个 horizon 单独报告。
- 禁止跨 horizon 合并或平均。

Provenance：

- `source_type` 和 `source_identity` 永远显式。
- `FORWARD_PAPER` 可作为默认 research source。
- `HISTORICAL_REPLAY` 只有显式选择时才能使用。
- 不得在 Forward 数据不存在时静默回退至 Replay。

禁止增加：

- Edge Score
- A/B/C grade
- Win Rate
- Sharpe/Sortino
- Profit Factor
- Drawdown/Equity Curve
- R-Multiple
- KEEP/DOWNWEIGHT/KILL

Accepted aggregate 内部的 `NOT_CALCULABLE`、`INTEGRITY_CONFLICT` 等是业务证据状态，不是 transport failure。

## 10. TradingAuditRead Contract

严格区分：

```
Risk Accepted
!= Execution Intent
!= Paper Order
!= Fill
!= Position
```

规则：

- Fill 才证明 Paper Economic Action。
- Order 或 Intent 不证明成交。
- Position protection authority 只能来自 OPEN Position durable protection snapshot。
- 不从过期 Trade Plan 重建当前 Position protection。
- 不发明 per-trade lifetime total PnL。

Account：

```
cash_balance
reserved_cash
available_cash = cash_balance - reserved_cash
realized_pnl
updated_at
```

Trace completeness：

```
traceability_status =
  COMPLETE
  | PARTIAL
  | NOT_PROVABLE
```

V1 只保证：

- global typed economic audit
- explicit traceability status
- typed missing links

不保证任意 historical Trade 可完整逆向重建所有 Orders/Fills/Ledger lineage。

## 11. SystemIncidentRead Contract

保持：

```
Live != Ready != Health
```

Sections：

- process live
- runtime ready
- health
- RuntimeHost telemetry
- market/provider state
- pipeline/lane state
- database/singleton state
- recovery
- reconciliation
- operator/system state
- incidents
- AI integration/activation state

Recovery：

- backend 提供 sanitized immutable process-lifetime Recovery Snapshot。
- 使用不可变 snapshot 的原子发布/替换。
- terminal snapshot 在当前进程生命周期内保持稳定。
- 至少返回：
  - `status`
  - `ready_at`
  - `reason`
  - 必需的脱敏 recovery facts
- frontend 不根据 timestamp 自行推断 recovery completion。

System consistency：

- section-level snapshot consistency。
- 每个 section 有自己的 `snapshot_at` 与 source context。
- 不宣称 runtime memory 与 PostgreSQL 属于一个 global ACID snapshot。

Reconciliation：

- detector only
- 不提供 mutation/repair control

## 12. Endpoint Proposal

| MethodEndpointProjection |                                                  |                        |
| ------------------------ | ------------------------------------------------ | ---------------------- |
| `GET`                    | `/api/v1/product/system`                         | `SystemIncidentRead`   |
| `GET`                    | `/api/v1/product/market-scanner`                 | `MarketScannerRead`    |
| `GET`                    | `/api/v1/product/opportunities`                  | Opportunity collection |
| `GET`                    | `/api/v1/product/opportunities/{opportunity_id}` | `OpportunityTraceRead` |
| `GET`                    | `/api/v1/product/trading-audit`                  | `TradingAuditRead`     |
| `GET`                    | `/api/v1/product/edge-aggregates`                | `EdgeAggregateRead`    |

现有 `/live`、`/ready`、`/health`、`/api/v1/universe` 均保持不变。

## 13. Query Parameter Contract

### 13.1 Market/Opportunity range

冻结范围：

```
15m
30m
1h
4h
6h
24h
7d
30d
custom
```

正式参数：

```
range = 15m | 30m | 1h | 4h | 6h | 24h | 7d | 30d | custom
default = 1h
```

Preset range：

- server 在请求开始时冻结一次 `effective_end`。
- `effective_start = effective_end - range duration`。
- response 必须返回 `effective_start`、`effective_end`。
- 后续 cursor 页面继承相同 effective range，不允许随当前时间滑动。

Custom range：

```
range=custom
start=<UTC-aware datetime>
end=<UTC-aware datetime>
```

要求：

- `start`、`end` 必须同时提供。
- `start < end`。
- 非 `custom` 时不得同时提交 `start/end`。

Authority：

- Opportunity：`detected_at ∈ [effective_start,effective_end)`
- Scanner：`event_time ∈ [effective_start,effective_end)`
- Forward Outcome：从 `evidence_at` 起算，不受 Opportunity record-range 截断。

禁止将未提供 custom 时间解释为不确定的“latest finite page”；必须解析为默认 `1h`。

### 13.2 Pagination

```
limit = 100
valid range = 1..500
cursor = opaque/versioned
```

Cursor 绑定：

- endpoint
- effective time range
- filters
- provenance
- sort tuple
- cursor version

### 13.3 Provenance parameters

Opportunity：

```
source_type = FORWARD_PAPER | HISTORICAL_REPLAY
default = FORWARD_PAPER
```

Edge：

```
source_type = FORWARD_PAPER | HISTORICAL_REPLAY
default = FORWARD_PAPER
source_identity = explicit selector when required
```

Scanner operational endpoint：

- 使用 operational `FORWARD_PAPER` context。
- 不进行隐式 Replay fallback。

### 13.4 Edge parameters

```
horizon = 5m | 30s | 15m | 1h
default = 5m

selected_population_key = server-issued opaque selector | omitted
```

### 13.5 Trading/System history

Trading timeline与 Incident history 可使用独立 `start/end` 或 keyset latest-page contract；不得改变 Market/Opportunity 已冻结的 range semantics。

## 14. DTO / Nested DTO Contract

共享 DTO：

```
OperationalContextDTO
  run_mode
  runtime_instance_id | null
  host_state
  operational_provenance
  context_snapshot_at

ProjectionMetaDTO
  projection
  contract_version
  read_surface_class
  operational_availability
  projection_state
  read_failure_reason | null
  snapshot_at
  observed_at | null
  is_partial
  next_cursor | null

RangeContextDTO
  requested_range
  effective_start
  effective_end
  time_authority_field

FreshnessDTO
  observed_at
  evaluated_at
  age_seconds
  stale_after_seconds
  freshness_basis

SourceContextDTO
  source_type
  source_identity
  snapshot_at

TraceNodeDTO[T]
  state
  data | null
  evidence_basis | null
```

每个正式 response 必须是明确的 concrete Pydantic DTO，不得退化为 `dict[str, object]`。

主要 response：

- `MarketScannerReadResponse`
- `OpportunityCollectionReadResponse`
- `OpportunityTraceReadResponse`
- `EdgeAggregateReadResponse`
- `TradingAuditReadResponse`
- `SystemIncidentReadResponse`

不得暴露 raw prompt、provider secret、session token、connection detail、内部异常或未经筛选的 arbitrary payload。

## 15. Operational Context / Provenance Contract

Operational Context 描述当前查询环境，不证明 historical row binding。

Scanner：

```
producer_source = durable MarketEventRecord.source
runtime_binding_status = NOT_RECORDED
```

禁止推导：

```
current run_mode
  ⇒ historical row run_mode

current runtime_instance_id
  ⇒ historical row runtime binding

current quote quality
  ⇒ historical Scanner Event data quality
```

Operational Market/Opportunity：

```
FORWARD_PAPER
```

如果 Forward 数据不可用：

- 返回真实 capability/availability/projection state。
- 不查询 Replay 补位。
- 不把 Replay 标成 live/operational。

Historical research：

- 必须由显式请求触发。
- 必须展示 `HISTORICAL_REPLAY` 和 `source_identity`。
- Edge 始终展示完整 source identity。

## 16. Projection State / NONE Semantics

### 16.1 Frontend lifecycle

```
LOADING
```

只属于 frontend request lifecycle。Backend 不返回 `LOADING` 作为业务事实。

### 16.2 Backend ProjectionState

```
ProjectionState =
  FRESH
  | STALE
  | EMPTY
  | UNAVAILABLE
  | CAPABILITY_NOT_INTEGRATED
```

### 16.3 Nested causal/presence state

```
TraceNodeState =
  PRESENT
  | NOT_OCCURRED
  | NOT_REACHED
  | NO_PROVABLE_RECORD
  | CAPABILITY_NOT_INTEGRATED
```

约束：

- `NOT_OCCURRED`、`NOT_REACHED`、`NO_PROVABLE_RECORD` 不属于 ProjectionState。
- 它们不得映射为 `ProjectionState=UNAVAILABLE`。
- 它们只描述 authoritative trace 内某个业务节点的发生/到达/证明状态。
- 父 projection 可为 `FRESH`，同时一个或多个 nested node 为非 `PRESENT`。

示例：

```
ProjectionState = FRESH
ForwardOutcomeNode.state = NOT_REACHED
```

含义：查询成功且 trace 是当前可信的，但 horizon 尚未到达。

### 16.4 五个 Frozen NONE 概念

| Frozen concept正式表达含义 |                                         |                                         |
| -------------------- | --------------------------------------- | --------------------------------------- |
| 未激活                  | `OperationalAvailability=NOT_ACTIVATED` | capability 未启用                          |
| 未发生                  | `TraceNodeState=NOT_OCCURRED`           | backend 证明业务步骤未发生                       |
| 未到达                  | `TraceNodeState=NOT_REACHED`            | upstream chain 在该步骤前结束或时间条件未到           |
| 暂无可证明记录              | `TraceNodeState=NO_PROVABLE_RECORD`     | durable evidence 无法证明发生或未发生             |
| 暂不可用                 | `ProjectionState=UNAVAILABLE`           | read/source/API 无法提供 authoritative data |

五者不得互换、折叠或通过统一 absence reason 表达。

## 17. State Validity Matrix

| Read SurfaceOperational AvailabilityProjection StateDataRead failureHTTP合法语义 |                           |                             |                           |                      |                             |                                                          |
| ---------------------------------------------------------------------------- | ------------------------- | --------------------------- | ------------------------- | -------------------- | --------------------------- | -------------------------------------------------------- |
| `A`                                                                          | `ACTIVE`                  | `FRESH`                     | Present                   | `null`               | 200                         | 当前 authoritative data                                    |
| `A`                                                                          | `ACTIVE`                  | `STALE`                     | Last-known may be present | `null`               | 200                         | backend freshness facts证明 stale                          |
| `A`                                                                          | `ACTIVE`                  | `EMPTY`                     | Typed empty/`[]`          | `null`               | 200                         | authoritative query 成功且零记录                               |
| `A`                                                                          | `NOT_ACTIVATED`           | `UNAVAILABLE`               | `null`                    | `null`               | 200                         | API 已实现，但 runtime 未激活                                    |
| `A`                                                                          | `ACTIVE`                  | `UNAVAILABLE`               | `null`                    | `SOURCE_UNAVAILABLE` | 503或partial 200             | active source read failure                               |
| `A`                                                                          | `ACTIVE`                  | `UNAVAILABLE`               | `null`                    | `SNAPSHOT_FAILED`    | 503或partial 200             | snapshot acquisition failure                             |
| `A/B`                                                                        | `ACCEPTED_NOT_INTEGRATED` | `CAPABILITY_NOT_INTEGRATED` | `null`                    | `null`               | 200                         | Accepted truth/design 尚未形成所需 product/runtime integration |
| `B`                                                                          | `ACTIVE`                  | 不产生正式 Product HTTP response | N/A                       | N/A                  | N/A                         | backend truth 存在，但正式 Product API 尚未实现                    |
| `C`                                                                          | `NOT_ACTIVATED`           | `CAPABILITY_NOT_INTEGRATED` | `null`                    | `null`               | 200，在父 projection section 内 | 无当前 consumable formal truth                              |

Nested trace matrix：

| Parent ProjectionStateTraceNodeStateNode data合法 |                                     |              |                            |
| ----------------------------------------------- | ----------------------------------- | ------------ | -------------------------- |
| `FRESH`                                         | `PRESENT`                           | Present      | 是                          |
| `FRESH`                                         | `NOT_OCCURRED`                      | `null`       | 是                          |
| `FRESH`                                         | `NOT_REACHED`                       | `null`       | 是                          |
| `FRESH`                                         | `NO_PROVABLE_RECORD`                | `null`       | 是                          |
| `FRESH`                                         | `CAPABILITY_NOT_INTEGRATED`         | `null`       | 是                          |
| `STALE`                                         | 任一可证明 node state                    | 按 node state | 是                          |
| `UNAVAILABLE`                                   | authoritative causal classification | 不得新推导        | 否；读取失败时不能假装已知 causal state |

禁止组合：

- `FRESH`/`STALE` + `ReadFailureReason`
- `EMPTY` + failure reason
- `UNAVAILABLE` + `[]` 或数值 `0` 伪装正常结果
- causal absence → `ProjectionState=UNAVAILABLE`
- `NOT_ACTIVATED` → `ReadFailureReason`
- source failure → `OperationalAvailability=FAILED`
- Host disabled → `CAPABILITY_NOT_INTEGRATED`

## 18. Error Semantics

| HTTPContract             |                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| `200`                    | Fresh、stale、empty、not activated、capability not integrated、成功查询下的 causal node state、允许的 partial section |
| `401`                    | Session 缺失或无效                                                                                          |
| `404`                    | 具体 detail identity 经 authoritative query 确认不存在                                                         |
| `422`                    | range、custom 时间、cursor、limit、selector 或 filter 非法                                                      |
| `503 SOURCE_UNAVAILABLE` | Active endpoint 的整体 source/DB/aggregation read failure                                                 |
| `503 SNAPSHOT_FAILED`    | Active endpoint 无法取得所需一致性 snapshot                                                                     |
| `500`                    | 未分类内部异常，只返回脱敏 correlation ID                                                                           |

规则：

- collection 零记录是 `200 EMPTY`。
- Host disabled 是 `200 + NOT_ACTIVATED + UNAVAILABLE`。
- causal node absence 是成功的 trace result，不是 transport error。
- 单一 System section 失败但其他 section 可用时：
  - HTTP `200`
  - `is_partial=true`
  - 失败 section 为 `UNAVAILABLE`
- 整体 projection 无法形成可信结果时才返回 `503`。

## 19. Snapshot / Consistency Boundary

MarketScanner：

- event page 使用稳定 DB statement snapshot。
- current market summary 使用独立 runtime-memory snapshot。
- 分别返回 source/snapshot metadata。

OpportunityTrace：

- canonical Evidence/Outcome revision folding与关联读取使用同一 read-only stable DB snapshot。
- transaction 结束后再构造 HTTP DTO。

TradingAudit：

- account/order/fill/position/ledger 的耦合读取使用明确的 read-only stable snapshot。
- runtime valuation如存在，单独标明 snapshot/source。

Edge：

- accepted `REPEATABLE READ READ ONLY` current snapshot。
- `statement_timestamp()` 为 `as_of` authority。
- transaction 内完成 canonical folding和immutable materialization。

System：

- section-level consistency。
- runtime memory、DB、market、incident、recovery 分别标注 snapshot。
- 不伪装 global ACID consistency。

## 20. Pagination / Time Boundary

大历史默认使用 keyset/cursor，不使用 page-number + offset。

排序：

| ProjectionSort tuple |                                                        |
| -------------------- | ------------------------------------------------------ |
| Scanner              | `(event_time DESC, event_id DESC)`                     |
| Opportunity          | `(detected_at DESC, opportunity_id DESC)`              |
| Trading timeline     | `(occurred_at DESC, entity_kind DESC, entity_id DESC)` |
| Incident             | `(opened_at DESC, incident_id DESC)`                   |
| Edge populations     | canonical population selector lexical order            |

时间规则：

- 所有 timestamps 为 UTC-aware datetime。
- API 使用 RFC 3339 UTC。
- Market/Opportunity 默认 range=`1h`。
- Opportunity：`detected_at ∈ [start,end)`。
- Scanner：`event_time ∈ [start,end)`。
- cursor 固定首个请求的 effective range，避免翻页窗口漂移。

## 21. Edge Aggregation Execution Boundary

唯一允许顺序：

```
async DB stable snapshot
  → canonical revision folding
  → materialize immutable projection
  → end DB transaction
  → bounded CPU admission
  → thread offload
  → pure aggregate_projection()
  → typed DTO adapter
```

禁止：

- 将 `AsyncSession`、connection、lazy ORM object 传入线程。
- 在线程访问 DB/provider。
- CPU phase 二次读取 snapshot。
- 无界线程或任务 admission。
- Celery/Redis/Kafka/独立 worker。
- 跨 horizon pooling。
- 重写 SE-02D mathematics。

## 22. OpenAPI / Frontend Type Boundary

每个新增 Product endpoint batch 必须同时完成：

```
Backend endpoint
+ explicit Pydantic response DTO
+ OpenAPI schema
+ generated.ts regeneration
+ npm run generate:api
+ npm run check:api-drift
+ frontend TypeScript compile/regression
```

规则：

- `generated.ts` 不手工修改。
- Frontend 不建立 duplicate authority DTO。
- 继续使用 `requestData()`。
- 每个中间 Acceptance Batch 保持 drift gate 通过。
- I05 不得首次同步前序 endpoint types。
- 正式 endpoint 不返回 `dict[str, object]`。

## 23. Authorization Boundary

- `/api/v1/product/*` 全部使用现有 authenticated session dependency。
- `/live`、`/ready`、`/health` 与 login 保持既有 public boundary。
- Host disabled 不绕过 authentication。
- Product Read 权限不赋予 mutation、activation、repair、recovery 或 trading 权限。
- 不返回 secret、provider credential、connection detail 或 raw internal exception。
- 未授权请求返回 `401`，不得通过响应差异泄露数据存在性。

## 24. Reuse Decisions

复用：

- `verify_session`
- Host-owned `DatabaseResources`
- Host-owned session factory
- RuntimeHost telemetry/current market accessors
- accepted recovery/reconciliation facts
- G2/G3/G4 durable records
- accepted Edge revision reader
- `aggregate_projection()`
- UI-F01 OpenAPI/generated/transport foundation

不直接作为正式 Product contract 复用：

- 弱 `dict[str, object]`
- raw ORM rows
- arbitrary payload
- raw AI prompt/response
- frontend handwritten duplicate DTO
- endpoint 内临时 DB/provider construction

## 25. Scope

本 Revision 只完成：

- 恢复 Frozen Axis A/B capability model
- 恢复五个 NONE 概念
- 引入独立 `TraceNodeState`
- 恢复 Market/Opportunity range/default/time authority
- 恢复 Forward/Replay provenance isolation
- 修正 `/api/v1/universe` inventory
- 输出完整 consolidated formal proposal

本轮未修改代码、配置、数据库、Git 状态或服务。

## 26. Out of Scope

不授权：

- Backend Product Read API
- Frontend 修改
- Product UI
- RuntimeHost implementation
- schema/migration/index
- provider/runtime activation
- UI-I01..UI-I06
- `PRE-01B-I2`
- Real AI activation
- live G2→G3
- Forward Outcome runtime integration
- Gate changes
- Live authorization
- mutation endpoint
- Implementation Task

## 27. Acceptance Criteria

Final Design Re-review 必须确认：

1. `ReadSurfaceClass` 严格为 `A|B|C`。
2. Axis A 定义与 Frozen UI 完全一致。
3. `OperationalAvailability` 严格为三值。
4. `FAILED` 已移除。
5. source/snapshot failure 由 `UNAVAILABLE + ReadFailureReason` 表达。
6. Axis A/B 独立。
7. `NOT_OCCURRED`、`NOT_REACHED`、`NO_PROVABLE_RECORD` 不再映射到 `UNAVAILABLE`。
8. causal/presence state 与 projection availability 分离。
9. 五个 Frozen NONE 概念全部保留。
10. Market/Opportunity range 包含九种选项。
11. 默认 range 为 `1h`。
12. Opportunity authority 为 `detected_at ∈ [start,end)`。
13. Scanner authority 为 `event_time`。
14. preset range 的 effective window 在首个请求冻结，并由 cursor 继承。
15. Operational Market/Opportunity 使用 `FORWARD_PAPER`。
16. 不允许隐式 Replay fallback。
17. Historical Replay 必须显式请求并显式标识。
18. Edge `source_type/source_identity` 始终显式。
19. `/api/v1/universe` inventory 已纠正。
20. R1–R4 的已关闭设计不被重新打开。
21. 五个 projections、Nullable Context、Edge/Trading/System/OpenAPI contracts保持不变。
22. 无 schema/migration/index 预授权。
23. 无 implementation authorization。

## 28. Risks

- 当前工作区有既有脏改动；未来实现必须使用经核对的 Accepted baseline 隔离开展。
- `ReadSurfaceClass` 与 `ProjectionState` 都涉及“是否可读”，若实现时混用会再次破坏双轴模型。
- causal absence 与 read failure 若共用一个 reason enum，会重新引入 R6。
- preset range 翻页若重新计算 `now`，会造成记录重复或遗漏。
- Scanner durable row 缺乏 runtime binding，不能因 Operational Context 为 Forward 而伪造 row provenance。
- Replay 数据若作为 fallback，可能污染 operational truth 与 Edge population。
- 多表 trace 性能尚未测量，不得提前添加 index。
- Edge CPU workload 必须有 bounded admission。
- System partial sections 不构成 global ACID snapshot。
- raw payload 仍需显式 allowlist 与脱敏。

性能决策继续保持：

```
EXPLAIN
→ duration
→ row count
→ pagination evidence
→ 独立性能评审
```

## 29. Final Human Decisions

保持既有决定：

- `OD-01 Scanner Provenance = ACCEPT WITH MODIFICATION`
- `OD-02 ProductReadContext = ACCEPT WITH MODIFICATION`
- `OD-03 Recovery = ACCEPT`
- `OD-04 Trading Trace Completeness = ACCEPT`
- `OD-05 System Consistency = ACCEPT`
- `Query Performance = ACCEPT`

FIX-02 reconciliation：

- Frozen Axis A/B 恢复，不增加替代 capability axis。
- causal trace state 与 projection availability 正式分离。
- Frozen Market/Opportunity time与 provenance contract 恢复。
- Existing API inventory 修正为 `/api/v1/universe`。

`Open Decisions = NONE`

## 30. Implementation Batch Decomposition

以下仅记录未来边界，不是 Implementation Task，不构成实施授权。

### UI-RD01-I01

- Shared Product Read contracts
- Nullable ProductReadContext
- SystemIncident vertical slice
- 本 slice OpenAPI/generated.ts integration

### UI-RD01-I02

- MarketScannerRead
- OpportunityTraceRead
- Frozen range/provenance/TraceNodeState
- 本 slice OpenAPI/generated.ts integration

### UI-RD01-I03

- TradingAuditRead
- 本 slice OpenAPI/generated.ts integration

### UI-RD01-I04

- EdgeAggregateRead
- bounded CPU offload
- explicit source identity
- 本 slice OpenAPI/generated.ts integration

### UI-RD01-I05

仅负责：

- Overall Product Read Contract Regression
- cross-projection adverse tests
- capability/state matrix regression
- OpenAPI completeness
- full backend/frontend regression
- acceptance evidence consolidation

I05 不得首次同步前序 slice 的 generated types。

## 31. 推荐 Implementation Model

未来另行获得授权后：

- 使用强代码推理模型逐 batch 串行实施。
- 不并发修改共享 OpenAPI/generated.ts boundary。
- 每个 batch 独立完成 implementation、测试、自审、修复、回归。
- 由新上下文 reviewer 独立检查 source、diff、adverse cases、DB/runtime evidence。
- reviewer 不继承实现模型的 PASS。
- I05 使用独立 integration reviewer。
- 本 Revision 不绑定具体模型 SKU，也不下发任务。

# Revision 02 Delta

## UI-RD01-R5 — CLOSED

- 恢复 `ReadSurfaceClass = A | B | C`。
- 恢复各值 Frozen 定义。
- 恢复三值 `OperationalAvailability`。
- 删除替代 Axis A 的 `INTEGRATED/NOT_INTEGRATED`。
- 删除 `OperationalAvailability=FAILED`。
- source/snapshot failure 改由 `ProjectionState=UNAVAILABLE` 与 `ReadFailureReason` 表达。
- 明确 Axis A/B 独立。

`R5 = CLOSED`

## UI-RD01-R6 — CLOSED

- `NOT_OCCURRED`、`NOT_REACHED`、`NO_PROVABLE_RECORD` 不再映射为 `UNAVAILABLE`。
- 新增独立 `TraceNodeState`。
- 明确成功且 fresh 的 projection 可以包含未发生、未到达或无可证明记录的 nested node。
- 恢复五个互不相同的 NONE 概念。
- 更新状态矩阵，禁止 causal state 与 read failure 混用。

`R6 = CLOSED`

## UI-RD01-R7 — CLOSED

- 恢复完整 range：
  - `15m / 30m / 1h / 4h / 6h / 24h / 7d / 30d / custom`
- 默认固定为 `1h`。
- Opportunity 使用 `detected_at ∈ [start,end)`。
- Scanner 使用 `event_time`。
- preset omission 不再表示不确定的 latest-page window。
- Operational Market/Opportunity 固定 `FORWARD_PAPER`。
- 禁止 Forward 不可用时隐式回退 Replay。
- Historical Replay 必须显式请求、显式标识。
- Edge 始终显式返回 `source_type/source_identity`。

`R7 = CLOSED`

## UI-RD01-R8 — CLOSED

Existing API inventory 已从：

```
/api/v1/market/universe
```

纠正为 repository truth：

```
/api/v1/universe
```

未修改现有 API。

`R8 = CLOSED`

---

`Open Decisions = NONE`

`UI-RD01-DESIGN-FIX-02`
`= ACCEPTED / CLOSED`

`UI-RD01`
`= ACCEPTED / FROZEN`

Product Read API Implementation
`= NOT STARTED`
`= NOT AUTOMATICALLY GRANTED BY DESIGN ACCEPTANCE`

未实施、未修改 repository、未生成 Implementation Task。