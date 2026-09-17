# UI-F01-I01-FINAL｜Frontend Foundation — Final Acceptance Closeout + Main Integration

## Task

- Task ID：`UI-F01-I01-FINAL`。
- Task Name：Frontend Foundation — Final Acceptance Closeout + Main Integration。
- Type：**DOCS / STATE / GIT INTEGRATION ONLY**。`NO PRODUCT IMPLEMENTATION`。
- Goal：把已被 Human 明确接受的 `UI-F01-I01｜Frontend Foundation`（含 `UI-F01-I01-FIX-01`）做
  **最小状态同步**，并以 **`FAST-FORWARD ONLY`** 收编 `main`。
- 本任务**不**实现任何前端 / 后端功能、**不**重新设计、**不**重新 Review、**不**选前端库、
  **不**实现 Product Read API、**不**改 schema / migration / config / runtime、**不**激活
  `PRE-01B-I2`、**不**激活 Real AI、**不**接通 live `G2→G3`、**不**接通 Forward Outcome runtime、
  **不**改变任何 Gate 状态、**不**授权 Live。

## Authority

- `UI-F01-I01｜Frontend Foundation` = **ACCEPTED / COMPLETE**；Human Acceptance =
  **`CONFIRMED — 2026-09-17`**。
- Independent Initial Review = **`FAIL — FIX REQUIRED`**；Finding = **`UI-F01-I01-R1`**
  （generic transport error-normalization boundary 不完整；原批已预置该风险为 `R-02`）。
- FIX = **`UI-F01-I01-FIX-01｜Transport Error Boundary Closure`**；Independent Re-Review =
  **`PASS — READY FOR HUMAN ACCEPTANCE`**；`UI-F01-I01-R1` = **`CLOSED`**。
- Final Re-Review severity：P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NON-BLOCKING ONLY`。
- ⚠️ 初始 Independent Review 的 `FAIL` 结论**按原样保留**：本收尾**不**改写历史，使其看起来
  曾经通过；`0c9186d2…` 与 `ecc213568…` 两层历史均作为 immutable 证据保留。

## Preflight（实测，非文档静态值）

| 项 | 期望 | 实测 | 结论 |
|---|---|---|---|
| remote `main`（收尾前） | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` | MATCH |
| Human-Accepted candidate（branch `ui-f01-i01-fix-01-transport-error-boundary`） | `ecc21356851f7deca8fd55ea086ec1007b0675d4` | `ecc21356851f7deca8fd55ea086ec1007b0675d4` | MATCH |
| original implementation candidate（branch `ui-f01-i01-frontend-foundation`） | `0c9186d2d94450d39754eb40536148a73deb123c` | `0c9186d2d94450d39754eb40536148a73deb123c` | MATCH |
| remote `ui-f01-i01-final-acceptance-closeout` | 不存在（本批新建） | 不存在 | MATCH |
| `ecc2135^` | = `0c9186d` | `0c9186d2d94450d39754eb40536148a73deb123c` | MATCH |
| `0c9186d^` | = `2c95cc2` | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` | MATCH |
| `merge-base(main, candidate)` | = `main` | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` | MATCH |
| `git rev-list --left-right --count main...candidate` | ahead > 0 / behind = 0 | `0	2` | MATCH |
| 候选 worktree（`…-ui-f01-i01-fix-01-transport-error-boundary`）`git status --porcelain` | 空 | 空 | MATCH |
| 候选 worktree 在途 merge（`MERGE_HEAD`） | 不存在 | `rc=1`（不存在） | MATCH |

⇒ **无 baseline drift**；candidate branch 未被重写；`main` 是 candidate 的**严格祖先** ⇒
`FAST-FORWARD ONLY` 可行。未做任何 merge / rebase / reset / cherry-pick / squash / force。

### main 未被任何 worktree 检出

- 程序化枚举 `.git/worktrees/*/HEAD`（14 个）：内容恰好等于 `ref: refs/heads/main` 的 = **0**
  ⇒ 本地 `main` ref 可用 `git update-ref` 同步。**不**依赖「HEAD SHA == main SHA」的推断 ——
  本仓库实测存在 HEAD SHA 恰等于 accepted main、但实际持有**自己**分支的 worktree。

## Accepted Lineage（线性、单 parent、fast-forward only）

```text
2c95cc21cc99d85c5692c5f9b276c5805cc32b13   （Accepted Main before）
  → 0c9186d2d94450d39754eb40536148a73deb123c  （UI-F01-I01；original implementation candidate）
  → ecc21356851f7deca8fd55ea086ec1007b0675d4  （UI-F01-I01-FIX-01；Human-Accepted candidate）
  → <本次 docs/state-only closeout commit>      （本收尾）
```

