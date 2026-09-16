"""PRE-01B-I2 AdvisoryIngress core — implementation of the accepted D2 contract.

Design authority: ``docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md``
(ACCEPTED / COMPLETE, Human Acceptance CONFIRMED 2026-09-17).

The package boundary is deliberately narrow and encodes the contract's structural
separation rather than relying on convention:

* the Gate A advisory path is a **provenance-only** consumer. It has no handle, no
  callable and no constructor argument that could reach ``TradePlanManager``,
  ``persist_trade_plan``, ``SystemRiskGate``, ``PaperExecutionService``,
  ``G3Workflow``, or any Position/Account/Ledger/Protection mutation repository
  (D2 §11);
* the only database capability the advisory path may receive is a Host-owned
  ``AdvisoryDbFence`` — never a raw engine, a raw primary session factory or a second
  DSN (D2 §20.1 item 2, §24.4);
* the SE-02D aggregation projection is **not** a runtime dependency. Nothing in this
  package imports ``marketpulse.edge.aggregation_snapshot`` (D2 §23.2);
* activation defaults to ``DISABLED`` and I2 only wires ``DISABLED`` and
  ``GATE_A_SHADOW``. ``GATE_B_PAPER`` must fail closed at startup (D2 §22).

This module currently exposes the *foundation* layers only: the frozen vocabulary and
the deterministic identity/binding derivations. The durable runtime path (admission
writer, DB fence and lease registry, bounded ingress, shadow-safe consumer, recovery)
is not implemented yet — see ``dev_log`` for the candidate's exact state.
"""

from __future__ import annotations

__all__: list[str] = []
