# ARCHITECTURE.md —— MarketPulse-AI · v6.5

## 0. CLI 边界（V0.1 独立例外见 §7）
- **一句话目标**：运行 `node fetch-history.mjs`，获取币安 BTC/USDT 最近 30 天 5 分钟已收盘 K 线，校验后写入 `history-5m.csv`。
- **CLI 明确不做**：网页、LLM、数据库、交易下单、定时调度、实时推送、命令行参数；独立 V0.1 例外见 §7。
- **V1 范围上限**：1 个数据源、1 个交易对、1 个周期、1 条命令、1 个 CSV 文件。
- **下游消费者**：离线量化回测沙盒（Python/Node），读取 `history-5m.csv`。
- **下游契约**：
  - 表头固定为 `open_time,open,high,low,close,volume`，无索引列。
  - `open_time` 为 UTC Unix 毫秒整数。
  - 价格与成交量保持币安返回的原始十进制字符串，不经浮点转换，不重新格式化。
  - 行按 `open_time` 严格递增，相邻间隔 300000 毫秒，无缺失、无重复（由 X1 保证）。
- **历史遗留**：除 §7 经独立 Issue 授权的有限 V0.1 修改外，`frontend/`、`backend/` 及其他既有文件保持原状，禁止修改、删除、迁移或重构。
- **独立只读审计**：新增 `mp_audit/`，仅允许在该目录新增审计脚本、样本和报告。`backend/`、`frontend/`、`research/` 及其他既有文件只读，不得修改或覆盖。C1 的数据源与周期限制、C3 的抓取器退出约定及 X1/X2 仅适用于 V1 抓取器；审计仍须遵守 C2 的失败不污染原则与 C5 红牌限制。
- **测试契约修复例外**：允许 Human 单独授权的前置 Issue 仅修改 `test/fetch-history.test.mjs` 中的 GWT-09 白名单及其直接相关测试。此例外不适用于审计 Issue #4，不授权修改其他既有文件。

## 1. 组件与通信

| 组件 | 职责 | 允许接触 | 禁止接触 |
| :--- | :--- | :--- | :--- |
| `fetch-history.mjs` | 分页抓取、数据校验、CSV 原子写入 | 币安公开 API、本地 CSV | 数据库、LLM、交易接口 |

- **通信方式**：HTTPS GET → JSON → 内存校验 → 同目录临时文件 → 原子 rename 替换 CSV。无队列、无数据库。

## 2. 通用硬约束
- **C1 外部依赖**：仅允许 `https://api.binance.com/api/v3/klines`，固定 `BTCUSDT`、`5m`，每次最多 1000 条，按时间顺序分页。单次请求超时 10 秒，不自动重试。超时、网络错误、HTTP 非 200（含 429/418）立即失败。防的失败：请求挂死、限流后继续请求、错误数据进入结果。验证：测试（超时、HTTP 错误、分页）。
- **C2 失败不污染**：全部抓取和校验成功后才写入，使用同目录临时文件加原子 rename。防的失败：残缺数据覆盖已有的完好 CSV。验证：测试（失败前后旧文件字节一致）。
- **C3 对外结果明确**：成功退出码 0，生成 UTF-8 CSV；失败退出码 1，stderr 仅输出一行 `FETCH_ERROR`，不暴露堆栈。防的失败：错误被当成成功。验证：测试。
- **C4 CLI 不适用 / V0.1 本地产品免登录**：CLI 只用公开接口，无密钥。Windows 本地个人使用的 V0.1 五个一级页面壳 `/overview`、`/market`、`/research`、`/trading`、`/system` 均无需账户密码、登录 Token 或登录跳转，`/` 默认进入 `/market`。后续产品功能也不要求用户执行账号密码登录流程；但页面可访问不等于敏感后端 API 已获授权，既有受保护接口暂保留认证，未来替代须另行设计可证明的本机调用来源、操作授权与风险门禁，未完成则 fail closed。行情 GET 匿名读取仅限 §7.2 的 Windows 严格条件。Secret 不进入 Git、前端或 API 返回。
- **C5 红牌文件**：`.github/**`、`AGENTS.md`、`ARCHITECTURE.md`、测试配置、`package.json`、锁文件。普通任务一律不得修改，只有 Human 单独开的架构 Issue 才可改。验证：终审清单（检查 Files changed）。

