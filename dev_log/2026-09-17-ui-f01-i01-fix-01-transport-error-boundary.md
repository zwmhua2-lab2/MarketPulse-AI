# UI-F01-I01-FIX-01｜Transport Error Boundary Closure

## Task

- Task ID：`UI-F01-I01-FIX-01`。
- Task Type：IMPLEMENTATION + VERIFICATION（**Fix 批**；**非** New Design、**非** 新功能、**非**
  New Scope 扩张）。
- 最终 Worker 状态：**`UI-F01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`**；
  **不**等于 `ACCEPTED` / `COMPLETE` / `HUMAN ACCEPTED`。

## Finding To Close

`UI-F01-I01-R1` —— **Generic Transport Error Boundary is incomplete**。

原实现把 bearer 注入与受保护 `401` 会话失效集中在 transport middleware 中，但**通用** API 调用方
（未来 Product Query 模块）若使用裸 `client.GET(...)` / `client.POST(...)`，仍会拿到
`openapi-fetch` 的 `{ data, error, response }` 结局，必须自行复现：

- catch 网络异常；
- 检查 `response.ok`；
- 映射 `401`；
- 映射普通 `4xx`；
- 映射普通 `5xx`。

而归一化逻辑大部分由 `readReadiness()` 拥有 ⇒ 通用传输行为被 readiness 化。这与已批准目标
「HTTP / Auth / Cache / Error 基础在 Product Query 模块引入**之前**一次性解决」冲突。

原批 `UI-F01-I01` 的 **`R-02` 风险条目**已预先记录同一隐患（"本批只在 `/ready` 路径上做显式分类；
未来若直接使用 `client.GET(...)` 而不经分类，调用方必须自行处理 `response.ok`"）。本批将该风险关闭。

## Task Base / Reviewed Candidate

- Reviewed candidate（任务卡声明）= `0c9186d2d94450d39754eb40536148a73deb123c`。
- 执行前**实读远端真值**：`git ls-remote origin refs/heads/main` =
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；本地 `main` 同为该 SHA ⇒ **无** baseline drift
  （CIP-02 / CIP-03）。
- candidate 校验（实读，非转述）：`git cat-file -p 0c9186d2…` ⇒ tree
  `dc91bcdf6150cea81ed8d98e44c2955df0f2627a`，**单 parent** =
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；`git branch -a --contains 0c9186d2…` ⇒
  `ui-f01-i01-frontend-foundation`（本地 + `origin/ui-f01-i01-frontend-foundation`）。
- candidate **未被重写**（零 reset / 零 rebase / 零 amend），保留为历史证据。
- Fix branch = `ui-f01-i01-fix-01-transport-error-boundary`，为基于 candidate 的独立 clean
  worktree（`git worktree add`，起始 `git status --porcelain` 为空）。**未** merge `main`、
  **未** push `main`。

## Scope

- `frontend/src/api/**`（唯一允许改动的实现目录）。
- 直接相关的 frontend Foundation 测试。
- 本 Fix 所需的最小 `dev_log` / `PROJECT_STATE.md` / `AI_CONTEXT.md` 同步。

## Out of Scope（本批确认**未**触碰）

- `UI-RD01`；`UI-I01` 与任何业务页面；任何 Product Read API；route IA；auth 持久化选择；
  refresh token；Redux / Zustand / MobX / XState。
- `PRE-01B-I2` 激活；Real AI 激活；live `G2→G3` 接通；Forward Outcome 运行时接通；
  任何 Gate 状态变更；Live 授权。
- 后端 production code / schema / migration / trading / risk / Scanner / Strategy / Position /
  Protection = **ZERO CHANGE**。
- `frontend/src/auth/**` 与 `frontend/src/app/**`：**零改动**（见「Remaining / Findings」F-01）。

## Required Responsibility Boundary（实现后的实际形态）

