# N5 controlled financial-shock mechanism diagnostic (Nov 20, 2026)

These observations are from engineering-only coupled simulations with the frozen public 104-sector physical technology, **not** from eight certified legacy economic anchors.
Sources: [forward-input-coverage release](https://github.com/ALRIER/On_the_public_impossibilityII/releases/tag/n5-public-forward-coverage-44758150356-a1) and [delivery-shock release](https://github.com/ALRIER/On_the_public_impossibilityII/releases/tag/n5-public-delivery-channel-44758591721-a1).
All case rows, including null and adverse outcomes, remain in the original immutable release archives.

## Original 104-sector economic differences: legacy capacity shock

| Ordering rule | Shock output DID | Shock real-value-added DID | Shock consumption DID | Value-added level difference |
|---|---:|---:|---:|---:|
| legacy_stock_only | +0.00000000 | +0.00000000 | +0.00000000 | -0.04563968 |
| forward_input_coverage | +0.00000000 | +0.00000000 | +0.00000000 | -0.00492672 |

## Original 104-sector paired delivery-shock contrasts

All contrasts are reconstructed (or explicitly nonadmissible diagnostic) minus inherited. Positive/negative DID signs are not evidence of overall network superiority.

| Design | Policy | Arm | Admissible original structure? | Output DID | Value added DID | Consumption DID | Value added shocked level difference |
|---|---|---|---|---:|---:|---:|---:|
| early | legacy_stock_only | reconstructed_0 | Yes — original | +0.00000000 | +0.00000000 | -0.00022169 | -0.04563968 |
| early | legacy_stock_only | diagnostic_full_payment | No — diagnostic control | -0.00095187 | -0.00102248 | -0.00499947 | +0.49937625 |
| early | legacy_stock_only | diagnostic_block_one_direct_edge | No — diagnostic control | -0.00074436 | -0.00088142 | -0.00458084 | +0.49301218 |
| early | forward_input_coverage | reconstructed_0 | Yes — original | -0.01426201 | -0.00926672 | -0.00096626 | -0.01419344 |
| early | forward_input_coverage | diagnostic_full_payment | No — diagnostic control | -0.01154933 | -0.00788920 | -0.01878257 | +0.38022748 |
| early | forward_input_coverage | diagnostic_block_one_direct_edge | No — diagnostic control | -0.01426201 | -0.00926672 | -0.01908335 | +0.37723010 |
| later | legacy_stock_only | reconstructed_0 | Yes — original | +0.00000000 | +0.00000000 | -0.00061388 | -0.15546489 |
| later | legacy_stock_only | diagnostic_full_payment | No — diagnostic control | -0.00728632 | -0.00519459 | -0.00219557 | +1.59988108 |
| later | legacy_stock_only | diagnostic_block_one_direct_edge | No — diagnostic control | -0.02731439 | -0.01842658 | -0.01806446 | +1.58482128 |
| later | forward_input_coverage | reconstructed_0 | Yes — original | +0.00000000 | +0.00000000 | +0.00000000 | -0.03543909 |
| later | forward_input_coverage | diagnostic_full_payment | No — diagnostic control | +0.00335996 | +0.00192790 | +0.00664125 | +1.81944833 |
| later | forward_input_coverage | diagnostic_block_one_direct_edge | No — diagnostic control | +0.00306121 | +0.00201079 | +0.00445486 | +1.81560138 |

## Audit and limitations

- Synthetic forward-coverage positive-control nonzero shock contrast: **True**.
- Original 104-sector delivery-shock contrasts with nonzero output/VA/consumption DID: **3 / 4**.
- Nonadmissible topology diagnostic nonzero contrasts: **8** (not candidates for Q2).
- Frozen A unchanged; periodic stock, goods and monetary accounting residuals below 1e-9; zero-financial-friction placebo passed.
- Sample sizes are small and deterministic; no independent seed-based economic intervals or external empirical calibration.
- Both new options are opt-in. The historical order policy and capacity shock are still the defaults.
- Ten legacy parameters and eight economic anchors have NOT been mapped and validated.
- Q1–Q4 original decisions and targets remain unchanged, Q5 deferred, and full ML/ABM confirmation blocked.

## Required scientific gate

Verify the original legacy-model parameter-to-state transition mapping for all eight anchors; independently certify no-shock macro parity, calibration, shock timing and 1995–2023 period semantics; then preregister structurally admissible network comparisons with fresh seeds. This report is not evidence of journal-ready scientific closure.