## 3. 模式库
- 无。V1 不提供实时服务，不接入 LLM，不自动重试。

## 4. 项目特有约束
- **X1 时间完整性**：结束时间为运行时刻向下取整到最近的 UTC 5 分钟边界，只包含已收盘 K 线；起点为结束时间减 30 天。必须恰好 8640 条，开盘时间严格递增，间隔 300000 毫秒，不得缺失、重复或越界。防的失败：分页遗漏、重复、混入未收盘数据。验证：测试（固定时钟、跨页缺失与重复）。
- **X2 数据格式**：每条必须是 12 字段数组；开盘时间为合法整数毫秒；开、高、低、收为大于 0 的十进制字符串；成交量为非负十进制字符串；满足 `high >= max(open, close, low)` 且 `low <= min(open, close)`。任一字段缺失或非法，整次失败。防的失败：异常价格、空字段混入 CSV。验证：测试（非法格式、非法价格、缺字段）。

## 5. 技术栈与目录
- **CLI 语言/运行时**：Node.js 20+，JavaScript ESM，仅使用内置模块和原生 `fetch`。
- **测试命令**：`node --test`　**启动命令**：`node fetch-history.mjs`
- **单 PR 行数上限**：300（含测试）。
- **目录 → 职责**：
  - `fetch-history.mjs`：抓取、校验、写入。
  - `test/fetch-history.test.mjs`：离线测试，使用模拟响应。
  - `history-5m.csv`：运行产物，不提交（由 `.gitignore` 任务卡保证）。
  - `frontend/**`、`backend/**`：除 §7 有限 V0.1 例外外，历史遗留禁止修改。
  - `mp_audit/**`：独立只读审计。允许新增脚本、读取既有日志和公开数据源，累计下载数据不得超过 20 MiB。所有新增文件仅写入本目录，不覆盖既有文件。报告必须包含事实证据及所核验数据的 SHA-256；无法核验的事项标注 `NOT_VERIFIED`。仅用于研究可信度核验，不进入 V1 生产流。
- **GWT-09 白名单**：`test/fetch-history.test.mjs` 中的 GWT-09 必须允许 `mp_audit/**` 下的新增审计文件，不视为污染；禁止修改、删除已有审计文件。其他未授权路径及未跟踪文件仍须拒绝。保留现有未跟踪文件拒绝测试。此白名单调整仅允许通过第 0 节所述独立前置修复 Issue 实施，不得合并到 Issue #4。
- **依赖**：零新增。

## 6. 风险区域
- **默认**：网络请求、文件读写、解析外部输入、并发、鉴权/金额、数据迁移。
- **本项目追加**：无。
- 命中以上任一区域的 PR 为高风险，走异源 QA；其余由 Human 审查。

## 7. V0.1 有限架构准入（ARCH-V01-01-A01）

