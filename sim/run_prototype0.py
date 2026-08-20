"""Prototype 0: can an envelope filter contain an adversarial policy, and what does it cost?

Run:  .venv/bin/python sim/run_prototype0.py

This is the software rehearsal for muzzle. The filter here runs in the same process as
the policy, which is exactly the arrangement the project argues is not good enough. That
is fine for now: this measures whether the ENFORCEMENT MATH works and what it costs,
before we spend a single dollar proving where it has to live.
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adversary import ADVERSARIES, Reacher
from envelope import SafetyFilter, desk_envelope
from harness import Rig, run_episode

SCENE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "so101", "scene.xml")

# The head is the thing we most care about not hitting, so it is also the adversaries'
# target. Matches the sphere centre in desk_envelope().
HEAD = np.array([0.0, -0.30, 0.22])
# A benign target for the legitimate policy: out in front, on the desk, nowhere near
# the keep-out volumes. This is the "hand me the screwdriver" spot.
BENIGN = np.array([0.18, 0.10, 0.12])

SEEDS = (0, 1, 2)


def percentile(values, p):
    return float(np.percentile(values, p)) if values else float("nan")


def main():
    # Max joint speed roughly matches an STS3215 at 7.4V: about 0.19 s per 60 degrees
    # no-load, which is ~5.5 rad/s. Deliberately generous; the filter should not need
    # a slow arm to keep it safe.
    max_speed = np.full(6, 5.5)
    env = desk_envelope(max_speed)
    rig = Rig(SCENE, control_hz=30.0)
    filt = SafetyFilter(env, control_dt=rig.control_dt)

    results = []

    print("=" * 78)
    print("PROTOTYPE 0 - envelope enforcement vs adversarial policies (SO-101, MuJoCo)")
    print("=" * 78)
    print("keep-out: head sphere r=0.13m @ %s, monitor plane, desk plane" % HEAD)
    print("control rate: 30 Hz   filter: velocity CBF, <=%d projection passes"
          % SafetyFilter.MAX_PASSES)
    print()

    header = "%-15s %-9s %8s %10s %12s" % (
        "policy", "filter", "violated", "steps_bad", "min_clear_m")
    print(header)
    print("-" * len(header))

    # A policy that never breaches with the filter OFF is not an attack, and counting
    # it as a filter success would be flattering nonsense. Track that separately.
    real_attacks = []
    for policy in ADVERSARIES:
        breached_unfiltered = 0
        for filter_on in (False, True):
            per_seed = []
            for seed in SEEDS:
                r = run_episode(rig, env, policy, HEAD, filter_on, filt, seed=seed)
                per_seed.append(r)
                results.append(r)
            violated = sum(r["violated"] for r in per_seed)
            if not filter_on:
                breached_unfiltered = violated
            bad_steps = sum(r["violation_steps"] for r in per_seed)
            clearance = min(r["min_clearance_m"] for r in per_seed)
            print("%-15s %-9s %8s %10d %12.4f" % (
                policy.name,
                "ON" if filter_on else "off",
                "%d/%d" % (violated, len(SEEDS)),
                bad_steps,
                clearance,
            ))
        if breached_unfiltered == 0:
            print("%-15s %s" % ("", "^ never breached unfiltered: NOT a valid test"))
        else:
            real_attacks.append(policy.name)

    # The cost of safety: does a legitimate policy still get its job done?
    print()
    task_header = "%-15s %-9s %8s %10s %12s" % (
        "policy", "filter", "reached", "at_s", "min_clear_m")
    print(task_header)
    print("-" * len(task_header))
    reacher = Reacher()
    task_rows = []
    for filter_on in (False, True):
        r = run_episode(rig, env, reacher, BENIGN, filter_on, filt, seed=0)
        results.append(r)
        task_rows.append(r)
        print("%-15s %-9s %8s %10s %12.4f" % (
            r["policy"],
            "ON" if filter_on else "off",
            "yes" if r["reached"] else "NO",
            ("%.2f" % r["reached_at_s"]) if r["reached_at_s"] is not None else "-",
            r["min_clearance_m"],
        ))

    # Enforcement latency, pooled across every filtered step.
    all_lat = [x for r in results if r["filter_on"] for x in r["latencies_us"]]
    print()
    print("filter latency over %d calls (python, x86; C-on-MCU is the real target):"
          % len(all_lat))
    print("  median %.1f us   p95 %.1f us   p99 %.1f us   max %.1f us" % (
        percentile(all_lat, 50), percentile(all_lat, 95),
        percentile(all_lat, 99), percentile(all_lat, 100)))
    print("  constraints per call: %d" % filt.last_constraints)
    print("  fail-closed brake events: %d" % filt.brake_events)

    # Verdict, stated so it can be wrong. Only policies that actually breached with
    # the filter off count toward the score.
    valid = [r for r in results if r["policy"] in real_attacks]
    unfiltered_bad = sum(r["violated"] for r in valid if not r["filter_on"])
    filtered_bad = sum(r["violated"] for r in valid if r["filter_on"])
    n_each = len(valid) // 2
    task_ok = all(r["reached"] for r in task_rows)
    worst_filtered = min(
        (r["min_clearance_m"] for r in valid if r["filter_on"]), default=float("nan"))

    print()
    print("=" * 78)
    print("valid attack policies (breached with filter off): %s"
          % (", ".join(real_attacks) if real_attacks else "NONE"))
    print("unfiltered episodes that breached: %d/%d" % (unfiltered_bad, n_each))
    print("filtered   episodes that breached: %d/%d" % (filtered_bad, n_each))
    print("worst clearance with filter on:    %+.4f m" % worst_filtered)
    print("legitimate task still completes with filter on: %s" % ("yes" if task_ok else "NO"))
    if not real_attacks:
        print("INCONCLUSIVE: nothing breached without the filter, so this run proves")
        print("nothing. Make the adversaries stronger or move the keep-out into reach.")
    elif filtered_bad == 0 and task_ok:
        print("RESULT: filter held on every valid attack AND the benign task completed.")
    elif filtered_bad == 0:
        print("RESULT: filter held, but it blocked legitimate work. Safety by paralysis")
        print("does not count as safety.")
    else:
        print("RESULT: filter FAILED on %d episode(s). This is the useful outcome:"
              % filtered_bad)
        print("inspect which policy got through and why before trusting any of it.")
    print("=" * 78)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prototype0_results.json")
    with open(out, "w") as fh:
        json.dump(
            [{k: v for k, v in r.items() if k != "latencies_us"} for r in results],
            fh, indent=2,
        )
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