```
openapi-fetch  client.GET / client.POST / client.PUT ...
      ↓
api/transport.ts  requestData(call)          ← 唯一通用入口
      ├─ 抛出 / 无法解析           → NetworkError
      ├─ HTTP 401                  → UnauthorizedError
      ├─ 其他非 2xx                 → HttpError（status + body 保留）
      ├─ 2xx + 可解释 JSON body     → typed data（生成类型的成功 body）
      └─ 2xx + 无可解释 body        → UnexpectedResponse
      ↓
Product Query（未来）

api/readiness.ts  readReadiness()            ← 唯一显式例外
      ↓ sendRequest(call) 取原始 outcome（只做网络层归一化）
      ↓ 503 拦截 → NOT_READY（body 保留 / 非 HttpError / 非 NetworkError / 不重试）
      ↓ 其余才走 transportErrorForStatus()（与通用路径同一实现）
```

**未**引入：Repository framework / Gateway framework / RequestFactory hierarchy /
BaseService hierarchy / 第二个 HTTP client / Axios。

## Files Changed

### 新增（A）

- `frontend/src/api/transport.ts` —— 通用传输解释（`TransportOutcome` / `TransportCall` /
  `transportErrorForStatus()` / `sendRequest()` / `requestData()`）。

### 修改（M）

- `frontend/src/api/readiness.ts` —— 改为「原始 outcome → `503` 拦截 → 复用通用解释」；
  不再拥有 `transportErrorForStatus()`。
- `frontend/src/api/errors.ts` —— `UnexpectedResponse` 增加可选 `{ cause }`（与 `NetworkError`
  同形，保留底层解析错误作为证据）；无行为变化。
- `frontend/src/api/transport.test.ts` —— 新增 `describe("generic transport interpretation")`，
  7 个新用例（使用**非 `/ready`** 端点 `/api/v1/protected/ping` 与 `/api/v1/runtime`）；
  既有 9 个用例**逐字保留**。

### 明确未改

- `frontend/package.json` / `frontend/package-lock.json` = **零改动**（生产依赖未因上一份
  Completion Report 的版本笔误做任何变更）。
- `frontend/tsconfig.json` / `vite.config.ts` / `vitest.config.ts` = 零改动。
- `frontend/src/api/generated.ts` = 零改动（`check:api-drift` 逐字节一致）。
- `backend/**`、仓库根 `scripts/**`、`docs/**`、`frontend/src/auth/**`、`frontend/src/app/**`、
  `frontend/src/test/**`、`frontend/src/pages/**` = 零改动。

## Implementation

### 1. 通用传输解释（新文件 `api/transport.ts`）

- `TransportOutcome<T>`：把 `openapi-fetch` 的结局约简为解释所需的三项（`data` / `error` /
  `response`），与生成 `paths` 的 `FetchResponse` 结构兼容，因此可写
  `requestData(() => client.GET(path))` 并让成功 body 类型推断进 `T`。
- `transportErrorForStatus(status, body)`：由 `readiness.ts` **迁入**本模块（实现逐字保留），
  成为通用状态映射的唯一实现。
- `sendRequest(call)`：等待一次请求；**只做网络层归一化**——`openapi-fetch` 对「响应已到达但
  声明为 JSON 的 body 无法解析」会抛出解析错误，这不是网络故障，误报会既错分类别又让它被重试，
  因此 `SyntaxError` → `UnexpectedResponse`，其余抛出 → `NetworkError`。
- `requestData(call)`：通用入口 = `sendRequest` + 通用解释；2xx 且无可解释 JSON body ⇒
  `UnexpectedResponse`（当前契约下所有端点都声明 JSON body；真正无 body 的未来端点应改用
  `sendRequest`，不静默得到 `undefined`）。

### 2. `readiness.ts` 降为唯一显式例外

- 先用 `sendRequest()` 取原始 outcome（仍获得网络故障归一化），再拦截 `503` → `NOT_READY`
  且 body 原样保留；其余状态复用 `transportErrorForStatus()`。模块文档显式声明：
  「本端点是通用传输解释的**唯一**显式例外，其它模块不得走此捷径」。