- Human 授权：[Issue #9 批准记录](https://github.com/zwmhua2-lab2/MarketPulse-AI/issues/9#issuecomment-6498889582)。本次只修订架构和门禁，业务源码、数据库及服务均不启动；最终 Diff 待独立 QA / Human 验收。
- **适用范围**：Windows 本地个人使用，React Web UI + FastAPI；BTC-USDT / ETH-USDT 的市场观察、Scanner、Opportunity、证据详情、研究摘要和系统状态。Web 业务界面只读，监听本地地址，不部署公网。
- **排除**：AI 自动决策、G2→G3 Advisory 激活、Paper Execution / Live Trading 激活、新量化回测引擎、多模型投票和无关重构。
- **CLI 不变**：§0–5 中抓取器行为、C1/C2/C3/X1/X2 仍约束 Binance BTCUSDT 最近 30 天 5m CLI；原子写入、失败不污染、退出码不变，不将 CLI 数据源/周期/存储限制扩展到 V0.1。C5 红牌规则及 mp_audit 已接受边界不变；审计任务自身仍无前后端写权限。

### 7.1 独立本地观察入口（设计边界，尚未实现）

- 优先复用 Market Data、G2 Scanner、EventRuntime、Opportunity Capture、Product Read；由 FastAPI 生命周期管理独立观察入口，原 RuntimeHost 默认关闭，不冒充、继承激活或借用旧 Host 的生产所有权。
- 旧 RuntimeHost 仍是既有生产经济运行的唯一 composition owner；本例外仅限隔离的非经济本地观察。旧 singleton、owner-session proof、恢复、Risk、订单与持仓保护契约不变。
- 观察入口仅可向隔离的本地观察数据库持久化必要市场事件、Scanner 状态、Opportunity 和 Evidence，不接触既有生产经济数据，不构造或激活 PaperExecution、G3、AI Provider、交易订单及持仓保护执行链。后台观察写入不等于交易授权。
- 不改变 G2 检测规则、Capture 身份、因果准入、revision 或幂等性。`FORWARD_PAPER` 必须保留 live-ingress causal proof + durable Capture Anchor 的严格语义；重试复用冻结事实，不用历史重放或新时间/BBO补造 Forward 证据。
- 后续独立任务必须验证所有权、数据库隔离、重复启动、启动失败、运行异常、关闭与资源释放；不能确认隔离或事实可信时 fail closed。不得通过关闭既有生产保护来实现观察模式。
- 当前 ProductReadContext 仅借用真实 RuntimeHost；独立观察源适配尚未实现，不能伪造 Host 让类型检查通过。新增入口及适配的精确路径须在后续 Issue 中明确，超出下表时先单独修订准入，不默认开放后台目录。

### 7.2 后续只读产品边界与路径资格

- 保留五个顶层路由 `/overview`、`/market`、`/research`、`/trading`、`/system`；五个页面壳均无需登录即可打开，且不以行情后端的运行准入条件为前提；`/` 默认进入 `/market`。未实现的页面明确展示占位/未接入，不得因未登录而跳转 `/login`，也不得将未接入功能冒充可用。匿名访问不创建隐式 Bearer 或管理员会话，不显示无效的退出登录控件。原 `/login`、V1 Auth Provider 和登录 API 暂保留为旧接口兼容，但不再作为五页导航门槛；页面开放不等于放开数据/API 或交易控制。交易页仅如实显示已实现状态或未接入占位，不引入交易控制；数据层未获准入时仅展示认证/不可用提示，不展示私有信息。
- **401 适用边界（V0.1 页面壳例外）**：`DECISIONS.md` UI-V1-D01 的受保护 API 返回 `401` 后，原 Auth Session Boundary 仍按既有语义清除 token/session 与已认证 Query Cache，不改变后端权限判定。原 Login 边界重定向依赖 `RequireAuth` 路由门禁；V0.1 五个页面壳不再设置此门禁，因此页面不因后端 `401` 跳转 `/login`。当前 `/market` 行情 GET `401` 只显示无权读取提示；未获数据权限时不得展示私有信息或凭空填充行情。兼容 `/login` 路由仍保留，此有限页面导航例外不扩大其他 API 的匿名权限。
- 复用现有 Product Read API；仅 `GET /api/v1/product/market-candles` 可按下述条件接受匿名请求。该接口仍仅允许 BTC-USDT / ETH-USDT、5m / 15m / 1h，返回 60 根真实已收盘 OKX 公共 K 线；数据完整性、时间、新鲜度、来源及不可信时 fail closed、显式 503 的约束不变。
- 行情 GET 匿名准入必须**同时**满足后端实际运行 OS 为 Windows（不得凭浏览器 UA 或前端检测）、`RUN_MODE=TEST`、`LOCAL_ONLY=true`、`HOST=127.0.0.1`、`RUNTIME_HOST_ENABLED=false`、`ADVISORY_ACTIVATION_LEVEL=DISABLED`，且服务实际仅监听本机 loopback、请求连接对端实际为 loopback。来源须依据可验证的连接级 peer 或未被代理头改写的 ASGI client；不得凭浏览器 UA、`Host`、`X-Forwarded-For`、`Forwarded` 等可伪造头放行，也不得将未验证代理链的客户端地址当作授权证据。无法证实来源时 fail closed。任一条件不满足时，保留既有合法会话鉴权；缺失或错误认证仍返回 401，且在鉴权拒绝前不得向 OKX 发出请求（上游调用数为零）。不得全局移除 `verify_session`、关闭其他鉴权、泄露凭据或创建隐藏 Token；不开放公网、LAN 或隧道访问。
- 除既有 `GET /api/v1/product/market-candles` 的严格条件化匿名例外外，其他 Product Read 与受保护 API **目前仍保留原有鉴权**；五个页面壳免登录不自动开放其数据或操作。后续所有用户功能均不设置账号密码或其他强制登录流程（产品硬约束），但敏感数据、配置修改、凭据及任何经济风险增加型操作必须由后续独立任务提供可信本机调用来源、请求来源防伪与操作授权/确认，仍受 Risk/Execution 权限边界约束；机制未验证前不得通过全局关闭 `verify_session`、信任 Host/代理头或默认放行来满足免登录。Scanner、Opportunity、RuntimeHost、AI、Paper/Live 和交易执行链不因页面免登录激活或扩大权限；不增加公网/LAN 监听、数据库改造或交易能力。
- Opportunity 币种筛选仅为后续允许设计，必须保持正确分页与 Evidence 身份；API 类型使用仓库官方生成命令并执行 drift 校验，禁止手改生成内容冒充同步。
- 下表仅为 GWT-09 **路径资格**，不是文件内容审查或写入授权。每个实施 Issue 必须另有 Human 精确白名单，C5 受保护文件仍需明确批准；Issue #21 仅授权修改 `ARCHITECTURE.md`，后续业务代码与测试需独立 Issue 授权。若所需路径不在现有 GWT-09 白名单中，先报告具体差异，不扩大目录通配符。
- 四份文档的 M 路径资格持续有效，不等于永久修改授权；本任务不授予未来任意修改文档的许可。未来修改 `ARCHITECTURE.md` 仍须独立架构 Issue 和 Human 明确批准，C5 红牌规则不变。
- **可信启动入口路径准入（Issue #24）**：仅新增 `backend/src/marketpulse/main.py` 的已有文件 M 路径资格；路径合格不等于后续代码修改获授权，也不等于已证明监听范围或原始连接 peer 可信。后续须单独授权并实证验证 loopback 绑定、代理头不改写与请求来源；不能证明则匿名行情 fail closed；若需要其他文件，先申请精确增补，不扩展目录白名单。

| 合资格路径 | 允许状态 / 内容边界 |
| --- | --- |
| `ARCHITECTURE.md`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`、`PROJECT_STATE.md` | M；持续有效的路径资格，具体修改须每个 Issue 单独授权 |
| `dev_log/2026-10-29-v01-architecture-admission.md` | A / 未跟踪新增；本次真实记录，既有日志不可覆盖 |
| `frontend/src/app/router.tsx`、`frontend/src/app/ProductShell.tsx` | M；后续只读页面接线，五路由不变 |
| `frontend/src/app/router.test.tsx` | 仅 M；既有路由测试的后续资格，本任务不得修改该文件 |
| `frontend/src/api/generated.ts` | M；后续官方生成与 drift 校验 |
| `backend/src/marketpulse/api/app.py` | M；后续 K 线路由注册，非 Runtime 激活授权 |
| `backend/src/marketpulse/main.py` | 仅 M；后续受独立 Issue 精确授权的 V0.1 Windows 本地可信启动入口/监听与连接事实，不改 RuntimeHost、交易或其他 API 鉴权 |
| `frontend/src/v01/**` | A / M / 未跟踪新增；仅 `.ts`、`.tsx`、`.css` 页面、只读客户端及相应测试 |
| `backend/src/marketpulse/api/product/market_candles.py`、`backend/tests/test_product_market_candles.py` | A / M / 未跟踪新增；后续最小只读 K 线接口及测试 |

- V0.1 子目录名仅 ASCII 字母数字、下划线、连字符；文件名以此类字符起始，可含点，禁止空段、`.`/`..` 路径段、反斜杠、控制字符、隐藏文件及 `config.*` / `*.config.*` 配置。不放开 `backend/**` 或 `frontend/**`。
- CLI 两路径保留 A/M 与原未跟踪允许行为；mp_audit 仍只允许新增。所有路径拒绝 D/R/C/T/U/X；未知未跟踪文件及 Git 失败仍拒绝。此条补充 §5，不能据路径测试 PASS 认定获得授权。

### 7.3 真实数据与状态

- 不用模拟行情冒充真实行情，不伪造 Scanner / Opportunity，不编造收益、胜率或策略盈利；没有可证明的 Evidence 关联时，禁止按币种、时间或相似字段猜测关联。
- `NOT_ACTIVATED`（未激活）、`UNAVAILABLE`（不可用）、`EMPTY`（可信查询为空）和数据过期必须区分；失败或过期不能显示为空或健康。
- R3/N1 仅历史探索，研究双门通过记录为 0；研究登记差异只展示，不修正研究成果，不宣称 Trading Edge 已证明。
