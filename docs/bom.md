# Bill of materials and buying strategy

Prices verified live 2026-08-20 (Bambu US store, Amazon US, SO-ARM100 official BOM).
Ship-to: Dallas 75252.

## The finding that shapes the order

The official SO-ARM100 BOM prices STS3215 servos at **$13.89 each via Alibaba**. Amazon
charges **$25.64-29.99 each** for the same servo, delivered tomorrow. For the six follower
servos that is $83 versus $180.

So: buy 2 servos at Amazon speed to start the muzzle bench THIS WEEK, and put the bulk
order on the slow cheap channel where it arrives while the arm parts are still printing.
Nothing sits idle either way.

## Official SO-ARM100 BOM totals (source of truth)

https://github.com/TheRobotStudio/SO-ARM100 — "Sourcing Parts"

| Config | US total | Contents |
|---|---|---|
| **One follower arm** | **$121.94** | 6x STS3215 7.4V 1/345 ($13.89 ea), motor control board $10.60, USB-C cables $7, PSU $10, table clamps $5, screwdriver set $6 |
| Two arms (follower + leader, enables teleop) | $229.88 | adds 6 leader servos: 3x 1/147, 2x 1/191, 1x 1/345, plus 2nd board/PSU |

Servo voltage: the BOM says **7.4V is sufficient**; 12V (30 kg·cm) is the optional upgrade
and needs a 12V 5A+ PSU instead of 5V. **The leader arm is always 7.4V.** Follower servos are
all 1/345 gear ratio. Going 7.4V keeps us on the documented, best-supported path; swapping to
12V is a later improvement if torque proves short.

## Print requirements (verified)

- Material PLA+, 0.4 mm nozzle at 0.2 mm layer height, **15% infill**
- **Bambu Lab A-series is on the official tested-printer list**
- A 180x180 pre-arranged plate exists (A1 mini would fit), but 256³ leaves headroom for
  enclosures, jigs, and the goblin hand tool-head

## Order 1 — this week (start the bench, start printing)

| Item | Price | Where | Notes |
|---|---|---|---|
| Bambu Lab A1 (plain, NOT Combo) | $299.00 | us.store.bambulab.com/products/a1 | 256×256×256, free shipping, ships 1-3 days. Combo (+$100) only adds multi-color AMS, not needed for robot parts |
| Filament bundle at checkout | ~$26-53 | same page | 40% off only when bundled with printer: PLA Basic $13.79, PETG Basic $12.59, or 4-spool starter pack $52.99 |
| 2x STS3215 7.4V servo | ~$46-51 | Amazon (2-pack $45.98, or singles $25.64) | The muzzle bench needs only two: one talks, one is the victim |
| USB logic analyzer 24 MHz 8ch | $12.69 | Amazon (HiLetgo) | 24 MHz vs a 1 Mbps bus = 24x oversampling, plenty |
| **Subtotal** | **~$385-410** | | |

Student discount: Bambu advertises up to 10% off printers for students, plus a back-to-school
2x-credits promo ending Aug 31 2026. Worth applying with the UTD email before checkout;
roughly $30 off the A1.

## Order 2 — same day, slow channel (bulk servos)

| Item | Qty | Unit | Total |
|---|---|---|---|
| STS3215 7.4V 1/345 (C001) via Alibaba | 4-6 | $13.89 | $56-83 |
| Motor control board | 1 | $10.60 | $10.60 |
| Power supply | 1 | $10.00 | $10.00 |
| Table clamps, screwdriver set | 1 | $11 | $11 |

Arrives in ~2-4 weeks, which is exactly when the printed parts will be ready. Buy 6 (not 4)
if the Alibaba minimum makes it cheap; spares are recommended by every kit seller anyway.

Fallback if Alibaba friction is not worth it: Amazon 2-packs at $45.98, or the Seeed
SO-ARM101 Pro servo kit at $277.99 (covers both arms).

## Later, not now

- Leader arm servos (~$85) — only needed when we start recording ACT demonstrations. The
  entire muzzle research phase runs on the follower alone.
- Parallel-jaw gripper upgrade — printable, servo already counted
- Goblin hand tool-head — 2-3 small servos, ~$50
- Wrist camera (RealSense/webcam) — perception phase

## Total to be running

~$385-410 now for printer, bench, and first prints; ~$90 more on the slow channel for the
rest of the arm. Against a $278 pre-made kit, the delta buys a permanent printer.
