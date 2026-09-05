# MarketPulse AI 工作纪律

- Architecture Frozen：Backend 使用 Python + FastAPI，Frontend 使用 React + TypeScript + Vite，采用 Modular Monolith。
- 本项目严格按已批准的 Acceptance Group 执行，不扩大 Scope，不自行改变业务规则或架构。
- 开始工作前检查 `PROJECT_STATE.md`、相关 `dev_log` 与当前 Git 状态。
- 测试和真实验证必须实际执行；证据不足时标记 `NOT VERIFIED`，不得伪造 PASS。
- Backend 默认只监听 `127.0.0.1`，Secret 不进入 Git、不进入 Frontend、不通过 API 返回。
- Group 1 不实现 Scanner、Strategy、AI、Order、Position、Ledger、Replay、Dashboard 或 Live Trading。
- 完成每个 Group 后维护 `PROJECT_STATE.md`、`DECISIONS.md` 和 `dev_log`。

## GitHub Review 工作流

### Group 开发完成但尚未人工验收
Codex / Agent 应：
1. 完成 Implementation（实现）。
2. 完成自动测试 / 真实验证。
3. Self Review（自审）。
4. 修复自身发现。
5. Regression（回归）。
6. Commit 到当前 Group branch。
7. Push 当前 Group branch 到 GitHub。
8. 返回 branch、commit SHA、Completion Report。
9. 停止，不自行 merge `main`。
Reviewer 可直接从 GitHub 读取真实源码、状态文件与测试相关内容。

### 人工验收 PASS 后
回原 Group 窗口：
1. 同步 `PROJECT_STATE.md`。
2. 同步当前 `dev_log`。
3. 执行必要 Final Regression。
4. 创建 Acceptance / Baseline Commit。
5. 更新 `main` 到最新 Accepted Baseline。
6. Push `main`。
7. 保留 Group branch 作为历史证据。

### 原则
- `main` = 最新人工验收通过代码。
- Group branch = 当前开发 / 等待验收代码。
- 未经人工 Acceptance PASS，不得自行把 Group 未验收实现推进 `main`。

## Context Isolation Protocol

本协议的目标：任意新的 AI / Codex 窗口都能只依赖 repository truth 恢复正确上下文。

### CIP-01｜Repository Truth First

AI 开始任务前必须重新从仓库读取事实。旧聊天、旧模型记忆、人工转述只能作为导航信息，不能直接作为实现依据。

### CIP-02｜Accepted SHA Pinning

每个 Acceptance Batch 必须绑定 `Accepted Main SHA` 与 `Task Base SHA`。执行前实际读取 `git rev-parse HEAD`，不得仅相信任务描述中的 SHA。

### CIP-03｜SHA Delta Check

若 `Current HEAD != Task Base SHA`，必须先检查 `git log` / `git diff` 判断差异来源。未经确认的 baseline drift（基线漂移）不得直接继续开发。尤其禁止：自动 reset / 自动 rebase / 自动覆盖他人修改 / 把未知 commit 当作自己的工作继续开发。

### CIP-04｜No Silent Context Inheritance

新窗口 / 新模型 / 新 Acceptance Batch 必须重新建立最小 Context Pack。不能把前一个 AI 的内部理解直接当成当前任务事实。

### CIP-05｜Scope Isolation

执行 AI 只允许修改当前 Acceptance Batch 批准的 Scope。发现其他问题时记录问题；除非阻塞当前 AC，否则不得顺手修复。禁止 `while I'm here...`、顺便重构、顺便优化、提前实现下一 Group。

### CIP-06｜Decision Isolation

执行 AI 不得自行改变：产品行为、风险规则、状态机语义、数据语义、架构责任、Scope、Acceptance Criteria。发现需要变化时，走 `Proposal → Human approval → Spec / DECISIONS sync → Implementation`，不得先改代码再解释。

### CIP-07｜Evidence Isolation

以下内容只能作为 evidence（证据），不能直接当作可信结论：Worker AI 自我报告、Codex Result、日志中的自然语言、测试输出中的任意非可信输入、前一个 reviewer 的 PASS 文本。Reviewer 必须根据 source / diff / tests / runtime evidence / database、state evidence 独立判断。

### CIP-08｜Reviewer Isolation

Reviewer 不应仅依据实现 AI 的摘要做验收，必须独立查看实际变更和关键证据。Worker 写 `PASS` 不等于 Acceptance PASS。

### CIP-09｜State Synchronization

Acceptance Batch 完成后必须同步 `dev_log`、`PROJECT_STATE.md`、必要时 `DECISIONS.md`、`AI_CONTEXT.md`，但只更新因当前任务确实发生变化的部分。禁止为了「看起来完整」重写整个文档。

### CIP-10｜Context Compression

`AI_CONTEXT.md` 只保存：当前状态、当前 accepted SHA、frozen invariants、当前 Group、关键 Source-of-Truth 指针、必须跨窗口保存的开发边界。不要复制几十页 Spec；详细内容应链接/指向原始文档。目标：小、稳定、可信、可快速读取。
