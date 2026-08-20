"""How much margin does the filter actually need, and what does it cost?

The first filter aimed the arm exactly at the boundary: the one-step constraint
permits h_next = 0, so every source of error (linearising a curved surface over a
33 ms hold, joint-limit clamping, guarding body origins instead of meshes) lands on
the wrong side of zero. Margin is how that error gets paid for.

Rather than pick a number that looks safe, sweep it and read the result. Too small
and adversaries still get in; too large and the arm is uselessly timid, so the sweep
reports both sides.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adversary import Lunger, Reacher, Seeker
from envelope import SafetyFilter, desk_envelope
from harness import Rig, run_episode

SCENE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "so101", "scene.xml")
HEAD = np.array([0.0, -0.30, 0.22])
BENIGN = np.array([0.18, 0.10, 0.12])
SEEDS = (0, 1, 2)


def main():
    max_speed = np.full(6, 5.5)
    rig = Rig(SCENE, control_hz=30.0)
    attacks = [Seeker(), Lunger()]

    print("%-10s %10s %14s %12s %10s" % (
        "margin_m", "breaches", "worst_clear_m", "task_reached", "brakes"))
    print("-" * 60)

    for margin in (0.000, 0.005, 0.010, 0.020, 0.030, 0.050, 0.080):
        env = desk_envelope(max_speed)
        env.margin = margin
        filt = SafetyFilter(env, control_dt=rig.control_dt)

        breaches = 0
        worst = float("inf")
        for policy in attacks:
            for seed in SEEDS:
                r = run_episode(rig, env, policy, HEAD, True, filt, seed=seed)
                breaches += int(r["violated"])
                worst = min(worst, r["min_clearance_m"])

        task = run_episode(rig, env, Reacher(), BENIGN, True, filt, seed=0)

        print("%-10.3f %10s %14.4f %12s %10d" % (
            margin,
            "%d/%d" % (breaches, len(attacks) * len(SEEDS)),
            worst,
            "yes @%.2fs" % task["reached_at_s"] if task["reached"] else "NO",
            filt.brake_events,
        ))

    print()
    print("Read it as: the smallest margin with 0 breaches AND the benign task still")
    print("reached is the operating point. If no row satisfies both, the filter design")
    print("is wrong, not the margin.")


if __name__ == "__main__":
    main()
