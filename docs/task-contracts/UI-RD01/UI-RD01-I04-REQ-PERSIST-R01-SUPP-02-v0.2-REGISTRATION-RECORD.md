# SUPP-02 v0.2 TaskContract Registration Record

## Identity and immutable artifacts

- Control task: `UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-TC-FORMALIZE-INTEGRATE-01 v0.1`
- Contract ID: `UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-TC-FORMALIZE-INTEGRATE-01-v0.1-candidate.1`
- Canonical contract: `docs/task-contracts/UI-RD01/UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-v0.2.task-contract.json`; SHA-256 `f2b136b2f94cf662a2043213c5cd88750ac5a7c9ea9c4be6102291105934d8aa`; Git blob `939ed78a103011651fd3e4e8e70364976aeb8cac`; 10115 bytes.
- Readable projection: `docs/task-contracts/UI-RD01/UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-v0.2.task-contract.md`; SHA-256 `00c64eb3b2a5c2dbd3b0e1a382c26dabcf07cc9776317ea1821d317b28950330`; Git blob `d080cb737758fd98d48c2e8e38c789685aa4a730`; 1815 bytes.
- Independent R01 review result: `docs/task-contracts/UI-RD01/reviews/UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-TC-FORMALIZE-R01-RESULT-v0.1.md`; SHA-256 `04de8534dcbf169d36a484f852a5effdef747770b5596bad6564c625641294dd`; 13884 bytes; verdict `CONTRACT_MATERIALIZATION_REVIEW_PASS / READY_FOR_CONTROLLED_INTEGRATION_DESIGN`; blocking findings `0`. The persisted file is byte-exact to the supplied `RESULT.md`.
- Reviewed materialization candidate: `9a7e8aec026381a941246e5d0ad046e938636134`; tree `a062a9d28ff9c49393e1c621e921baae4d70291a`; sole parent and bound MarketPulse main `8c94ea338f500e2ea4dd2f8a5ccc81a65502468e`.
- Integration carrier: branch `codex/ui-rd01-i04-supp02-tc-integrate-01`, created directly from the exact reviewed candidate. Its full commit identity is the exact branch tip reported by the controlled integration result after commit and remote readback.

## Authorization and effective lifecycle

- Human authorization: `WRITE_MAIN GRANTED for UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-TC-FORMALIZE-INTEGRATE-01, exact reviewed candidate 9a7e8aec026381a941246e5d0ad046e938636134`.
- Authority scope is one normal, non-force fast-forward of MarketPulse `main` to this exact single-parent carrier. No other main mutation is authorized.
- Registration target: `FORMALLY_REGISTERED_ON_MAIN`, conditional on successful exact-carrier integration and post-integration identity checks. Until then this record is a candidate carrier record, not an assertion that main has changed.
- Canonical JSON and Markdown contract bytes are unchanged. This registration does not amend their candidate-time internal state snapshot.
- `SUPP-02 v0.2` review remains `NOT STARTED` unless and until the separate post-integration receipt gate passes. Dispatch remains blocked pending that receipt.
- Requirement Freeze, R01 persistence closure, Implementation Authorization, Implementation, and code/schema/runtime changes are `NOT PERFORMED` and are not authorized by this registration.
- Next legal gate: `UI-RD01-I04-REQ-PERSIST-R01-SUPP-02-TC-FORMALIZE-INTEGRATION-V01` read-only post-integration receipt. Only its PASS can make the contract current for dispatch.