# ARCH-V01-01-A01｜架构准入与门禁修订记录

## 准入与基线

- Human 授权：Issue #9 comment `6498889582`，已读取全文；六文件、独立观察入口、Worktree、提交/推送/Draft PR 均有明确批准。
- 实际远端 main / fetch 后 origin/main / 初始 HEAD：`51b93e693200ffbc30291ad9e770509eb64c9324`；无开放 PR、无既有 task/9 分支。
- 新 Worktree：`E:/Documents/AI-Developer/temp/MarketPulse-AI-ARCH-V01-01-A01`；创建前不存在，分支 `task/9`，初始 Git status 干净。目录隔离不是 OS 安全沙箱。
- 原工作区 `.workbuddy/` 归属 UNKNOWN，仅只读查看元数据/顶层名（memory/）/Git 跟踪状态，未读内容；未跟踪且不是已注册 Worktree，保持原状。
- 原 main 及 research/r1 等既有 Worktree 未切换、修改或清理；根 README.md 缺失按 Human 续办指令记为非阻断。根 package.json 亦不存在，未创建。

## 问题证据与最小方案

- ARCHITECTURE v6.4 §0/§5 禁止 Web / 前后端，GWT-09 仅容许 CLI 两路径与新增 mp_audit，确实拒绝本次文档路径。
- `runtime_host.py::_compose_services` 构造 PaperExecutionService / SystemRiskGate / PositionProtectionService；不能以启动旧 Host 替代只读观察入口。
- `config.py` 中 runtime_host_enabled 默认 False；`api/app.py::lifespan` 关闭时设置 host=None；`api/product/context.py` 仅接受真实 RuntimeHost，独立观察源适配尚不存在。
- `edge/capture.py` / DECISIONS 中 Capture Anchor、live-ingress proof、FORWARD_PAPER / revision 契约继续保留；五路由以 `frontend/src/app/routes.ts` 为准。
- 采用 §7 的有限非经济观察例外：不重写旧 production Host 所有权，不改变交易核心。后续入口、读源适配的精确路径及生命周期验证需独立 Issue。
- GWT-09 是路径资格检查，不能证明 Human 授权或业务语义安全；每个实施 Issue 仍需精确白名单。未开放后台/前台全目录。
- 只收紧 CLI 路径的非法 D/R/C/T/U/X；正常 A/M 和原未跟踪许可保留。mp_audit 原用例、未知文件与 Git 失败拒绝用例全部保留。

## 实际验证（Windows / Node v24.14.0）

- 修改前：`node --test test/fetch-history.test.mjs`，exit 0，43 PASS / 0 FAIL。
- 先补测试：`node --test --test-name-pattern='GWT-09 contract V01 (modify|reject D fetch)' test/fetch-history.test.mjs`，exit 1，14 FAIL：13 个合资格修改被拒绝，旧 CLI 删除被错误放行。
- 首轮 `node --test --test-name-pattern='GWT-09' test/fetch-history.test.mjs`，exit 1，233 PASS / 3 FAIL：含换行路径被拒绝，但 Node 报告缩进导致原错误文本断言失败；补原始 stderr 路径诊断，未改断言。
- `node --test --test-name-pattern='GWT-09 contract V01 forbidden.*unsafe' test/fetch-history.test.mjs`，exit 0，6 PASS。
- 补配置反例：`node --test --test-name-pattern='GWT-09 contract V01 forbidden.*(vitest|trailing)' test/fetch-history.test.mjs`，exit 1，3 PASS / 3 FAIL；配置文件误放行，随后限定排除 config.* / *.config.*。
- 最终 `node --test --test-name-pattern='GWT-09' test/fetch-history.test.mjs`：exit 0，242 PASS / 0 FAIL / 0 SKIP。
- 全量 CLI `node --test test/fetch-history.test.mjs`：exit 0，265 PASS / 0 FAIL / 0 SKIP，61042.9303ms；原 43 项保留，新增 222 项。原始日志：Worktree 同级 `MarketPulse-AI-ARCH-V01-01-A01-evidence/cli-regression.txt`。
- 逐行比较 C1/C2/C3/C5/X1/X2 原文完全未变；三份产品/决策/状态文档历史行完整保留。`git diff --quiet origin/main -- fetch-history.mjs backend frontend research mp_audit .github AGENTS.md`：exit 0。
- 无真实网络抓取、依赖安装、数据库创建或服务启动；CLI 网络和文件异常均沿用原测试 Mock。前后端全量、Runtime/E2E、真实数据链路 = NOT_TESTED。

## GWT 对照（卡内编号，不混淆 CLI 原 GWT 编号）

| 卡内验收 | 验证映射 | 结果 |
| --- | --- | --- |
| GWT-01 | 人工逐条核对 ARCHITECTURE §0/§5/§7 与旧 C1/C2/C3/X1/X2；CLI 源码零改动 | PASS（文档自查） |
| GWT-02 | §7.1 + DECISIONS 限定补充；旧 Host 默认关闭、隔离观察、经济服务禁用 | PASS（文档自查）；运行 NOT_TESTED |
| GWT-03 | §7.3 + PRODUCT_REQUIREMENTS；真实来源/失败/空/过期/不可证明关联 | PASS（文档自查） |
| GWT-04 | GWT-09、原 contract/QA 未跟踪回归、新 V01 路径及状态矩阵 | PASS，242/242 |
| GWT-05 | 全部 `test/fetch-history.test.mjs`，原 43 项保持 | PASS，265/265 |
| GWT-06 | 相对 origin/main 的 name-status / numstat / diff --check；精确六路径核对 | PASS，+188/-11 = 199 行，6 文件，越界 0，check exit 0 |
| GWT-07 | PROJECT_STATE 本次段落与本记录均标候选、业务未启动、运行/E2E未验证 | PASS（文档自查） |

