# imp

A desk robot with an untrusted brain and a hardware conscience.

imp is a small robot arm that lives on my desk. In useful mode it hands me tools, grabs my
phone, presses buttons, and moves cables. In unhinged mode it steals the phone back when I
doomscroll, points at me when my build fails, and generally behaves like a goblin. The
personality is allowed to be unhinged because of the part of this project that actually
matters: **muzzle**, a trusted hardware firewall that sits physically between the robot's
software and its motors, and makes the arm incapable of leaving its safety envelope no matter
what the software does.

## Thesis

An untrusted, even adversarial intelligence can safely hold full creative control of a
physical robot when, and only when, the physical envelope is enforced *below* the host, by a
transparent hardware interposer the software cannot reach. The goblin personality is not
decoration: it is the adversarial load generator that soak-tests the firewall every day.

## Why this needs to exist

- LLM-driven robots are here, and every published guardrail for them (RoboGuard, Safety Chip,
  constitution critics) runs as software on the same computer as the planner it distrusts. If
  the host is compromised, the guardrail is too.
- Robot hosts are already empirically untrusted: the Unitree Go1 shipped with a remote-access
  backdoor (CVE-2025-2894) into 1,900+ robots, including university labs.
- The open-source arm ecosystem (LeRobot SO-101) has no hardware safety layer at all. The
  official emergency stop is unplugging the USB cable.
- As of August 2026 there is no published adversarial soak test of a physical arm, no
  enforcement-latency data, and no zero-violation-over-time methodology, at any scale,
  industrial included. Producing that data is the point of this project.

## Architecture

```
 UNTRUSTED                                        TRUSTED
+--------------------------------------+   +-------------------+   +--------------+
| host computer                        |   | muzzle            |   | SO-101 arm   |
|  LLM planner / learned policies      |-->|  ESP32-C3 inline  |-->|  6x Feetech  |
|  goblin personality engine           |USB|  on the 1 Mbps    |bus|  STS3215     |
|  (assumed hostile by design)         |   |  half-duplex bus  |   |              |
+--------------------------------------+   +-------------------+   +--------------+
```

muzzle parses every packet on the servo bus, reconstructs the arm's kinematic state from
traffic alone, and rewrites or drops anything that would violate the envelope: keep-out zones
(my face, my monitors), joint speed limits, torque and contact budgets. It also firewalls
configuration writes (a hostile host could otherwise rewrite servo baud rates or IDs to
desynchronize it), proves its own liveness (a dead firewall must be detectable, not silent),
and keeps a signed flight-recorder log. Transparent retrofit: no changes to the LeRobot
stack, the protocol, or the servo firmware.

## Claims this project makes (each one falsifiable)

1. Kinematic envelope enforcement can run on a microcontroller, inline on a live 1 Mbps
   Feetech bus, transparently to an unmodified LeRobot stack.
2. An adversarial policy can operate a physical arm for hours with zero envelope violations,
   while legitimate task completion stays useful. Reported with enforcement-latency
   distributions and a standard violation taxonomy. If the filter is so conservative it kills
   task success, that is a reported negative result, not a footnote.
3. The configuration-desync attack surface can be closed in-protocol, and firewall liveness
   can be attested.
4. A desk robot can be both genuinely useful (manipulation) and genuinely characterful
   (expressive motion). No shipping robot does both as of August 2026.

## Standing on

The arm is a LeRobot SO-101; policies via LeRobot ACT/SmolVLA. The safety architecture
descends from Simplex/S3A (Sha 2001; Mohan and Bak 2012) and NASA Safeguard's below-host
enforcement pattern. Envelope math from kinematic control barrier functions (Singletary and
Ames). Violation taxonomy from the ANNIE benchmark. Expressive motion format from Pollen's
Reachy Mini emotion libraries (Apache 2.0). What is new here is the conjunction and the
measurements, and the prior-art map that says so honestly: see [docs/prior-art.md](docs/prior-art.md).

## Build log

Weekly entries in [log/](log/). Started 2026-08-20. Kills, dead ends, and negative results
get logged with the same care as wins.

## Safety note

This is safety *research* on a 1 kg-class hobby arm, not a certified safety device. Do not
point any of this at anything that can hurt someone.