- 每个 commit **单 parent**（无 merge commit）。
- reviewed candidate branch `ui-f01-i01-fix-01-transport-error-boundary` 与 original candidate
  branch `ui-f01-i01-frontend-foundation` 均保持 **immutable**、远端 tip 未被移动；本收尾的
  docs-only commit **不**追加到 Fix branch。

## Final Regression（收尾前在候选 lineage 上重新执行）

| # | 命令 | exit | 结果 |
|---|---|---|---|
| 1 | `npm run typecheck`（`tsc -b`） | `0` | PASS（无输出即通过） |
| 2 | `npm run test:run`（`vitest run`） | `0` | **Test Files 7 passed (7) / Tests 44 passed (44)** |
| 3 | `npm run build`（`tsc -b && vite build`） | `0` | `✓ 150 modules transformed` / `dist/` 产物正常 |
| 4 | `npm run check:api-drift` | `0` | `no OpenAPI drift: /api/v1/live, /api/v1/ready present; generated.ts matches the backend contract` |

- 期望基线 = `7 files / 44 tests` ⇒ **实测一致**（既有 37 **未**削弱 + 新增 7）。
- `npm ci` **未**执行：`package.json` / `package-lock.json` 与本批 candidate 逐字节一致，本批为
  docs/state-only ⇒ **不**引入不必要的环境动作。`frontend/node_modules` 由 candidate worktree
  同盘整体 rename 迁移复用（该目录被 `.gitignore` 忽略、**非** repository truth）。
- 本批**不**涉及 Python 实现面 ⇒ `pytest` / `ruff` = `NOT REQUIRED / NOT RUN`。
- 门结果**绑定候选 lineage**；closeout commit 为 docs/state-only（见下节 changed paths），
  不改变任何 `frontend/**` blob ⇒ 门结果对本收尾后的 `main` 同样成立。

## Changed Paths（恰 4 个，docs/state-only）

1. `PROJECT_STATE.md`
2. `AI_CONTEXT.md`
3. `DECISIONS.md`
4. `dev_log/2026-09-17-ui-f01-i01-final-acceptance-closeout.md`（本文件，新增）

| 文件 | 落点 |
|---|---|
| `PROJECT_STATE.md` | ① `## Current Group` 新增 `UI-F01 — Frontend Foundation — ACCEPTED / COMPLETE` 组条目；② `UI-F01-I01` 条目标题改 `ACCEPTED / COMPLETE` 并补验收 / 复审 / FIX / candidate / closeout / FF 元数据；③ `UI-F01-I01-FIX-01` 条目标题改 `ACCEPTED / CLOSED` 并补元数据；④ 两条目内「本批为 Worker 交付…不等于 ACCEPTED」句加时间限定；⑤ `UI-V1-D01` 条目中已失效的 `UI implementation = NOT STARTED` / 「`vite.config.ts` 尚无 `/api` proxy」加时间限定；⑥ `## In Progress` 新增 `UI-F01-I01` bullet；⑦ 两处 Result 章节的 Result 行加「（…完成时）」限定并指向收尾结果；⑧ 文末新增 `## UI-F01-I01 Final Acceptance Closeout Result` |
| `AI_CONTEXT.md` | ① §1 新增 `UI-F01-I01` / `UI-F01` ACCEPTED bullet，并把 `UI-V1-D01` bullet 的 `UI implementation（仍 NOT STARTED）` 加时间限定；② §6 `UI-F01-I01` 节标题与状态改最终状态 + 补 closeout 元数据；③ §6 `UI-F01-I01-FIX-01` bullet 状态改 `ACCEPTED / CLOSED`；④ §6 `UI-V1-D01` 节中已失效的 `Implementation = NOT STARTED` / `前端库选型 = DEFERRED 至 UI-F01` 加时间限定；⑤ §6 next-task 行显式写 `UI-RD01 = NOT STARTED / NOT AUTOMATICALLY AUTHORIZED`；⑥ 详见指针补齐 |
| `DECISIONS.md` | 既有 `UI-F01-I01 V1` 条目仅改**状态 / provenance**（`ACCEPTED / COMPLETE` + FIX / Re-Review 结果 + candidate + closeout + FF）并补 dev_log 指针；`UI-V1-D01` 条目的 `UI 实现 …= NOT STARTED` 边界句加时间限定。**未**新增第二条 UI-F01 spec |

