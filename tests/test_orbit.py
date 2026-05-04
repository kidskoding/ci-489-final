import math
import pytest
from orbit import Orbit, solve_kepler

def test_perihelion_and_aphelion_match_orbit_model():
    orbit = Orbit(apoapsis=360, periapsis=145)

    perihelion = orbit.point_at(0)
    aphelion = orbit.point_at(0.5)

    assert perihelion.x == pytest.approx(145, abs=1e-5)
    assert perihelion.y == pytest.approx(0, abs=1e-5)
    assert aphelion.x == pytest.approx(-360, abs=1e-5)
    assert aphelion.y == pytest.approx(0, abs=1e-5)

def test_kepler_solution_satisfies_equation():
    mean_anomaly = 1.7
    eccentricity = 0.61
    eccentric_anomaly = solve_kepler(mean_anomaly, eccentricity)

    residual = eccentric_anomaly - eccentricity * math.sin(eccentric_anomaly) - mean_anomaly

    assert abs(residual) < 0.000001
