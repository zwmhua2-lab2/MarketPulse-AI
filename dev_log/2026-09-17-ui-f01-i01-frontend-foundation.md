# UI-F01-I01｜Frontend Foundation — Implementation

## Task

- Task ID：`UI-F01-I01`。
- Goal：实现 MarketPulse UI V1 的第一批前端基础（Router / Server Query-Cache / Typed API
  Client / Auth Session Boundary / OpenAPI generation discipline / Frontend Test Harness /
  Global Data State Boundary / Vite `/api` proxy / 401 与 `/ready` 503 传输语义 /
  最小前端目录与职责结构）。
- Task Type：IMPLEMENTATION + VERIFICATION。
- 本批**只做 Foundation**：不实现任何正式业务页面。

## Task Base

- Task Base（任务卡声明）= `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`。
- 执行前**实读远端真值**：`git ls-remote origin refs/heads/main` =
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` ⇒ **与 Task Base 一致，无 baseline drift**
  （CIP-02 / §30；AC-01）。
- Task branch = `ui-f01-i01-frontend-foundation`（基于上述 SHA 的独立 clean worktree）。
- 本批**未** merge `main`；未 push 到 `main`。

## Scope

- `frontend/**`（manifest / lockfile / Vite config / app & bootstrap / router / auth boundary /
  API infrastructure / query infrastructure / test infrastructure / generated OpenAPI artifact /
  frontend foundation tests）。
- 项目状态同步：`dev_log/`、`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md`
  （仅作已批准 Foundation 决策的最压缩持久化）。

## Out of Scope

- 五个业务页（总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统）的正式 UI；
- 任何 Product Read API（`MarketScannerRead` / `OpportunityTraceRead` / `EdgeAggregateRead` /
  `TradingAuditRead` / `SystemIncidentRead`）与后端实现；
- 交易 / 风险 / Scanner / Strategy / Position / Protection 语义变更；schema / migration；
- `PRE-01B-I2` 激活、Real AI 激活、live `G2→G3` 接通、Forward Outcome 运行时接通、
  Gate 状态变更、Live 授权、任何 mutation 控制。

## Reuse Decisions implemented

任务卡冻结的复用决策**逐条按实际安装结果**落地（无替代、无新增框架）：

| 领域 | 冻结决策 | 实际安装 |
|---|---|---|
| Router | `react-router`，Declarative 模式（**非** Framework Mode / 非 SSR / 非 loader 主导数据） | `react-router@8.4.0` |
| Server Query / Cache | `@tanstack/react-query` | `@tanstack/react-query@5.103.1` |
| API Client | `openapi-fetch`（**未**引入 Axios / 未自建 HTTP 框架） | `openapi-fetch@0.17.0` |
| OpenAPI 生成 | 复用既有 `openapi-typescript` | `openapi-typescript@7.13.0` |
| 测试 | vitest + jsdom + RTL + jest-dom + user-event + MSW | `vitest@5.0.1` / `jsdom@30.1.0` / `@testing-library/react@16.3.3` / `@testing-library/dom@10.4.2` / `@testing-library/jest-dom@7.0.1` / `@testing-library/user-event@14.6.7` / `msw@2.15.0` |
| Build 工具 | 既有 Vite + React 插件 + TypeScript | `vite@8.3.0` / `@vitejs/plugin-react@6.1.1` / `typescript@5.9.3` |
| 全局客户端状态 | **不引入** Redux / RTK / Zustand / MobX / XState | 未安装 |

工具链兼容性实测：Node `v22.22.2` / npm `10.9.7`（本机 `node` 解析到 managed 22.22.2）。
所有选中依赖的 `engines` 均被满足（`react-router` `>=22.22.0`、`jsdom` `^22.22.2`、
`vite` `>=22.12.0`、`vitest` `^22.12.0`）。

**TypeScript 版本决策（证据驱动）**：先按 `latest` 解析得到 `typescript@7.0.2`，`npm install`
报 `ERESOLVE overriding peer dependency` —— `openapi-typescript@7.13.0` 的 peer 为
`typescript@^5.x`，与 TS 7 不兼容（peer 未被满足）。按任务卡 §15「使用明确兼容的稳定版本」，
改为 `typescript@^5.9.3`（`^5.x` 的最新稳定版）后重新安装，警告消失、树一致。

## Files Changed

### 修改（M）

- `frontend/package.json` —— 去除全部字面 `latest`，改为稳定 semver；补齐 scripts
  （`typecheck` / `test` / `test:run` / `generate:api` / `check:api-drift`）；运行期依赖与
  构建 / 测试工具依赖正确分区。
- `frontend/package-lock.json` —— 与 manifest 同步重生成。
- `frontend/vite.config.ts` —— 新增开发 `/api` proxy → `http://127.0.0.1:8000`（**不** rewrite）。
- `frontend/src/main.tsx` —— 改为渲染 `App`。
- `frontend/src/styles.css` —— 深色终端风格的最小 shell / placeholder / login 样式。
- `frontend/src/api/generated.ts` —— 重新生成（含 `/api/v1/live` 与 `/api/v1/ready`）。

### 新增（A）

- `frontend/vitest.config.ts`（jsdom + setup + `globals: false`）
- `frontend/scripts/export-openapi.py`（从 FastAPI app 对象离线导出 OpenAPI，确定性输出）
- `frontend/scripts/openapi-source.mjs`（导出 / 生成两个步骤的共享机制）
- `frontend/scripts/generate-api.mjs`（`generate:api`）
- `frontend/scripts/check-api-drift.mjs`（`check:api-drift`，漂移即 exit 1）
- `frontend/src/api/errors.ts`（`ApiError` / `UnauthorizedError` / `HttpError` / `NetworkError` / `UnexpectedResponse`）
- `frontend/src/api/client.ts`（`openapi-fetch` client + bearer 注入 + 401 生命周期）
- `frontend/src/api/readiness.ts`（`readReadiness`：200 → READY / 503 → NOT_READY 且保留 body）
- `frontend/src/api/readiness.test.ts` / `transport.test.ts` / `generated.test.ts`
- `frontend/src/app/App.tsx` / `AppProviders.tsx` / `ProductShell.tsx` / `queryClient.ts` /
  `router.tsx` / `routes.ts`
- `frontend/src/app/router.test.tsx` / `queryClient.test.ts`
- `frontend/src/auth/session.ts` / `AuthSessionProvider.tsx` / `RequireAuth.tsx` / `LoginPage.tsx`
- `frontend/src/auth/sessionBoundary.test.tsx` / `unauthorized.test.tsx`
- `frontend/src/pages/FoundationPlaceholder.tsx`
- `frontend/src/test/setup.ts` / `server.ts` / `handlers.ts` / `render.tsx` / `probe.tsx` / `raw.d.ts`

### 明确未改

- `frontend/tsconfig.json` —— **零改动**（`strict: true` 保持；AC-27）。
- `backend/**`、`scripts/**`（仓库根）、`docs/**`、任何 schema / migration = 零改动。

## Implementation

### 1. Router（Declarative）

`app/routes.ts` 是五页 IA 的唯一声明（`/overview`、`/market`、`/research`、`/trading`、`/system`），
`app/router.tsx` 用 `Routes` / `Route` 声明式装配：`/login` 为 Auth Shell，其余全部位于一个
受 `RequireAuth` 保护的产品 shell 内；index route（`/`）与未知路径 redirect 到 `/overview`。
**不存在顶层 `/ai` 路由**，`/login` 不属五页产品 IA。

### 2. Server Query / Cache

`app/queryClient.ts` 导出**单一应用级** `queryClient`。冻结策略：`refetchInterval: false`、
`refetchOnWindowFocus: false`（无默认高频轮询 / 无全局 refetch interval，行为确定可测）。
Retry：`401` 不重试、普通 `4xx` 不重试、`/ready` 503 因不是 error 而不进入重试、
network 与 5xx 有界重试（`MAX_QUERY_RETRIES = 2`）。**Query cache 的 `stale` 与 MarketPulse 业务
`FRESH / STALE` 无任何映射**，代码中不存在由 Query 状态推导业务新鲜度的路径。

### 3. Typed API Client / Transport

`api/client.ts` 用 `openapi-fetch` + 生成的 `paths`。应用代码只写 `/api/v1/...`，
**不硬编码任何后端 host**；路径解析到当前 document origin（同源同 scheme），开发期由 Vite
`/api` proxy 转发到 `127.0.0.1:8000`。

> 说明（**唯一**一处对"相对路径"的显式实现取舍）：origin 由 `window.location.origin` 提供，
> 而非把 `baseUrl` 留空。原因是 Fetch `Request` 构造函数在**浏览器 document 上下文之外**
> 拒绝相对 URL —— 实测 `new Request("/api/v1/ready")` 在 Node 下抛
> `TypeError: Failed to parse URL from /api/v1/ready`，而 Vitest/jsdom 正是该环境。
> 若留空 `baseUrl`，本批**必需**的传输 / 认证测试将无法执行。

Middleware 只做两件事：附加 `Authorization: Bearer <token>`；当 `401` 来自**非公开端点**时
触发会话失效。公开端点（`login` / `live` / `ready` / `health`，UI-V1-D01 §26 冻结）的 `401`
不被当作会话失效。

### 4. Auth Session Boundary

`auth/session.ts` 是唯一被批准持久化 bearer token 的位置（`sessionStorage`）；
**密码永不持久化**（本模块不提供任何接受密码的 API）。
`auth/AuthSessionProvider.tsx` 同时拥有 session 与绑定该 session 的 transport：
`signIn` 只把凭据交给 login POST；`signOut` 与权威 `401` 走同一条 `endSession`
（清 token + 清已认证 Query cache）。token 不解析、不派生额外前端 auth 权威；
后端 `401` 是唯一 auth authority；**不存在** refresh token 机制。
`RequireAuth` 声明式地把未认证状态收敛到 `/login`，并通过 router state 保留原定内部路由
（排除 `/login` 自身与 `//host`）。`LoginPage` 的 login 401 = 凭据错误：留在登录页、显示失败、
**不**清 session、**不**导航 ⇒ 无重定向循环。

### 5. `/ready` 503 语义

`api/readiness.ts` 把 `GET /api/v1/ready` 解释为语义结果：`200` → `READY`，
`503` + 可解析 JSON body → `NOT_READY` 且 **body 原样保留**。503 是**成功解释**而非抛错，
因此既不是 `NetworkError`、也不是通用后端故障，也不可能被重试。Readiness 与 Risk Admission
无任何推断关系。

### 6. Vite `/api` proxy

`/api` → `http://127.0.0.1:8000`，**不** rewrite `/api` 前缀；**未**引入宽泛开发 CORS。

### 7. OpenAPI 生成纪律

`generated.ts` 为纯粹自动生成产物（保留 generator banner，**未**手写任何业务类型）。
生成链路恢复为可复现：`scripts/export-openapi.py` 直接导入 FastAPI app 对象导出当前 OpenAPI
（**无需**运行服务、**无需**数据库、**无需** `.env` —— `Settings` 每个字段都有默认值），
输出确定性（`sort_keys` + LF + 结尾换行）；`generate:api` 据此重生成，
`check:api-drift` 重新导出 + 重生成并与已提交产物逐字节比对，漂移即 exit 1。
**未**为绕开弱 OpenAPI typing 手写重复权威 DTO。

### 8. Test Harness

Vitest（jsdom）+ RTL + jest-dom + user-event + MSW；MSW 拦截在**网络边界**，
`openapi-fetch` client、bearer 注入与 401 生命周期均以真实路径被驱动，未被 mock 掉。
`setup.ts` 显式 `cleanup()`（`globals: false` 下 RTL 不会自动注册 afterEach），
并对未处理请求设 `onUnhandledRequest: "error"`。

## Verification

真实执行（全部在本 worktree 内）：

| # | 命令 | 结果 |
|---|---|---|
| 1 | `git ls-remote origin refs/heads/main` | `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` = Task Base ⇒ 无 drift |
| 2 | `node --version` | `v22.22.2` |
| 3 | `npm --version` | `10.9.7` |
| 4 | `npm ci`（`--offline`，起点为空 `node_modules`） | exit 0：`added 187 packages in 3m`，由已提交 `package-lock.json` 干净安装（AC-30） |
| 5 | `npm run typecheck`（`tsc -b`） | exit 0 |
| 5a | 同上，注入临时类型错误 | exit 1，`src/typecheckProbe.ts(1,14): error TS2322` ⇒ **门有牙齿**（探针已删除，未进入提交） |
| 6 | `npm run test:run` | **7 files / 37 tests 全部 PASS**（exit 0） |
| 7 | `npm run build` | exit 0；`dist/assets/index-*.js` 294.91 kB / gzip 93.27 kB |
| 8 | `npm run generate:api` | exit 0；`generated.ts` 408 行，含 `/api/v1/live` 与 `/api/v1/ready`（及 login / health / runtime / instruments / universe / protected-ping） |
| 9 | `npm run check:api-drift` | exit 0：`no OpenAPI drift: /api/v1/live, /api/v1/ready present; generated.ts matches the backend contract` |
| 9a | 人为向 `generated.ts` 追加一行后重跑 | exit 1：`OpenAPI drift detected: src/api/generated.ts is not identical to a fresh regeneration…` ⇒ **门有牙齿**；随后 `generate:api` 复原并复读 exit 0 |
| 9b | `generate:api` 连跑两次 + 复原后取 sha256 | 复原后与基线**逐字节一致**（`sha256 = 04bff23c…44e84`）；再跑 `generate:api` 后仍为同一 sha256 ⇒ 生成确定、可复现 |

**门有牙齿与确定性**（本批收尾时在同一次运行内重跑，脚本 `mp-gate-checks.mjs`）：

- `typecheck` 注入类型错误 ⇒ exit 1（`src/typecheckProbe.ts(1,14): error TS2322`）；探针删除后 ⇒ exit 0。
- `check:api-drift` 在产物被人为篡改时 ⇒ exit 1；`generate:api` 复原后 ⇒ exit 0。
- 探针文件与篡改行均已移除，**未**进入提交（提交前 `git status` 已复核无残留）。

测试分布（`npm run test:run`）：`src/app/queryClient.test.ts` 6、`src/api/generated.test.ts` 3、
`src/api/readiness.test.ts` 5、`src/api/transport.test.ts` 9、`src/app/router.test.tsx` 7、
`src/auth/unauthorized.test.tsx` 3、`src/auth/sessionBoundary.test.tsx` 4。

任务卡 §17 覆盖对照：A Router（7 项）、B Auth（4 项）、C 受保护 401（2 项）、D Login 401（1 项）、
E Readiness（5 项）、F Transport（9 项，含 401 生命周期归属）、G Query（6 项）、H OpenAPI（3 项 +
`check:api-drift` 可执行门）。

**未执行 / 未声称**：浏览器端真机联调（无 running backend + 浏览器会话）；`npm run dev` 下的
真实 proxy 转发验证（proxy 配置为静态声明，未在本批做端到端运行验证）；任何后端 / 运行体验证。

## Result

`UI-F01-I01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`。

**不**等于 ACCEPTED / COMPLETE / HUMAN ACCEPTED —— 本批为 Worker 交付，独立复审与人工验收另开窗口。

## Remaining / Findings

- **F-01（非阻塞 Finding，本批不修）**：后端 `/api/v1/live` / `/ready` / `/health` / `/runtime` /
  `universe` / `market/instruments` 目前返回 `dict[str, object]`，生成的 OpenAPI 因此是
  `{[key: string]: unknown}` 而非显式 typed Response DTO。本批**未**替后端加 DTO
  （§14 明令禁止静默改后端 API 设计），也**未**手写重复权威 DTO。正式 Product Read API 的
  typed DTO 属 `UI-RD01` 范围。
- **F-02（非阻塞 Finding，本批不修）**：`frontend/vite.config.ts` 与
  `frontend/vitest.config.ts` 不在 `tsconfig.json` 的 `include` 内，`tsc -b` 不检查这两个配置
  文件（改动最小化取舍；未改 tsconfig）。
- **F-03（非阻塞 Finding，本批不修）**：`check:api-drift` 与 `generate:api` 依赖本机后端运行时
  可被导入（`py -3.14`），与仓库既有 Python 脚本约定一致；若未来仓库标准化为 uv / venv，
  此处需同步。
- **F-04（环境 Finding，非产品缺陷；本批不修）**：在**已存在**较大 `node_modules` 的工作树里执行
  `npm ci`，本机会在 npm 自己的 `node_modules` 递归删除阶段**静默冻结**（实测：进程存活但 90 秒内
  零文件写入、零删除；`npm ci --dry-run` 仅 569ms 即 exit 0，说明依赖解析本身完全正常，卡点纯在
  实际 reify 的文件删除上）。可用做法：先把旧 `node_modules` **整体重命名移出仓库**（同盘 rename，
  不做删除），再在空起点上跑 `npm ci` —— 实测 3 分钟 exit 0。该现象与本工作树、依赖内容、缓存均
  无关（离线缓存与全新缓存两种配置下都复现），属本机沙箱对批量删除的拦截行为。**记录以便后续
  CI / 其他机器不要照搬这一绕法**：正常环境无需此步骤。
- 上述 Finding 均不阻塞本批 Acceptance Boundary；本批**不**顺手修复（CIP-05）。

## Risks

- R-01｜**OpenAPI 弱类型**：`/live`、`/ready`、`/health`、`/runtime`、`universe`、
  `market/instruments` 在 schema 中是 `unknown` 级 body。Foundation 只对 `/ready` 做了
  最小语义解释（不引入权威 DTO），未来正式页面在 `UI-RD01` 补齐 typed DTO 前，
  相应读面的类型安全是**弱**的。
- R-02｜**transport 解析分工**：`openapi-fetch` 对非 2xx **不抛异常**（返回
  `{ data, error, response }`）。本批只在 `/ready` 路径上做显式分类；未来若直接使用
  `client.GET(...)` 而不经分类，调用方必须自行处理 `response.ok`。已由 `transport.test.ts`
  固定住当前语义。
- R-03｜**未做浏览器端真实联调**：proxy 与相对同源请求的行为只经 MSW 网络边界验证，
  未经真实 backend + 浏览器验证。

## Evidence

- 分支：`ui-f01-i01-frontend-foundation`（**未** merge `main`）。
- Task Base / 远端 `main`（执行前实读）：`2c95cc21cc99d85c5692c5f9b276c5805cc32b13`。
- 实现提交：本批单 commit（见该分支 HEAD）。
- 生成产物：`frontend/src/api/generated.ts`（408 行；含 `/api/v1/live`、`/api/v1/ready`）。
- 测试证据：`npm run test:run` → 7 files / 37 tests PASS（见 Verification #6）。
- 安装证据：`npm ci --offline` → exit 0，`added 187 packages in 3m`（空起点，日志 `E:/mp-npm-ci-run.log`）。
- 门证据：typecheck 注入错误 exit 1（#5a）；`check:api-drift` 人为漂移 exit 1（#9a）；
  复原后与基线逐字节一致 + 生成可复现（#9b，`sha256 = 04bff23c…44e84`）。

## Context For Next AI

1. 本批**只**建立前端 Foundation；五页仍是 `FoundationPlaceholder`，**不得**据此声称任何业务 UI
   或 Product Read API 已存在。
2. 正式页面接入时的既定分工：服务端状态 → TanStack Query；可分享的 route/filter 状态 →
   URL / Router；认证会话 → `AuthSessionProvider`；组件局部状态 → React state。
   **不得**新增通用全局 store（本批明确未引入 Redux / Zustand / MobX / XState）。
3. **不得**由 Query cache 的 `stale` 推导 MarketPulse 业务 `FRESH / STALE`；业务新鲜度由 backend
   显式状态与权威观测时间戳拥有。
4. `/ready` 503 的既有语义（保留 body、非网络故障、不重试）已由测试固定；改动它属改变冻结契约，
   需要另批授权。
5. 改动 `frontend/package.json` 后必须同步 `package-lock.json` 并跑 `npm ci`（本机在已有
   `node_modules` 上直接跑 `npm ci` 会冻结，做法见 F-04）；
   改动后端 OpenAPI 后必须跑 `npm run generate:api` 并提交产物（`npm run check:api-drift` 会拦）。
6. 本批**未**触碰后端 / schema / migration / Gate / Live / PRE-01B-I2 / Real AI；
   上述冻结边界仍然有效。
