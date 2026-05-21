"""Particle Physics Engine & Intensity Heat Map."""

import numpy as np

from . import noise as _noise

_X = 0
_Y = 1
_VX = 2
_VY = 3


class FlowEngine:
    """Manages simulation state for one frame cycle."""

    def __init__(
        self,
        cols: int,
        rows: int,
        n_particles: int,
        speed: float,
        decay: float,
        noise_scale: float,
        time_step: float,
    ) -> None:
        self.n_particles = n_particles
        self.speed = float(speed)
        self.decay = float(decay)
        self.noise_scale = float(noise_scale)
        self.time_step = float(time_step)
        self._t = 0.0

        self._rng = np.random.default_rng()
        self._noise_buffer = np.empty((n_particles, 2), dtype=np.float32)

        self.resize(cols, rows)

    def _spawn_particles(self, n: int) -> np.ndarray:
        """Spawn N particles uniformly across the virtual canvas."""
        p = np.zeros((n, 4), dtype=np.float32)
        p[:, _X] = self._rng.uniform(0, self.vw, size=n)
        p[:, _Y] = self._rng.uniform(0, self.vh, size=n)
        p[:, _VX] = self._rng.uniform(-0.5, 0.5, size=n)
        p[:, _VY] = self._rng.uniform(-0.5, 0.5, size=n)
        return p

    def _respawn_oob(self) -> None:
        """Respawn out-of-bounds particles on a random edge with inward velocity."""
        x, y = self.particles[:, _X], self.particles[:, _Y]
        oob = (x < 0) | (x >= self.vw) | (y < 0) | (y >= self.vh)

        n_oob = int(oob.sum())
        if n_oob == 0:
            return

        edges = self._rng.integers(0, 4, size=n_oob)
        rand_x = self._rng.uniform(0, self.vw, size=n_oob)
        rand_y = self._rng.uniform(0, self.vh, size=n_oob)
        speed_mag = self._rng.uniform(0.3, 1.0, size=n_oob) * self.speed

        x_oob = np.where(
            edges == 0,
            0.0,
            np.where(edges == 1, float(self.vw - 1), rand_x),
        )
        y_oob = np.where(
            edges == 2,
            0.0,
            np.where(edges == 3, float(self.vh - 1), rand_y),
        )

        vx_oob = np.where(
            edges == 0,
            speed_mag,
            np.where(edges == 1, -speed_mag, 0.0),
        )
        vy_oob = np.where(
            edges == 2,
            speed_mag,
            np.where(edges == 3, -speed_mag, 0.0),
        )

        self.particles[oob, _X] = x_oob
        self.particles[oob, _Y] = y_oob
        self.particles[oob, _VX] = vx_oob
        self.particles[oob, _VY] = vy_oob

    def _update_flow_field(self) -> None:
        """Regenerate flow field from noise."""
        raw = _noise.noise2d(self._gx, self._gy, self._t, self.noise_scale)
        angles = (raw + 1.0) * (2.0 * np.pi)
        upsampled = np.repeat(np.repeat(angles, 4, axis=0), 2, axis=1)
        self.flow_field[:] = upsampled.astype(np.float32)

    def _update_particles(self) -> None:
        """Vectorized particle physics update."""
        p = self.particles

        xi = np.clip(np.floor(p[:, _X]).astype(np.int32), 0, self.vw - 1)
        yi = np.clip(np.floor(p[:, _Y]).astype(np.int32), 0, self.vh - 1)
        angles = self.flow_field[yi, xi]

        self._rng.standard_normal(out=self._noise_buffer, dtype=np.float32)

        p[:, _VX] += (
            np.cos(angles) * self.speed * 0.15 + self._noise_buffer[:, 0] * 0.01
        )
        p[:, _VY] += (
            np.sin(angles) * self.speed * 0.15 + self._noise_buffer[:, 1] * 0.01
        )

        p[:, _VX] *= 0.92
        p[:, _VY] *= 0.92

        max_v = 3.0 * self.speed
        np.clip(p[:, _VX], -max_v, max_v, out=p[:, _VX])
        np.clip(p[:, _VY], -max_v, max_v, out=p[:, _VY])

        p[:, _X] += p[:, _VX]
        p[:, _Y] += p[:, _VY]

    def _stamp_heat_map(self) -> None:
        """Stamp positions into heat map and apply decay."""
        p = self.particles
        xi = np.clip(np.floor(p[:, _X]).astype(np.int32), 0, self.vw - 1)
        yi = np.clip(np.floor(p[:, _Y]).astype(np.int32), 0, self.vh - 1)

        self.intensity[yi, xi] = 1.0
        self.intensity *= self.decay
        self.intensity[self.intensity < 0.02] = 0.0

    def step(self) -> np.ndarray:
        """Execute one simulation tick."""
        self._update_flow_field()
        self._update_particles()
        self._respawn_oob()
        self._stamp_heat_map()
        self._t += self.time_step
        return self.intensity

    def resize(self, cols: int, rows: int) -> None:
        """Reinitialize size-dependent state."""
        self.cols, self.rows = cols, rows
        self.vw, self.vh = cols * 2, rows * 4

        gx_1d = np.linspace(0, cols, cols, endpoint=False, dtype=np.float32)
        gy_1d = np.linspace(0, rows, rows, endpoint=False, dtype=np.float32)
        self._gx, self._gy = np.meshgrid(gx_1d, gy_1d)

        self.intensity = np.zeros((self.vh, self.vw), dtype=np.float32)
        self.flow_field = np.zeros((self.vh, self.vw), dtype=np.float32)
        self.particles = self._spawn_particles(self.n_particles)
        self._noise_buffer = np.empty((self.n_particles, 2), dtype=np.float32)