- `/ready` 语义**逐条未变**：`200` → `READY`；`503` + 可解析 JSON body → `NOT_READY`（body 保留）；
  `503` 不成为 `HttpError` / `NetworkError` / 通用后端故障，且因成功解释而**不重试**；
  `503` + 非 JSON body → `UnexpectedResponse`。

### 3. 类型推断实测（非断言、非猜测）

以临时 `src/api/typeProbe.ts`（**已删除，未进入提交**）把推断结果打印出来：

```
src/api/typeProbe.ts(9,9): error TS2322: Type '{ [x: string]: string; }' is not assignable to type 'number'.
```

⇒ `requestData(() => client.GET("/api/v1/protected/ping"))` 的成功 body 被推断为
`{ [x: string]: string }`（即生成类型的成功响应），**不是** `unknown`、**不需要** cast。
该探针同时证明 `tsc -b` 门**有牙齿**（注入类型错误 ⇒ exit 1）。

## Tests Added（7 个新用例，全部使用非 `/ready` 端点）

| # | 用例 | 端点 | 断言 |
|---|---|---|---|
| 1 | 成功返回 typed body | `/api/v1/protected/ping` | 返回值为生成的成功 body 类型（`const status: string = data["status"]` 为编译期断言） |
| 2 | network failure → `NetworkError` | `/api/v1/protected/ping` | `NetworkError`，且**不**是 `HttpError` / `UnauthorizedError` |
| 3 | `401` → `UnauthorizedError` | `/api/v1/protected/ping` | `UnauthorizedError` + `status = 401`，且 `onUnauthorized` 仍被调用 **1** 次（401 生命周期未被通用化破坏） |
| 4 | 普通 `4xx` → `HttpError` | `/api/v1/protected/ping` | `status = 404`，`body` 深等于 `{ detail: "telemetry not found" }` |
| 5 | 普通 `5xx` → `HttpError` | `/api/v1/protected/ping` | `status = 502`，非 JSON body 原样保留为字符串 |
| 6 | `503` 的权威语义**只**属于 `/ready` | `/api/v1/runtime` | 503 → `HttpError(503)` + body 保留，且**不**是 `NetworkError` / `UnauthorizedError` |
| 7 | 无法解释的 2xx body → `UnexpectedResponse` | `/api/v1/protected/ping` | `UnexpectedResponse`，且**不**是 `NetworkError` / `HttpError` / `UnauthorizedError` |

既有覆盖：`transport.test.ts` 原 9 个用例、`readiness.test.ts` 5 个、`generated.test.ts` 3 个、
`queryClient.test.ts` 6 个、`router.test.tsx` 7 个、`unauthorized.test.tsx` 3 个、
`sessionBoundary.test.tsx` 4 个 —— **全部逐字保留**，无削弱、无删除、无 skip。

## Verification