**未**修改的允许面内文件：`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
（frozen design；其「前端库选型 = `DEFERRED` 至 `UI-F01`」与「冻结时点现状核对」均为**设计时点**
的忠实记录，不因 Foundation 落地而变假）。**未**修改任何 `dev_log/*.md` 历史条目（历史证据，
不在本收尾写入面）。

## Verification

| # | 检查 | 结果 |
|---|---|---|
| 1 | Preflight 全部 MATCH（remote `main` / 两个 candidate / `merge-base` / left-right count / FF 可行性） | `PASS` |
| 2 | Final Regression 四门全部 exit 0；测试基线 = `7 files / 44 tests` | `PASS` |
| 3 | closeout commit changed paths **仅** 4 个 docs/state 文件（无 `frontend/**` / `backend/**` / `scripts/**` / migration / config） | `PASS` |
| 4 | `git diff --check` rc = 0（无 trailing whitespace / conflict marker） | `PASS` |
| 5 | closeout commit `parent` = Human-Accepted candidate `ecc213568…`；无 merge commit | `PASS` |
| 6 | 收尾后 `main` lineage 中每个 commit **单 parent**（纯 fast-forward） | `PASS` |
| 7 | 两个候选分支远端 tip 未变（`0c9186d2…` / `ecc213568…`） | `PASS` |
| 8 | 三份状态文档与本 dev_log 保持**纯 CRLF**（bare LF = 0） | `PASS` |
| 9 | 状态断言自检（正 / 负 / 时间限定三组，含跨行否定感知） | `PASS` |
| 10 | 相对 Accepted Main before 的全部 `frontend` / `backend` / `scripts` 文件 blob **零差异** | `PASS` |

## Accepted Capability（UI-F01-I01 / Frontend Foundation）

- React Router **Declarative** foundation；**恰好五页**已认证产品路由；`/login` = Auth Shell，
  位于五页产品 IA **之外**（**非**第六页）。
- TanStack Query server-state / cache 边界；`openapi-fetch`；既有 `openapi-typescript`。
- 通用 Foundation transport 归一化（单一所有权）；Auth Session Boundary；bearer 仅存
  `sessionStorage`；**密码永不持久化**；受保护 `401` session invalidation；Login `401` =
  凭据错误且无重定向循环。
- `/ready` `503` = 权威 `NOT_READY`（body 保留、**不**重试、**不**成为传输错误）。
- Vite `/api` 开发 proxy；可复现 OpenAPI 生成；可执行 OpenAPI drift 门；Vitest + RTL + MSW
  harness。
- **无** Redux / Redux Toolkit / Zustand / MobX / XState；通用跨页 client store =
  `NOT REQUIRED FOR UI-F01`。

### Generic Transport Accepted Boundary

```text
network failure                    -> NetworkError
401                                -> UnauthorizedError
other non-2xx                      -> HttpError（status / body 保留）
uninterpretable expected response  -> UnexpectedResponse
valid 2xx                          -> typed data
```

显式例外：`GET /api/v1/ready` 的 `503` + 合法 readiness payload ⇒ 权威 `NOT_READY`、body 保留、
**不**是 `HttpError`、**不**是 `NetworkError`、**不**重试。该边界由 `frontend/src/api/transport.ts`
**单点拥有**（`requestData()`）。

### Global Client-State Boundary

```text
Server state                      = TanStack Query
Shareable route / filter state    = URL / React Router
Authentication                    = Auth Session Boundary
Local transient UI                = React state
General cross-page client store   = NOT REQUIRED FOR UI-F01
```

## Non-Claims（本收尾明确保留）

```text
五页正式业务页面                     = NOT STARTED（仍为 FoundationPlaceholder）
Product Read API                    = NOT STARTED
MarketScannerRead / OpportunityTraceRead / EdgeAggregateRead /
  TradingAuditRead / SystemIncidentRead = NOT STARTED
UI-RD01 / UI-I01..UI-I06            = NOT STARTED / NOT AUTOMATICALLY AUTHORIZED
PRE-01B-I2                          = NOT STARTED / NOT ACTIVATED
Real AI                             = NOT ACTIVATED
live G2->G3                         = NOT ACTIVE
Forward Outcome runtime integration = NOT INTEGRATED
Gate C                              = NOT PASSED
Live                                = NOT AUTHORIZED
Trading Edge                        = NOT PROVEN
```

- `UI-F01 ACCEPTED / COMPLETE` **不**等于任何正式业务页面已实现，也**不**等于 Product Read API
  已实现；`UI-RD01` / `UI-I01..UI-I06` 状态**不**变。
- ⚠️ **`UI-F01 ACCEPTED / COMPLETE` != `UI-RD01 MAY START`**：上游收尾**不**自动解锁下游批次，
  必须另开独立获批窗口。
- 本收尾**不**改变上述任何状态。

## Remaining Non-Blocking Findings（保留，**未** resolved）

| ID | 内容 | 状态 |
|---|---|---|
| `F-01` | 现有 backend system / read endpoint 在若干位置返回 `dict[str, object]` ⇒ 生成的 OpenAPI body typing 偏弱（`{[key: string]: unknown}`）；正式 Product Read DTO 属 `UI-RD01` / 相关 read-contract 工作 | `OPEN / NON-BLOCKING`（本收尾**未**处理） |
| `F-02` | `vite.config.ts` / `vitest.config.ts` 当前**不**在 frontend tsconfig `include` 边界内 | `OPEN / NON-BLOCKING` |
| `F-03` | OpenAPI 生成当前依赖仓库兼容的 Python 运行时调用（Windows = `py -3.14`） | `OPEN / NON-BLOCKING` |
| `R-03`（等价项） | 真实浏览器 + 真实运行中 backend 的端到端 proxy 集成**不**属 UI-F01 验收证据 | `NOT IN SCOPE`（**非** blocker） |
| `UI-F01-I01-FIX-01 F-01` | `frontend/src/auth/AuthSessionProvider.tsx` 的 `signIn()` 仍自行 `try/catch` + 检查 `response.ok` / `status === 401`（FIX-01 Scope 只允许 `frontend/src/api/**`，**未**改 auth 边界） | `OPEN / NON-BLOCKING`（若后续复审认为属 `UI-F01-I01-R1` 范围，须另开含 `frontend/src/auth/**` 的 Fix 窗口） |

- 上述各项**均**为 `NON-BLOCKING`；本收尾**不**把任何一项升级为 blocker、也**不**声称已解决。
- 仅登记（**非** finding）：`frontend/src/api/transport.ts` 的单点归一化边界已在 `PROJECT_STATE.md`
  与本批 dev_log 记录，但**未**另立 `DECISIONS.md` 条目（本轮 `DECISIONS.md` 仅做状态 / provenance
  最小同步，**未**新建第二条 UI-F01 spec）。

## Integration

- Integration method = **`FAST-FORWARD ONLY`**（**无** merge commit / **无** squash / **无** rebase /
  **无** cherry-pick / **无** force push）。
- closeout branch = `ui-f01-i01-final-acceptance-closeout`（base = Human-Accepted reviewed candidate
  `ecc21356851f7deca8fd55ea086ec1007b0675d4`）。该分支**独立于** Fix branch ⇒ reviewed Fix branch
  仍停在 `ecc213568…`，作为「未被改写」的证据。
- 推送顺序：closeout commit → 复读远端 closeout branch tip → **再次**复读 remote `main`
  （必须仍 = `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`）→ 才 push `main`。
- **final main SHA after integration** = 本次 docs/state-only closeout commit 的 SHA。
  ⚠️ 本文件**不**写入自引用 SHA（仓库既有惯例；写死自身 SHA 物理上不可能，且会诱导 commit 后
  再补 commit、破坏「one closeout commit」）。**权威获取方式**：`git rev-parse refs/heads/main` /
  `git ls-remote origin refs/heads/main`。

## Next Entry

- 下一正式设计任务 = **`UI-RD01｜Product Read API Formal Design`**。
- `UI-RD01` = **`NOT STARTED` / `NOT AUTOMATICALLY AUTHORIZED`**：本收尾**不**启动它、**不**授权它。
- 其后序列（仅排序，不授权）：`UI-I01` → `UI-I02` → `UI-I03` → `UI-I04` → `UI-I05` → `UI-I06`。

## Evidence Pointers

- Human-Accepted reviewed candidate：`ecc21356851f7deca8fd55ea086ec1007b0675d4`
  （branch `ui-f01-i01-fix-01-transport-error-boundary`）。
- Original implementation candidate：`0c9186d2d94450d39754eb40536148a73deb123c`
  （branch `ui-f01-i01-frontend-foundation`）。
- Accepted Main before：`2c95cc21cc99d85c5692c5f9b276c5805cc32b13`。
- closeout branch：`ui-f01-i01-final-acceptance-closeout`。
- 前置 dev_log：`dev_log/2026-09-17-ui-f01-i01-frontend-foundation.md` /
  `dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md`。
- Final Regression 原始输出（仓库外证据目录）：四个门的 stdout / stderr 与 `gates.json`。