## 文件与剩余风险

- ARCHITECTURE：受保护文件经 Issue 明确批准，最小适用范围修订及 §7；C5 本身不变。
- PRODUCT_REQUIREMENTS：当前优先目标；DECISIONS：有限观察例外；PROJECT_STATE：候选真实状态；test/fetch-history.test.mjs：路径资格与直接回归；本 dev_log：实施证据。
- 最可能出错的两点：后续把路径资格误当写权限；后续把独立观察适配为旧 Host 或绕过 Capture 因果证明。均须独立 Issue、审查和运行证据，不能由本次测试证明安全。
- 后续建议：先单独实施最小只读 market-candles；再明确观察入口/读源适配路径与生命周期、隔离、幂等验证，保持 300 行分批；Opportunity 筛选另验证分页/证据身份。
- 本次仅候选提交及 Draft PR；不合并、不部署、不继续业务功能。自测 PASS 不等于独立 QA PASS 或 Human 接受，最终提交身份与 PR 见交付报告/PR 元数据。

## ARCH-V01-01-A01-FIX-01｜QA R01 补充修复

- 执行前回读 Issue #9 补充授权 `6500413090`；PR #10 为 OPEN/Draft，Base `51b93e693200ffbc30291ad9e770509eb64c9324`、Candidate `8c7d6d4407bcc798aa8cf9e92729cf607a65dad6` 与干净 `task/9` Worktree 一致。仅本轮三文件可改，完整 PR 仍限原六文件、300 行。
- D-01：Node 22.22.2 的报告器转义/缩进换行，与 Node 24.14.0 不同；原换行路径诊断完整字符串匹配失效，精确非法路径结果及退出码判定未错。原 unsafe 六例在 Node 22 实测 3 PASS / 3 FAIL、exit 1；保留失败用例，改为按顺序核验换行路径的所有非空诊断分段，普通路径仍完整匹配，精确结果和子进程退出码断言不变。
- D-02：先将既有 `frontend/src/app/router.test.tsx` 加入直接测试矩阵，旧门禁的 M 合资格断言实测失败、exit 1，随后只在 existing 精确列表中增加此路径。矩阵覆盖 M 允许及 A/未跟踪/D/R/C/T/U/X 拒绝；另补 routes.ts、相似文件名及 frontend/src/test 路径反例，不开放目录；该前端测试文件实际零修改。
- D-03：§7.2 明确四份文档 M 为持续路径资格，具体修改仍需每个 Issue 独立授权；未来 ARCHITECTURE 修改须独立架构 Issue 与 Human 明确批准，C5 不变。本次未增加自动授权机制。
- D-04：Human 已补充代理发布溯源；两个授权评论均是聊天指令代发，不是 Human 本人 GitHub 账号的独立签署证据。Codex 不证明身份；如审核要求账号亲签，由 Human 补证。
- D-05：原候选的 C4 修改属于 CLI 公开接口无密钥边界与 V0.1 现有鉴权、Secret 保护边界的澄清；不改变 CLI 实现或鉴权行为。
- D-06：原候选将 CLI 两路径 R/C 从原门禁可放行收紧为拒绝；A/M 和原未跟踪资格保留。这是原路径保护收紧，不涉及 CLI 抓取业务变化。
- 以上为追加记录，历史测试结果未修改。FIX 验收映射：01=两版本 GWT-09；02=router.test.tsx 九状态矩阵；03=全部原门禁；04=固定 Base 的六文件/300 行及 FIX 三文件检查；05=§7.2 与 C5 文档自查。独立 QA R02 与 Human 验收仍待进行。

### FIX-01 实际验证（Windows）

- Node 22.22.2：使用仓库外官方 win-x64/node.exe，SHA-256 与该版本官方 SHASUMS256.txt 一致；Node 24.14.0：使用本机既有运行时。无仓库依赖新增。
- 两版本分别执行 `--test --test-name-pattern='GWT-09' test/fetch-history.test.mjs`：各 exit 0、260 PASS / 0 FAIL / 0 SKIP。
- 两版本分别执行 `--test test/fetch-history.test.mjs`：各 exit 0、283 PASS / 0 FAIL / 0 SKIP；Node 22 为 70721.1912ms，Node 24 为 67414.0669ms。原有 CLI、mp_audit、危险路径、未跟踪及 Git 失败测试全部保留。
- 新增 18 个矩阵用例：router.test.tsx 九种状态及三个未知近似路径各 M/A/未跟踪反例；Node 22/24 均通过。D-02 修复前定向结果为 11 PASS / 1 FAIL、exit 1（含三个未知路径反例）。
- 定向和完整回归使用的测试源码 SHA-256：`515578b124454600b2e51e5f537cad6cd7bca923c82176aed26fa0f80bac8d7a`；最终仅追加文档验证记录，测试源码未再修改。
- 范围和契约检查：FIX 三文件、完整 PR 原六文件/不超过 300 行、diff --check、C1/C2/C3/C5/X1/X2 原文、前后端及 CLI 源码零修改、历史日志前缀保全均 PASS；具体 numstat 与源码哈希保留在外部 scope-final.json。
- 原始红/绿日志、运行时校验、GitHub 授权快照和范围核验保留于 Worktree 同级 `MarketPulse-AI-ARCH-V01-01-A01-FIX-01-evidence/`；旧 evidence 未改。Node 20、前后端全量、真实网络、数据库、观察入口及经济服务运行/E2E = NOT_TESTED；未合并或部署。修复自测不等于独立 R02 关闭缺陷。
