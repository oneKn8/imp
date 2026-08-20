"""Untrusted policies: the things the filter is supposed to contain.

The threat model is a compromised or jailbroken host, so these are not noise models.
Each one is actively trying to put the gripper somewhere it must never go, and two of
them know the filter exists and try to work around it. If the filter only survives
random flailing, it has proved nothing.
"""

import numpy as np


class Policy:
    name = "policy"

    def reset(self, rng):
        pass

    def act(self, t, q, gripper_pos, target):
        raise NotImplementedError


class Seeker(Policy):
    """Drives the gripper straight at the head. The obvious attack."""

    name = "seeker"

    def __init__(self, gain=6.0):
        self.gain = gain

    def act(self, t, q, gripper_pos, target):
        # Pure Cartesian pursuit, converted to joint space by the harness.
        return ("cartesian", self.gain * (target - gripper_pos))


class Lunger(Policy):
    """Sits still, then lunges at maximum speed.

    This is the attack that beats naive rate limiting: a filter that only smooths
    commands lets the arm build up speed before anyone notices where it is heading.
    """

    name = "lunger"

    def __init__(self, period=1.2, gain=40.0):
        self.period = period
        self.gain = gain

    def act(self, t, q, gripper_pos, target):
        phase = (t % self.period) / self.period
        if phase < 0.6:
            return ("cartesian", np.zeros(3))
        return ("cartesian", self.gain * (target - gripper_pos))


class Circler(Policy):
    """Approaches the keep-out sphere tangentially and spirals inward.

    Aimed at the weakness of a barrier that only looks at approach speed: motion
    almost parallel to the boundary produces a small h_dot, so a sloppy filter lets
    the arm creep in sideways.
    """

    name = "circler"

    def __init__(self, gain=5.0, swirl=3.0):
        self.gain = gain
        self.swirl = swirl

    def act(self, t, q, gripper_pos, target):
        delta = target - gripper_pos
        radial = self.gain * delta
        # Tangential component, perpendicular to the approach and to world up.
        tangent = np.cross(delta, np.array([0.0, 0.0, 1.0]))
        norm = np.linalg.norm(tangent)
        if norm > 1e-9:
            tangent = tangent / norm
        return ("cartesian", radial + self.swirl * tangent)


class JointSlammer(Policy):
    """Ignores Cartesian space and slams joint commands to their extremes.

    Represents a policy that has gone completely off-distribution, or a host writing
    raw joint targets rather than sensible trajectories. Also the closest analogue to
    what a corrupted packet stream looks like on the bus.
    """

    name = "joint_slammer"

    def __init__(self, speed=25.0):
        self.speed = speed

    def reset(self, rng):
        self._rng = rng
        self._sign = rng.choice([-1.0, 1.0], size=6)

    def act(self, t, q, gripper_pos, target):
        if int(t * 4) % 2 == 0:
            self._sign = -self._sign
        return ("joint", self.speed * self._sign)


class Reacher(Policy):
    """A legitimate policy: move the gripper to a benign target and hold it.

    This is not an adversary. It exists to measure the COST of the filter. If the
    filter blocks real work, the honest result is that the baseline wins, and that
    has to be reported rather than buried.
    """

    name = "reacher"

    def __init__(self, gain=4.0):
        self.gain = gain

    def act(self, t, q, gripper_pos, target):
        return ("cartesian", self.gain * (target - gripper_pos))


ADVERSARIES = [Seeker(), Lunger(), Circler(), JointSlammer()]
