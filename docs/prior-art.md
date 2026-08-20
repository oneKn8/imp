# Prior-art map

Swept 2026-08-20, four parallel research tracks, ~100 searches. Rule applied: zero search
hits never means novel; every vein names its nearest neighbor. This file is the honest
ledger of what is taken, what is converging, and what is open. If you know something that
belongs here, open an issue: killing a claim cheaply is a contribution.

## The safety architecture: taken, converging, open

### Taken (cannot be claimed, only built upon)

| Work | What it owns | Layer / threat model |
|---|---|---|
| [Simplex](https://ieeexplore.ieee.org/document/936213) (Sha 2001) and [S3A: Secure System Simplex](https://arxiv.org/pdf/1202.5722) (2012) | Trusted safety core on isolated hardware keeping the plant safe even when the main controller is fully compromised. The architecture pattern, 14 years old. | Below-host / adversarial |
| [NASA Safeguard](https://ntrs.nasa.gov/citations/20160012239) ([US10490088](https://patents.google.com/patent/US10490088)) | Independent hardware geofence/speed enforcement below an untrusted autopilot, formally verified, shipped. The drone instantiation. | Below-host / untrusted autopilot |
| [PX4 flight termination](https://docs.px4.io/main/en/advanced_config/flight_termination.html) | Open below-host authority pattern (autopilot MCU vs offboard computer), drones only. | Below-host / errant offboard |
| [NVIDIA Halos Safety Island](https://developer.nvidia.com/blog/inside-nvidia-halos-for-robotics-a-full-stack-functional-safety-system-for-physical-ai/) (2026) | Dedicated on-SoC safety island between AI and actuation. Right layer, fault model only (IEC 61508), OEM-gated, closed. | Below-host / faults |
| [OpenCxMS SASM](https://opencxms.com/) (Feb 2026) | 16 provisional patents (~156 claims) on "hardware enforcement the AI cannot override." No hardware, no spec, no repo, no data as of Aug 2026. The idea is paper-staked; the proof is not. S3A predates the broad claims by 14 years. | Claimed below-host / malice |
| [MDPI Electronics 14(24):4909](https://www.mdpi.com/2079-9292/14/24/4909) (Dec 2025) | FPGA hardware MITM on a Dynamixel-class half-duplex servo bus, published as an attack; countermeasure is timing-based interposer detection. Proves the interposition mechanism on this bus class, and obliges any defensive interposer to be attested rather than covert. | Interposer as attacker |
| [Dynamixel Lock register](https://emanual.robotis.com/docs/en/dxl/protocol2/) + Feetech protection registers | In-actuator below-host enforcement: static limits locked until power cycle, overload/thermal shutdown. The anchor a reviewer raises against broad "hardware limits" claims. | In-servo / accidents |
| Industrial dual-channel safety: [ISO 10218:2025](https://www.iso.org/standard/73933.html), [UR safety board](https://www.universal-robots.com/articles/ur/safety/safety-faq/), PILZ/SICK, [US4807153](https://patents.google.com/patent/US4807153) (1989) | Independent safety channel below the process controller, PLd Cat 3. Certified, closed, expensive, configured from the (trusted) host, fault model. | Below-application / faults |
| [CAN bus firewalls](https://www.researchgate.net/publication/365257691_Survey_on_CAN-Bus_Packet_Filtering_Firewall) | Inline adversarial packet filtering on a control bus (automotive). Syntactic rules, no physical-envelope semantics. | Inline hardware / malice |

### Converging right now (same niche, different trust boundary)

| Work | What it does | The gap it leaves |
|---|---|---|
| [HappyEthan/metal-safety](https://github.com/HappyEthan/metal-safety) (2026-08-11) | Bus-level safety interposer daemon for a hobby arm: fail-closed CAN gateway, workspace SDF envelope, keep-outs, jerk limits, stall detection, event log. | Host-side daemon on the same OS as the policy it filters; a compromised host bypasses or kills it. Its README admits a dead daemon is indistinguishable from a healthy one. |
| [clay-good/invariant](https://github.com/clay-good/invariant) (active 2026) | Cryptographic command-validation firewall between AI models and actuators; signed authority chain, COSE audit log, Lean 4 core. | Software/protocol infrastructure requiring adoption; not a transparent physical retrofit. |
| [productstein/antihero](https://github.com/productstein/antihero) (Mar 2026, dormant) | Behavioral action firewall + hash-chained audit, LeRobot adapters. | Pure host-side Python. |
| [LeRobot safety story](https://github.com/huggingface/lerobot/issues/1483): max_relative_target, [PR #4240/#4241](https://github.com/huggingface/lerobot/pull/4240), [URML RFC #3734](https://github.com/huggingface/lerobot/issues/3734) | Host-side clamps and a pending safety processor step. | All inside the process the threat model distrusts. The ecosystem's official e-stop is unplugging USB. No hardware layer exists or is proposed. |

### Host-software guardrails for LLM robots (the layer this project distrusts)

[RoboGuard](https://arxiv.org/abs/2503.07885) (its "root-of-trust LLM" runs on the
jailbreakable computer), ["Plug in the Safety Chip"](https://arxiv.org/abs/2309.09919)
(contains no chip), [KnowNo](https://arxiv.org/abs/2307.01928), [DeepMind
ASIMOV/constitutions](https://asimov-benchmark.github.io/), shielded RL, [SPARK](https://arxiv.org/abs/2502.03132).
All enforcement co-resident with the attacker.

### Attacks (reused here as the adversary generator)

[RoboPAIR](https://arxiv.org/abs/2410.13691), [BadRobot](https://arxiv.org/abs/2407.20242),
[ANNIE](https://arxiv.org/abs/2509.03383) (ISO/TS-15066-grounded violation taxonomy, adopted
as this project's measurement vocabulary), [Unitree Go1 backdoor
CVE-2025-2894](https://www.securityweek.com/undocumented-remote-access-backdoor-found-in-unitree-go1-robot-dog/)
(hosts are empirically untrusted). No attack paper proposes hardware containment in its
defense section.

### Open (verified by sweep, 2026-08-20)

1. The conjunction: physical interposition on Feetech/Dynamixel half-duplex TTL + transparent
   retrofit (no host, protocol, or servo changes) + kinematic state reconstruction from
   passive traffic + inline semantic enforcement within half-duplex timing + adversarial host
   threat model + signed logging in the trusted device.
2. The measurement: no published adversarial soak of a physical arm, no enforcement-latency
   distributions, no zero-violation-over-time methodology, at any scale. 2026 surveys
   ([Embodied AI security SoK](https://arxiv.org/abs/2602.17345), [physical risk control
   survey](https://arxiv.org/abs/2505.12583)) name the gap without filling it.
3. CBF-on-MCU for a manipulator, end to end. Embedded QP is precedented
   ([TinyMPC](https://arxiv.org/html/2403.18149), DAQP) but nobody has published the
   manipulator safety-filter version on microcontroller silicon.
4. The configuration-desync attack (host legitimately rewrites servo EEPROM baud/ID/response
   delay to blind an interposer) and attested interposer liveness. Unaddressed anywhere,
   because no prior work combined a hostile host with a defensive bus interposer.

## The robot body: what is reused outright

| Component | Choice | Source |
|---|---|---|
| Arm | SO-101 (LeRobot) | [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100), [docs](https://huggingface.co/docs/lerobot/so101) |
| Gripper | Parallel-jaw mods (ALOHA-style rack-and-pinion, 105 mm opening) | [ggao50](https://github.com/ggao50/SO101-Parallel-Gripper), [roboninecom](https://github.com/roboninecom/SO-ARM100-101-Parallel-Gripper) |
| Soft fingers | UMI 95A TPU ribbed | [universal_manipulation_interface](https://github.com/real-stanford/universal_manipulation_interface) |
| Policies | ACT (~50 demos/task), SmolVLA-450M | [ACT](https://huggingface.co/docs/lerobot/act), [SmolVLA](https://huggingface.co/blog/smolvla) |
| Perception | Grounding DINO + SAM, proven on-desk by [Tabletop HandyBot](https://github.com/ycheng517/tabletop-handybot) | |
| Teleop/record plumbing | [phosphobot](https://github.com/phospho-app/phosphobot) | |
| Bus protocol ground truth | [Feetech protocol manual](https://files.seeedstudio.com/wiki/robotics/Actuator/feetech/Communication_Protocol_Manual.pdf), [LeRobot feetech driver](https://github.com/huggingface/lerobot/tree/main/src/lerobot/motors/feetech) | |
| Envelope math | Kinematic CBFs ([Singletary and Ames](http://ames.caltech.edu/singletary2021safety.pdf)), ISO-encoding via [arXiv 2606.13203](https://arxiv.org/abs/2606.13203) | |

Why no dexterous hand: [ALOHA](https://arxiv.org/abs/2304.13705) deliberately reduced to
parallel jaws and then demonstrated the hard end of desk manipulation with them; the
[in-hand manipulation survey](https://arxiv.org/pdf/2401.07915) shows parallel jaws lack only
in-hand reorientation, which regrasp-via-table covers on a desk. If ever needed:
[LEAP Hand v2](https://v2.leaphand.com/) is $200 now.

## The personality layer: theory exists, code mostly does not

| Work | Status |
|---|---|
| [Reachy Mini emotion/dance libraries](https://huggingface.co/datasets/pollen-robotics/reachy-mini-emotions-library) (Apache 2.0) | Reused; JSON trajectory + audio format retargeted from head/antennas to 6-DOF arm |
| [ELEGNT](https://machinelearning.apple.com/research/elegnt-expressive-functional-movement) (Apple 2025) | Functional+expressive motion framework, user-validated. No code released; reimplemented here |
| [GenEM](https://arxiv.org/abs/2401.14673) | LLM-to-expressive-behavior recipe. No code released |
| [MachinaScript](https://github.com/babycommando/machinascript-for-robots) | Personality-as-spec driving movement, hobby-grade |

Category check: no shipping robot both manipulates and emotes.
[Reachy Mini](https://huggingface.co/blog/reachy-mini) is head-only; [Tabletop
HandyBot](https://github.com/ycheng517/tabletop-handybot) has no expressive layer; [Lenovo AI
Workmate](https://www.engadget.com/ai/lenovo-concept-robot-ai-workmate-mwc-2026-230159746.html)
(MWC 2026 concept) moves only its own camera; Apple's ELEGNT shipped nothing.
