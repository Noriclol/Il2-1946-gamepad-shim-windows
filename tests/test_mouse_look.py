import unittest

from res.mouse_look import (
    RelAccumulator,
    aiming_curve,
    flatten_deadzone,
    normalize,
    stick_to_velocity,
)


class TestNormalize(unittest.TestCase):
    def test_centre_is_zero(self):
        self.assertAlmostEqual(normalize(0, -32768, 32767), 0.0, places=3)

    def test_max_is_one(self):
        self.assertAlmostEqual(normalize(32767, -32768, 32767), 1.0, places=3)

    def test_min_is_negative_one(self):
        self.assertAlmostEqual(normalize(-32768, -32768, 32767), -1.0, places=3)


class TestFlattenDeadzone(unittest.TestCase):
    def test_inside_deadzone_is_zero(self):
        self.assertEqual(flatten_deadzone(0.05, deadzone=0.1), 0.0)

    def test_deadzone_edge_rescales_to_full_range(self):
        self.assertAlmostEqual(flatten_deadzone(0.5, deadzone=0.1), 0.4444444, places=5)

    def test_negative_side_mirrors_positive(self):
        pos = flatten_deadzone(0.5, deadzone=0.1)
        neg = flatten_deadzone(-0.5, deadzone=0.1)
        self.assertAlmostEqual(neg, -pos)


class TestAimingCurve(unittest.TestCase):
    def test_zero_is_zero(self):
        self.assertEqual(aiming_curve(0.0), 0.0)

    def test_endpoints_are_full_scale(self):
        self.assertAlmostEqual(aiming_curve(1.0), 1.0, places=6)
        self.assertAlmostEqual(aiming_curve(-1.0), -1.0, places=6)

    def test_negative_side_mirrors_positive(self):
        self.assertAlmostEqual(aiming_curve(0.37), -aiming_curve(-0.37))

    def test_half_stick_stays_gentle(self):
        # Fine-control zone: well under half output at 50% deflection.
        self.assertLess(aiming_curve(0.5), 0.3)

    def test_past_centre_is_near_half_output(self):
        # centre defaults to 0.6 -- that's the midpoint of the ramp.
        self.assertAlmostEqual(aiming_curve(0.6), 0.5, delta=0.02)

    def test_monotonically_increasing(self):
        xs = [i / 100 for i in range(-100, 101)]
        ys = [aiming_curve(x) for x in xs]
        self.assertEqual(ys, sorted(ys))

    def test_custom_centre_and_steepness_still_end_at_one(self):
        self.assertAlmostEqual(aiming_curve(1.0, centre=0.3, steepness=6.0), 1.0, places=6)


class TestStickToVelocity(unittest.TestCase):
    def test_centred_stick_is_zero(self):
        self.assertAlmostEqual(stick_to_velocity(0, -32768, 32767), 0.0, places=2)

    def test_full_deflection_is_near_one(self):
        self.assertAlmostEqual(stick_to_velocity(32767, -32768, 32767), 1.0, places=2)


class TestRelAccumulator(unittest.TestCase):
    def test_zero_velocity_produces_zero(self):
        acc = RelAccumulator(rate_hz=60.0)
        self.assertEqual(acc.tick(0.0), 0)

    def test_full_velocity_matches_scaling_constant(self):
        acc = RelAccumulator(rate_hz=60.0)
        for _ in range(5):
            self.assertEqual(acc.tick(1.0), 60)

    def test_partial_velocity_converges_to_expected_average(self):
        acc = RelAccumulator(rate_hz=60.0)
        velocity = 0.3
        counts = [acc.tick(velocity) for _ in range(100)]
        expected_total = velocity * 60.0 * 100
        self.assertLess(abs(sum(counts) - expected_total), 1.0)

    def test_recenter_resets_remainder(self):
        acc = RelAccumulator(rate_hz=60.0)
        acc.tick(0.3)
        self.assertEqual(acc.tick(0.0), 0)

        fresh = RelAccumulator(rate_hz=60.0)
        after_recentre = [acc.tick(0.3) for _ in range(10)]
        from_fresh = [fresh.tick(0.3) for _ in range(10)]
        self.assertEqual(after_recentre, from_fresh)


if __name__ == "__main__":
    unittest.main()
