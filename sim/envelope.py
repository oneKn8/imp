"""The safety envelope and the filter that enforces it.

Everything in this file is written under one constraint that is easy to forget in
simulation: it has to run on a microcontroller later. The whole thesis is that
enforcement lives below the host, on an ESP32-C3 sitting on the servo bus. A filter
that needs scipy, a general QP solver, or unbounded iteration would prove nothing
about that claim, so this uses only fixed-size arrays, a bounded iteration count, and
arithmetic that maps directly to plain C.

The envelope is expressed as keep-out volumes in Cartesian space plus per-joint speed
limits. The filter is a velocity-level control barrier function: for a safety function
h(q) that is positive when safe, we require h_dot >= -alpha * h, which keeps h from
crossing zero. With velocity commands that is a linear constraint on q_dot, so
enforcement is a projection onto an intersection of half-spaces.
"""

import numpy as np

# Bodies whose geometry we guard. The gripper and jaw are what actually reach a face.
GUARDED_BODIES = ("wrist", "gripper", "camera_mount", "moving_jaw_so101_v1")


class Sphere:
    """A ball the arm must stay out of. Santo's head, a coffee cup, a hand."""

    def __init__(self, center, radius, name):
        self.center = np.asarray(center, dtype=np.float64)
        self.radius = float(radius)
        self.name = name

    def distance(self, point):
        return float(np.linalg.norm(point - self.center) - self.radius)

    def gradient(self, point):
        """d(distance)/d(point). Unit vector pointing away from the center."""
        delta = point - self.center
        norm = float(np.linalg.norm(delta))
        if norm < 1e-9:
            # Degenerate: point at the exact center. Push along +z rather than divide by zero.
            return np.array([0.0, 0.0, 1.0])
        return delta / norm


class Slab:
    """A half-space the arm must stay out of, used for monitors, walls, the desk.

    Safe side is where dot(normal, point) >= offset.
    """

    def __init__(self, normal, offset, name):
        n = np.asarray(normal, dtype=np.float64)
        self.normal = n / np.linalg.norm(n)
        self.offset = float(offset)
        self.name = name

    def distance(self, point):
        return float(np.dot(self.normal, point) - self.offset)

    def gradient(self, point):
        return self.normal


class Envelope:
    """The physical envelope: keep-out volumes plus joint speed limits."""

    def __init__(self, regions, max_joint_speed, alpha=4.0, margin=0.020):
        self.regions = list(regions)
        self.max_joint_speed = np.asarray(max_joint_speed, dtype=np.float64)
        # alpha sets how hard the filter brakes as it approaches a boundary. Higher
        # alpha lets the arm get closer and faster before the filter bites.
        self.alpha = float(alpha)
        # margin inflates every region. This is where discretisation and model error
        # get paid for, and it is not optional: with margin at zero the one-step
        # constraint permits h_next = 0 exactly, so the arm is aimed at the boundary
        # and every rounding error lands on the wrong side of it. sweep_margin.py
        # measured the residual at ~1.2 mm and found 5 mm enough for zero breaches
        # at no cost to task time. The default is 20 mm because real hardware adds
        # encoder quantisation, backlash, and the gap between guarding body origins
        # and guarding actual mesh geometry, none of which the sim charges us for.
        self.margin = float(margin)

    def violations(self, points):
        """Which (region, body) pairs are currently breached. Ground truth, not a prediction."""
        breached = []
        for region in self.regions:
            for idx, point in enumerate(points):
                if region.distance(point) < 0.0:
                    breached.append((region.name, idx))
        return breached

    def worst_distance(self, points):
        return min(
            (region.distance(p) for region in self.regions for p in points),
            default=float("inf"),
        )


def desk_envelope(max_joint_speed):
    """The envelope for a desk: a head, a monitor plane, and the desk surface.

    Coordinates are the SO-101's own frame, metres, arm mounted at the origin.
    These are deliberately aggressive for a first prototype: the head sits inside the
    arm's reach, so an unfiltered adversary can and does hit it.
    """
    return Envelope(
        regions=[
            # Santo's head, sitting behind the desk, well inside reach.
            Sphere(center=(0.0, -0.30, 0.22), radius=0.13, name="head"),
            # The monitor: a vertical plane the gripper must stay in front of.
            Slab(normal=(0.0, 1.0, 0.0), offset=-0.34, name="monitor"),
            # The desk surface, so the arm does not drive itself into the table.
            Slab(normal=(0.0, 0.0, 1.0), offset=0.005, name="desk"),
        ],
        max_joint_speed=max_joint_speed,
    )


