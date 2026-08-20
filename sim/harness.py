"""Episode runner and measurement.

Three numbers come out of here, and they are the whole point of Prototype 0:

  1. violations       - did the guarded geometry ever enter a keep-out volume
  2. filter latency   - how long enforcement takes, distribution not average
  3. task completion  - what the filter costs a legitimate policy

A filter that scores zero violations by refusing to move is not a success, which is
why the third number is measured in the same harness as the first two.
"""

import time

import mujoco
import numpy as np

from envelope import GUARDED_BODIES


class Rig:
    """Wraps the SO-101 model with the bits both the policy and the filter need."""

    def __init__(self, scene_path, control_hz=30.0):
        self.model = mujoco.MjModel.from_xml_path(scene_path)
        self.data = mujoco.MjData(self.model)
        self.control_dt = 1.0 / control_hz
        self.steps_per_control = max(1, int(round(self.control_dt / self.model.opt.timestep)))

        self.body_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, name)
            for name in GUARDED_BODIES
        ]
        missing = [n for n, i in zip(GUARDED_BODIES, self.body_ids) if i < 0]
        if missing:
            raise RuntimeError("guarded bodies not found in model: %s" % missing)

        self.gripper_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "gripper")
        self.nv = self.model.nv

        # Scratch buffers reused every step. Allocation inside a control loop is the
        # kind of habit that does not survive the move to an MCU.
        self._jacp = np.zeros((3, self.nv))
        self._jacr = np.zeros((3, self.nv))

    def reset(self, qpos=None):
        mujoco.mj_resetData(self.model, self.data)
        if qpos is not None:
            self.data.qpos[:] = qpos
        mujoco.mj_forward(self.model, self.data)

    def guarded_points(self):
        return [self.data.xpos[i].copy() for i in self.body_ids]

    def guarded_jacobians(self):
        jacs = []
        for i in self.body_ids:
            mujoco.mj_jacBody(self.model, self.data, self._jacp, self._jacr, i)
            jacs.append(self._jacp.copy())
        return jacs

    def gripper_pos(self):
        return self.data.xpos[self.gripper_id].copy()

    def gripper_jacobian(self):
        mujoco.mj_jacBody(self.model, self.data, self._jacp, self._jacr, self.gripper_id)
        return self._jacp.copy()

    def apply_joint_velocity(self, q_dot):
        """Integrate a velocity command into position targets, then step physics.

        The SO-101's servos are position-controlled over the bus, which is exactly what
        muzzle will see: Goal_Position writes, not torques. Keeping the sim in the same
        currency as the hardware means the filter we test is the filter we ship.
        """
        target = self.data.qpos[: self.model.nu] + q_dot[: self.model.nu] * self.control_dt
        lower = self.model.jnt_range[: self.model.nu, 0]
        upper = self.model.jnt_range[: self.model.nu, 1]
        self.data.ctrl[:] = np.clip(target, lower, upper)
        for _ in range(self.steps_per_control):
            mujoco.mj_step(self.model, self.data)


def run_episode(rig, envelope, policy, target, filter_on, safety_filter=None,
                duration=6.0, seed=0, task_radius=0.05):
    """Run one policy for `duration` seconds and report what happened."""
    rng = np.random.default_rng(seed)
    policy.reset(rng)
    rig.reset()

    steps = int(duration / rig.control_dt)
    latencies = []
    violation_steps = 0
    breached_regions = set()
    min_clearance = float("inf")
    reached_at = None

    for step in range(steps):
        t = step * rig.control_dt
        gpos = rig.gripper_pos()

        mode, command = policy.act(t, rig.data.qpos.copy(), gpos, target)
        if mode == "cartesian":
            jac = rig.gripper_jacobian()
            # Damped least squares: the untrusted side's own inverse kinematics.
            # Its quality is not our problem; containment must hold regardless.
            lam = 0.05
            q_dot = jac.T @ np.linalg.solve(jac @ jac.T + lam * np.eye(3), command)
        else:
            q_dot = np.asarray(command, dtype=np.float64)

        if q_dot.shape[0] < rig.nv:
            q_dot = np.pad(q_dot, (0, rig.nv - q_dot.shape[0]))

        if filter_on:
            points = rig.guarded_points()
            jacs = rig.guarded_jacobians()
            start = time.perf_counter()
            q_dot = safety_filter.filter(q_dot, points, jacs)
            latencies.append((time.perf_counter() - start) * 1e6)  # microseconds

        rig.apply_joint_velocity(q_dot)

        points = rig.guarded_points()
        breaches = envelope.violations(points)
        if breaches:
            violation_steps += 1
            breached_regions.update(name for name, _ in breaches)
        min_clearance = min(min_clearance, envelope.worst_distance(points))

        if reached_at is None and np.linalg.norm(rig.gripper_pos() - target) < task_radius:
            reached_at = t

    return {
        "policy": policy.name,
        "filter_on": filter_on,
        "steps": steps,
        "violation_steps": violation_steps,
        "violated": violation_steps > 0,
        "breached_regions": sorted(breached_regions),
        "min_clearance_m": min_clearance,
        "reached": reached_at is not None,
        "reached_at_s": reached_at,
        "latencies_us": latencies,
    }