全部在 Fix worktree 内**真实执行**：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `git ls-remote origin refs/heads/main` | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` = candidate parent ⇒ 无 drift |
| 2 | `npm run typecheck`（`tsc -b`） | exit 0 |
| 2a | 注入临时类型探针 | exit 1，`typeProbe.ts(9,9): error TS2322` ⇒ 门有牙齿；探针已删除（未进入提交） |
| 3 | `npm run test:run` | **7 files / 44 tests 全部 PASS**（exit 0）= 既有 37 + 新增 7 |
| 4 | `npm run build` | exit 0；`dist/assets/index-_e9L-8pv.js` 294.91 kB / gzip 93.27 kB |
| 5 | `npm run check:api-drift` | exit 0：`no OpenAPI drift: /api/v1/live, /api/v1/ready present; generated.ts matches the backend contract` |
| 6 | 基线（改动前，同一 worktree） | `typecheck` exit 0；`test:run` = 7 files / **37 tests** PASS ⇒ Fix 造成的 delta 精确为 `+7 tests` |

**注入式「门有牙齿」探针**（脚本 `E:/Documents/mp-fix01-probe.mjs`，仓库外；每个探针运行后逐字节
复原并以 sha256 复核）：

| 探针 | 破坏点 | 结果 |
|---|---|---|
| P-1 | `requestData()` 不再对非 2xx 抛错 | exit 1 ⇒ 用例 3 / 4 / 5 / 6 失败（4 个新用例守卫通用分类） |
| P-2 | `sendRequest()` 不再区分「body 无法解析」与网络故障 | exit 1 ⇒ 用例 7 失败（`NetworkError` 而非 `UnexpectedResponse`） |
| P-3 | `/ready` 不再拦截 `503` | exit 1 ⇒ `readiness.test.ts` 4 个既有用例 + `transport.test.ts` 的 503 生命周期用例失败（`HttpError(503)` 取代 `NOT_READY`） |
| 复原复核 | — | 3 个探针后 `transport.ts` / `readiness.ts` 的 sha256 与原文件**完全一致**；复原后重跑 exit 0 |

**未执行 / 未声称**：

- **未**重跑 `npm ci`：`package.json` / `package-lock.json` 零改动，依赖树与 candidate 完全一致。
  本批的 `frontend/node_modules` 由 candidate worktree **整体同盘 rename 迁移**（14 ms）到 Fix
  worktree 以复用已验证的安装树；该目录被 `.gitignore` 忽略、**不属于** repository truth，
  candidate worktree 的源码与 `git status` 保持干净（迁移后复核为空）。
- 未做浏览器端真机联调、未连接真实 backend、未做任何后验运行时验证。

## 版本真值（按实际 lockfile / repository truth 报告）

| 包 | lockfile 实际解析 |
|---|---|
| `react` | `19.3.0` |
| `react-dom` | `19.3.0` |
| `react-router` | `8.4.0` |
| `@tanstack/react-query` | `5.103.1` |
| `openapi-fetch` | `0.17.0` |
| `msw` | `2.15.0` |
| `vitest` | `5.0.1` |
| `vite` | `8.3.0` |
| `typescript` | `5.9.3` |
| `jsdom` | `30.1.0` |
| `openapi-typescript` | `7.13.0` |

上一份 Completion Report 的 `react` / `react-dom` 版本笔误**未**通过改动任何 production
dependency 来"修正"；此处按 lockfile 实测值报告。

## FIX-AC 逐条对照

- **FIX-AC-01** PASS：通用归一化只有一条 Foundation-owned 路径 = `api/transport.ts` 的
  `requestData()`（其内部复用 `transportErrorForStatus()`）；`sendRequest()` 是同一机制的网络层
  组件，只被 `/ready` 消费，不做任何 HTTP 分类。
- **FIX-AC-02** PASS：7 个新用例全部使用非 `/ready` 端点，覆盖 network→`NetworkError`、
  `401`→`UnauthorizedError`、普通 `4xx`→`HttpError`、普通 `5xx`→`HttpError`，并逐一断言
  status / body 保留；`/ready` 自身的分类用例仍保留（未以它单独满足本 AC）。
- **FIX-AC-03** PASS：`auth/unauthorized.test.tsx` 3 个用例逐字保留并 PASS；新用例 3 另加断言
  「401 仍触发 `onUnauthorized`」⇒ 清 session → 清已认证 Query cache → Login 边界 → 保留原定
  安全路由的链路未被通用化破坏。
- **FIX-AC-04** PASS：login `401` = `invalid-credentials`、不清 session、不导航循环
  （`unauthorized.test.tsx` 用例逐字保留、PASS；`auth/**` 本批零改动）。
- **FIX-AC-05** PASS：`/ready` `503` = 权威 `NOT_READY`，body 保留、不重试；用例 6 另证明
  「`503` 不是全局语义」——非 `/ready` 端点的 503 是普通 `HttpError`。
- **FIX-AC-06** PASS：未创建任何 Product Read API 或业务查询模块；新测试只使用既有
  Foundation 端点（`/api/v1/protected/ping`、`/api/v1/runtime`）。
- **FIX-AC-07** PASS：后端 / schema / migration / trading / risk / Scanner / Strategy /
  Position / Protection = ZERO CHANGE（`git status --porcelain` 仅列出
  `frontend/src/api/**` 4 个文件）。
- **FIX-AC-08** PASS：`typecheck` / `test:run` / `build` / `check:api-drift` 四项全部 exit 0
  （见 Verification #2–#5）。
- **FIX-AC-09** PASS：既有 37 个测试全部保留并 PASS，delta 精确为 `+7`；无删除、无削弱、无 skip。

## Result

`UI-F01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`。

**不**等于 `ACCEPTED` / `COMPLETE` / `HUMAN ACCEPTED` —— 独立复审与人工验收另开窗口。

## Remaining / Findings

- **F-01（非阻塞，本批不修 —— Scope 边界）**：`auth/AuthSessionProvider.tsx` 的 `signIn()` 仍
  自己 `try/catch` 并检查 `outcome.response.status === 401` / `response.ok`。本批 Scope
  **只允许** `frontend/src/api/**`，因此**未**改动它。理由（供复审判断）：login `401` 是
  「凭据被拒绝」这一**认证判决**，不是传输错误类别；把它接到通用边界需要 `UnauthorizedError`
  → `invalid-credentials` 的映射，属 auth 边界的职责。若复审认为该处也属 `R1` 范围，应另开
  一支 Fix（Scope 需包含 `frontend/src/auth/**`）。
- **F-02（非阻塞，沿用原批 Finding，本批不修）**：`F-01/F-02/F-03`（后端弱 typed DTO、
  `vite.config.ts` / `vitest.config.ts` 不在 `tsconfig.json` `include` 内、
  `generate:api` 依赖本机 `py -3.14`）与 `R-03`（未做浏览器真机联调）**状态不变**。
- **F-03（环境 Finding，非产品缺陷）**：本机在**已存在**较大 `node_modules` 的工作树里跑
  `npm ci` 会静默冻结（原批 `R-04`），本批以「整体 rename 迁移已安装树」规避；
  正常环境无需此步骤。
- 原批 **`R-02`** 由本批关闭（通用传输分类不再由调用方各自复现）；其余风险 `R-01` / `R-03`
  **状态不变**，**不得**据此声称已解决。

## Evidence

- Fix branch：`ui-f01-i01-fix-01-transport-error-boundary`（**未** merge `main`）。
- Reviewed candidate：`0c9186d2d94450d39754eb40536148a73deb123c`（单 parent = main
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；未重写）。
- 远端 `main`（执行前实读）：`2c95cc21cc99d85c5692c5f9b276c5805cc32b13`。
- 改动文件（4）：`frontend/src/api/transport.ts`（新）、`frontend/src/api/readiness.ts`、
  `frontend/src/api/errors.ts`、`frontend/src/api/transport.test.ts`。
- 门证据：`npm run typecheck` / `npm run test:run`（7 files / 44 tests PASS）/ `npm run build` /
  `npm run check:api-drift` 全部 exit 0。
- 牙齿证据：探针脚本 `E:/Documents/mp-fix01-probe.mjs` 输出（P-1 / P-2 / P-3 均 exit 1，
  sha256 复原一致，复原后 exit 0）。

## Context For Next AI

1. 通用传输分类现由 `frontend/src/api/transport.ts` **单点拥有**：新 Product Query 一律用
   `requestData(() => client.GET(...))`，**不要**再自行 catch / 检查 `response.ok` / 分类状态码。
2. `/ready` 是**唯一**显式例外（503 权威 `NOT_READY`）。新增任何「非 2xx 但有权威业务语义」的
   端点，须走 `Proposal → Human approval`，**不得**照抄 `/ready` 的捷径。
3. `sendRequest()` 是同一机制的网络层组件，只服务 `/ready` 的 503 前置拦截；不要用它绕过通用解释。
4. 本批**未**触碰 `auth/**`（见 F-01）：login `401` 仍是 auth 边界的凭据判决。
5. 本批**未**授权或实现 `UI-RD01` / `UI-I01..UI-I06`，边界（`PRE-01B-I2` / Real AI / Gate / Live）
   状态不变。