class SafetyFilter:
    """Velocity-level CBF filter, solved by bounded successive projection.

    Given a desired joint velocity from an untrusted source, return the closest
    velocity that satisfies every barrier constraint and the speed limits. The
    projection loop is Kaczmarz-style: repeatedly project onto whichever half-space
    is violated. It is not an exact QP solution, but it is monotone, needs no matrix
    factorisation, and terminates in a fixed number of passes, which is what makes it
    implementable on the C3.

    Three details here were learned by watching the first version leak, and each one
    is the kind of mistake that would have shipped silently:

    1. Speed limits are CONSTRAINTS, not a clamp applied afterwards. Clipping after
       projecting undoes the projection and quietly reintroduces the violation.
    2. The barrier is enforced against the state one control step ahead, not the
       state right now. A continuous-time CBF says nothing about what a zero-order
       hold does over 33 ms, and at 5.5 rad/s the gripper covers centimetres in that
       window.
    3. If the constraints cannot all be met, the filter brakes rather than returning
       its best effort. Fail closed is the whole posture of the project: an
       interposer that passes something through when confused is decoration.
    """

    MAX_PASSES = 12

    def __init__(self, envelope, control_dt):
        self.env = envelope
        self.control_dt = float(control_dt)
        self.last_constraints = 0
        self.last_passes = 0
        self.brake_events = 0

    def build_constraints(self, points, jacobians):
        """Turn the envelope into rows A @ q_dot >= b.

        For each guarded point and region:
            h     = signed distance to the region, minus margin
            dh/dq = grad_point(h) @ J    (J maps joint velocity to point velocity)

        The continuous CBF condition is dh/dq @ q_dot >= -alpha * h. Because the
        command is held for a whole control step, we take whichever of the CBF decay
        rate and the one-step reachability limit is tighter. With dt = 1/30 s the
        second term dominates whenever the barrier is nearly breached, which is
        exactly when it matters.
        """
        rows = []
        lower = []
        for region in self.env.regions:
            for point, jac in zip(points, jacobians):
                h = region.distance(point) - self.env.margin
                grad = region.gradient(point)
                # Never permit more than the distance that remains this step.
                decay = -min(self.env.alpha * h, h / self.control_dt)
                rows.append(grad @ jac)
                lower.append(decay)
        if not rows:
            return np.zeros((0, len(self.env.max_joint_speed))), np.zeros(0)
        return np.asarray(rows), np.asarray(lower)

    def _speed_rows(self, nv):
        """Speed limits expressed as half-spaces so the projection respects them."""
        rows = []
        lower = []
        limits = self.env.max_joint_speed
        for i in range(len(limits)):
            up = np.zeros(nv)
            up[i] = -1.0
            rows.append(up)            # -v_i >= -limit  ->  v_i <= limit
            lower.append(-limits[i])
            dn = np.zeros(nv)
            dn[i] = 1.0
            rows.append(dn)            #  v_i >= -limit
            lower.append(-limits[i])
        return rows, lower

    def filter(self, q_dot_desired, points, jacobians):
        """Return a safe joint velocity as close to the requested one as possible."""
        A_bar, b_bar = self.build_constraints(points, jacobians)
        nv = q_dot_desired.shape[0]
        s_rows, s_lower = self._speed_rows(nv)

        A = np.vstack([A_bar, np.asarray(s_rows)]) if A_bar.shape[0] else np.asarray(s_rows)
        b = np.concatenate([b_bar, np.asarray(s_lower)]) if b_bar.size else np.asarray(s_lower)
        self.last_constraints = A.shape[0]

        v = q_dot_desired.astype(np.float64).copy()
        v, passes, feasible = self._project(A, b, v)

        if not feasible:
            # Could not satisfy everything from the requested velocity. Brake: start
            # from a full stop, which satisfies the speed limits by construction, and
            # project that onto the barriers so the arm still retreats if it must.
            self.brake_events += 1
            v, extra, feasible = self._project(A, b, np.zeros(nv))
            passes += extra
            if not feasible:
                v = np.zeros(nv)

        self.last_passes = passes
        return v

    def _project(self, A, b, v):
        for p in range(self.MAX_PASSES):
            worst = 0.0
            for i in range(A.shape[0]):
                row = A[i]
                shortfall = b[i] - row @ v
                if shortfall > 1e-9:
                    denom = row @ row
                    if denom > 1e-12:
                        v = v + (shortfall / denom) * row
                        worst = max(worst, shortfall)
            if worst <= 1e-9:
                return v, p + 1, True
        residual = float(np.max(b - A @ v)) if A.shape[0] else 0.0
        return v, self.MAX_PASSES, residual <= 1e-6
