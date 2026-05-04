import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def rotate(self, radians: float) -> "Vec2":
        c = math.cos(radians)
        s = math.sin(radians)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)


@dataclass
class Orbit:
    apoapsis: float = 360.0
    periapsis: float = 145.0
    argument_of_periapsis: float = 0.0
    samples: int = 360

    def __post_init__(self) -> None:
        if self.periapsis <= 0:
            raise ValueError("periapsis must be positive")
        if self.apoapsis <= 0:
            raise ValueError("apoapsis must be positive")
        if self.samples < 60:
            self.samples = 60

    @property
    def semi_major_axis(self) -> float:
        return (self.apoapsis + self.periapsis) / 2.0

    @property
    def semi_minor_axis(self) -> float:
        return math.sqrt(self.apoapsis * self.periapsis)

    @property
    def eccentricity(self) -> float:
        return (self.semi_major_axis - self.periapsis) / self.semi_major_axis

    def point_at(self, t: float) -> Vec2:
        """Return a point for orbital progress t in [0, 1)."""
        progress = t % 1.0
        mean_anomaly = progress * math.tau
        eccentric_anomaly = solve_kepler(mean_anomaly, self.eccentricity)
        x = self.semi_major_axis * (math.cos(eccentric_anomaly) - self.eccentricity)
        y = self.semi_minor_axis * math.sin(eccentric_anomaly)
        return Vec2(x, y).rotate(math.radians(self.argument_of_periapsis))

    def polyline(self) -> list[Vec2]:
        return [self.point_at(i / self.samples) for i in range(self.samples + 1)]


def solve_kepler(mean_anomaly: float, eccentricity: float) -> float:
    """Solve M = E - e sin(E) with a Newton iteration."""
    if not 0 <= eccentricity < 1:
        raise ValueError("eccentricity must be in [0, 1)")

    eccentric_anomaly = math.pi if eccentricity > 0.8 else mean_anomaly
    for _ in range(100):
        value = eccentric_anomaly - eccentricity * math.sin(eccentric_anomaly) - mean_anomaly
        derivative = 1 - eccentricity * math.cos(eccentric_anomaly)
        next_value = eccentric_anomaly - value / derivative
        if abs(eccentric_anomaly - next_value) < 0.000001:
            return next_value
        eccentric_anomaly = next_value
    return eccentric_anomaly
