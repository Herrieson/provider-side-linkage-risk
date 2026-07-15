# Mitigation Implications From Linkage-Surface Controls

Status: supplementary planning note, excluded from the AAAI submission claim set.

The paper does not propose or evaluate a defense. Its strict-removal and turn-delta controls instead
show that two leakage surfaces must be treated separately:

- stable workspace, repository, owner, and internal-domain anchors;
- retransmitted dialogue and tool state that preserve workflow continuity.

On held-out Open-SWE, strict anchor removal reduces project/owner F1 to zero. It does not remove
exact cumulative-message nesting, which remains at session F1 1.000. Combining strict removal with
turn-delta requests reduces CARP and Hybrid session F1 to 0.016. These are attack-surface stress
tests, not task-utility or deployment measurements.

The bounded design implications are therefore:

- protocol metadata stripping should not be described as content de-identification;
- privacy gateways should minimize or abstract stable task namespaces where operationally possible;
- cumulative dialogue and tool outputs require separate retention and retransmission policies;
- provider-side raw-log retention, access, and secondary clustering should be governed directly.

The repository retains exploratory redaction/minimization artifacts for completeness, but the main
paper does not use their utility proxies, present a defense research question, or claim that any
transformation solves the privacy problem.
