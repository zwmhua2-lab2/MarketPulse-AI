# 2026-09-15 — SE-02D-D01-FIX-01｜Revision Folding + Population/Coverage Identity

## Task / Status

修复 reviewed D01 candidate `1b2494c66e0c7623edf8a00d3b88f29627882771` 的
`D01-R1 / P1`、`D01-R2 / P1`，并最小澄清 `D01-R3 / P2`。

```text
SE-02D-D01-FIX-01 = READY FOR INDEPENDENT RE-REVIEW
Human Acceptance = NOT GRANTED
Implementation Authorization = NO
```

## Requirement / Scope

只修改 D01 design contract 与本最小 FIX-01 dev_log：

- revision folding 必须先于 revision-mutable membership/filtering；
- population/coverage identity 必须与 Outcome measurement compatibility 解耦；
- mixed COMPLETE measurement versions 必须 deterministic fail closed；
- 重新确认 `source_manifest_id` 的 provenance/comparability 边界。

Production Python、tests、ORM、DB、migration、frontend、runtime、configuration、Accepted
SE-02A/B/C/PRE-01A-D1、`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md` 与 `main` 均不在
Scope。不得开始 SE-02D implementation 或自行 Human Accept。

## Repository Truth

- branch：`design/se-02d-d01-family-aggregation-expectancy`；
- FIX-01 starting HEAD / reviewed candidate：`1b2494c66e0c7623edf8a00d3b88f29627882771`；
- reviewed candidate parent / local main / origin main / live remote main：
  `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`；
- `BASELINE MISMATCH = NO`；design worktree clean before FIX-01；
- 原 session checkout 的既有 27 项 dirty status entries 未触碰。

## Root Cause

### D01-R1

原算法先读取“与 full aggregate key 相容”的 Evidence revisions，再 fold。由于 source、manifest、
Evidence contract 等字段可随 correction 改变，filter 可隐藏 predecessor/successor，并让 superseded
revision 残留旧 aggregate。

### D01-R2

原 full key 混合 Evidence population fields 与 Outcome-only contract/calculator/cost fields。
当 canonical Evidence 已成熟但 Outcome row 不存在时，不可能从不存在的 Outcome fields 得到 key，
从而无法可靠产生 `MISSING_OUTCOME` coverage membership。

### D01-R3

Repository 证明 `source_manifest_id` 是 caller/context-supplied immutable provenance，并进入
Capture Anchor/Evidence payload/hash；但没有 Accepted contract 证明不同 manifest 必然不可比较。
按 manifest `MUST SEPARATE` 会在 token 随 run/context 改变时人为碎片化长期 Expectancy。

## Contract Fix

1. pipeline 冻结为完整 visible Evidence chain validation/fold → canonical Evidence head → exact-horizon
   完整 Outcome chain validation/fold → canonical Outcome head/`NO_OUTCOME` → membership/coverage/
   measurement compatibility；不指定 SQL 物理实现。
2. `Population Key` 仅含 canonical Evidence head 可用的 family/version/instrument/market/source/
   Evidence-contract facts；与 `horizon` 共同拥有 coverage denominator。
3. canonical Outcome head 派生 `Measurement Signature`：Outcome contract、calculator、cost policy/model、
   Outcome source。它只防止 COMPLETE returns 跨语义混算，不拥有 coverage membership。
4. mixed canonical COMPLETE signatures 选择 Minimal Sufficient Candidate A：
   `INCOMPATIBLE_MEASUREMENT_SIGNATURES`，coverage 完整，headline economic statistics = NULL。
5. `source_manifest_id` 改为 `REPORT AS STRATIFICATION / PROVENANCE`。只有 Population Key、horizon、
   唯一 Measurement Signature 全相同且不是 post-hoc selection 时才可跨 manifest headline；必须
   报告 manifest counts/concentration。
6. 明确构造证明：canonical Evidence mature + exact-scope Outcome chain empty → `NO_OUTCOME` →
   `MISSING_OUTCOME`，进入同一 population/horizon mature denominator，不猜 calculator/cost version。

## Regression Boundary

- 每 logical Opportunity/fixed horizon 最多一个 canonical observation；
- Evidence/Outcome corrections 均不会 double count；
- missing/invalid/insufficient 不 silent drop；四 horizon 继续严格分离；
- headline 仍为 mean(`cost_adjusted_forward_return`)；
- K/D/K、Gate C、Live、historical-as-of blocker 与 no-implementation boundaries 不变。

## Verification

实际完成：

- live remote main = `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`，reviewed candidate
  remote = `1b2494c66e0c7623edf8a00d3b88f29627882771`，lineage check PASS；
- changed paths = 2，均为允许的 design/dev_log；unexpected/forbidden paths = 0；
- required pipeline/population/signature/missing proof/manifest markers = PASS；
- original D01 ten-invariant regression audit = PASS；
- forbidden `SE-02D = ACCEPTED/COMPLETE` claim = 0；candidate status = PASS；
- Markdown fences balanced，trailing whitespace = 0；
- staged `git diff --check` = PASS；
- production/test/schema/runtime diff = zero。

Backend pytest/runtime verification：`NOT APPLICABLE — DOCS ONLY / NO IMPLEMENTATION AUTHORIZED`。

## Remaining

本候选仍需 Independent Re-Review 与 explicit Human Acceptance。Historical revision-as-of、Gate C
experiment identity、durable regime identity 仍是既有 prerequisite；FIX-01 不修复或扩大这些边界。
