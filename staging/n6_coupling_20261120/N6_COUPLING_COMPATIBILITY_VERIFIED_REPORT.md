# N6-2 new payment coupling compatibility — source-verified results

**Scope:** only the new N5/N6 payment/material coupling. The already certified original Test 3 model has NOT been recertified or modified.
Public [N6-2 workflow](https://github.com/ALRIER/On_the_public_impossibilityII/actions/runs/44821050420) and [immutable Release](https://github.com/ALRIER/On_the_public_impossibilityII/releases/tag/n6-public-coupling-compatibility-44821050420-a1).

## Tested baseline behavior

- 72 no-shock 104-sector trajectories, 1296 monthly records, 36 static payment-technology compatibility checks; two seeds.
- Engineering-only reference ratio below 90% in **60/72** cases (90% is not a Test 3 scientific threshold).
- Financial edge-capacity shortfalls occurred in **48/72** cases.
- Max physical/cash accounting residual: **5.329e-14**; no-friction topology placebos: **8**.
- The original eight parameter vectors and corresponding macro targets remain intact, but the new public engine does not accept or implement these validated Test 3 state controls; **8/8 new coupling parity is not certified**.

## Output by payment mode

| Payment mode | No-shock cases | Late realized/planned output (mean) | Illustrative reference >= 90% |
|---|---:|---:|---:|
| direct | 24 | 0.56% | 0/24 |
| two_hop | 24 | 0.56% | 0/24 |
| unrestricted_payment_placebo | 24 | 50.17% | 12/24 |

## Strict necessary supplier-payment support and throughput test

For each positive technological input requirement, the current coupled kernel requires an eligible payment route, plus enough financed monthly settlement. With a hard non-substitutable Leontief minimum, even a very small unsupported input can stop a buyer sector. The following table is a **pre-shock necessary-condition audit**, not evidence that caps alone explain every dynamic outcome.

| Mode | Frozen payment arm | Missing technological payment edges | Buyers missing an essential route | Buyers below ex ante input requirement | Direct capacity-short edges | Eligible technological mass |
|---|---|---:|---:|---:|---:|---:|
| direct | inherited | 0 | 0 | 103 | 8274 | 100.000000% |
| direct | reconstructed_00 | 1548 | 103 | 103 | 4334 | 99.863690% |
| direct | reconstructed_31 | 1474 | 103 | 103 | 4607 | 99.872778% |
| two_hop | inherited | 0 | 0 | 103 | 8274 | 100.000000% |
| two_hop | reconstructed_00 | 81 | 74 | 103 | 4334 | 99.999893% |
| two_hop | reconstructed_31 | 78 | 74 | 103 | 4607 | 99.999944% |
| unrestricted_payment_placebo | inherited | 0 | 0 | 0 | 0 | 100.000000% |
| unrestricted_payment_placebo | reconstructed_00 | 0 | 0 | 0 | 0 | 100.000000% |
| unrestricted_payment_placebo | reconstructed_31 | 0 | 0 | 0 | 0 | 100.000000% |

## N6-2 compatibility decision and next code change

**Public engineering diagnostics ran successfully. The new coupling FAILS the compatibility-readiness gate** because its no-shock economy collapses under direct/two-hop payment routing, and the eight authentic legacy economic anchors are not wired into the new state transitions. This does NOT revisit or invalidate the original Test3 economy.

**Next implementation:** reuse the existing opt-in original Test3 `n4_coupling` integration seam for a source-faithful baseline. Keep original ten parameter/state equations intact. Introduce a *separate* bilateral purchase/settlement layer with bank routing, funded credit and explicit edge-capacity constraints, preserving full technological input requirements and goods/money identities. Test no-shock baseline before shock sensitivity; do not optimize any engineering knobs to manufacture beneficial shock differences. Repeat reference comparison across eight anchors, independently.

Q2 original six bands, Q3 historical reference window and Q4 original failed targets remain untouched. No new economic benefit or reviewer closure certified.

Original source Release archive SHA256: `c547a93a772f1bc0ab7f4feca38f9650a21edbece341ca7e7385db992369c067`; archive 36173 bytes, 4 original Release assets, 3 source/workflow snapshots.
