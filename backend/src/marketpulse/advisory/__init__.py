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

The package exposes the frozen vocabulary/identity plus the disabled-safe admission,
fence, bounded ingress, fake-provider worker and durable recovery primitives. Runtime
activation remains disabled; these components are exercised only through injected,
disposable-PostgreSQL tests until a separate activation gate authorizes composition.
"""

from __future__ import annotations

__all__: list[str] = []
