"""Regression tests for the safety filter.

These exist because every bug the filter has had so far was silent: it kept running,
kept looking plausible, and leaked a millimetre. Each test below pins one property
that was broken at some point during Prototype 0.

Run:  .venv/bin/python -m pytest sim/test_envelope.py -q
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adversary import Lunger, Seeker
from envelope import SafetyFilter, Slab, Sphere, desk_envelope
from harness import Rig, run_episode

SCENE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "so101", "scene.xml")
HEAD = np.array([0.0, -0.30, 0.22])
CONTROL_DT = 1.0 / 30.0


def _filter(margin=0.020, max_speed=5.5):
    env = desk_envelope(np.full(6, max_speed))
    env.margin = margin
    return env, SafetyFilter(env, control_dt=CONTROL_DT)


def test_sphere_distance_and_gradient():
    s = Sphere(center=(0.0, 0.0, 0.0), radius=0.1, name="s")
    assert abs(s.distance(np.array([0.3, 0.0, 0.0])) - 0.2) < 1e-9
    assert s.distance(np.array([0.05, 0.0, 0.0])) < 0.0
    g = s.gradient(np.array([0.3, 0.0, 0.0]))
    assert np.allclose(g, [1.0, 0.0, 0.0])


def test_sphere_gradient_at_centre_does_not_divide_by_zero():
    s = Sphere(center=(0.0, 0.0, 0.0), radius=0.1, name="s")
    g = s.gradient(np.array([0.0, 0.0, 0.0]))
    assert np.all(np.isfinite(g))
    assert abs(np.linalg.norm(g) - 1.0) < 1e-9


def test_slab_safe_side():
    s = Slab(normal=(0.0, 0.0, 1.0), offset=0.0, name="desk")
    assert s.distance(np.array([0.0, 0.0, 0.5])) > 0
    assert s.distance(np.array([0.0, 0.0, -0.5])) < 0


def test_speed_limit_is_respected_after_filtering():
    """The first version clamped AFTER projecting, which silently undid the projection."""
    env, filt = _filter(max_speed=2.0)
    points = [np.array([0.4, 0.4, 0.4])]          # far from everything
    jacs = [np.eye(3, 6)]
    out = filt.filter(np.full(6, 50.0), points, jacs)
    assert np.all(np.abs(out) <= 2.0 + 1e-6), out


def test_unconstrained_command_passes_through_unchanged():
    """Safety must be free when nothing is at risk, or the filter is a tax on everything."""
    env, filt = _filter()
    points = [np.array([0.4, 0.4, 0.4])]
    jacs = [np.eye(3, 6)]
    want = np.array([0.5, -0.3, 0.2, 0.1, -0.1, 0.0])
    out = filt.filter(want, points, jacs)
    assert np.allclose(out, want, atol=1e-6)


def test_filter_blocks_motion_into_a_keep_out_region():
    env, filt = _filter()
    # A point just outside the head sphere, with a Jacobian that maps joint 0
    # directly to motion straight at the head centre.
    point = HEAD + np.array([0.0, 0.14, 0.0])
    jac = np.zeros((3, 6))
    jac[1, 0] = -1.0                                # joint 0 drives -y, toward the head
    out = filt.filter(np.array([5.0, 0, 0, 0, 0, 0]), [point], [jac])
    assert out[0] < 5.0, "filter let a direct approach through untouched"


def test_filter_is_deterministic():
    """Same input, same output. An interposer that varies run to run cannot be audited."""
    env, filt = _filter()
    points = [HEAD + np.array([0.0, 0.16, 0.0])]
    jacs = [np.eye(3, 6)]
    cmd = np.array([1.0, -2.0, 0.5, 0.0, 0.3, -0.2])
    a = filt.filter(cmd.copy(), points, jacs)
    b = filt.filter(cmd.copy(), points, jacs)
    assert np.allclose(a, b)


def test_adversaries_actually_breach_without_the_filter():
    """If the attacks cannot win unfiltered, the whole experiment proves nothing."""
    env, filt = _filter()
    rig = Rig(SCENE, control_hz=30.0)
    for policy in (Seeker(), Lunger()):
        r = run_episode(rig, env, policy, HEAD, False, filt, seed=0, duration=4.0)
        assert r["violated"], "%s never breached unfiltered; not a valid attack" % policy.name


def test_filter_contains_adversaries_end_to_end():
    env, filt = _filter()
    rig = Rig(SCENE, control_hz=30.0)
    for policy in (Seeker(), Lunger()):
        r = run_episode(rig, env, policy, HEAD, True, filt, seed=0, duration=4.0)
        assert not r["violated"], "%s breached with the filter on" % policy.name
        assert r["min_clearance_m"] > 0.0


def test_filter_does_not_block_legitimate_work():
    """Zero violations achieved by refusing to move is not a passing result."""
    from adversary import Reacher

    env, filt = _filter()
    rig = Rig(SCENE, control_hz=30.0)
    benign = np.array([0.18, 0.10, 0.12])
    r = run_episode(rig, env, Reacher(), benign, True, filt, seed=0, duration=4.0)
    assert r["reached"], "filter prevented a benign reach"
