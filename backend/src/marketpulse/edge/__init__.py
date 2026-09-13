"""SE-02 Edge layer.

* :mod:`marketpulse.edge.models`, :mod:`marketpulse.edge.identity`,
  :mod:`marketpulse.edge.hashing`, :mod:`marketpulse.edge.repository` -- the
  accepted SE-02A contracts plus their append-only persistence;
* :mod:`marketpulse.edge.capture` -- SE-02B G2 opportunity capture;
* :mod:`marketpulse.edge.attribution` -- SE-02B append-only attribution lineage;
* :mod:`marketpulse.edge.forward` -- SE-02C pure Forward Outcome Calculator;
* :mod:`marketpulse.edge.forward_service` -- SE-02C Forward BBO path capture,
  durable due discovery and the bounded evaluation API.

Still absent by design (SE-02D): expectancy, family aggregation and
KEEP / DOWNWEIGHT / KILL.
"""
