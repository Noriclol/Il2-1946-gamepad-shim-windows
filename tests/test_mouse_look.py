import unittest

from res.mouse_look import (
    RelAccumulator,
    apply_expo,
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


class TestApplyExpo(unittest.TestCase):
    def test_zero_expo_is_linear(self):
        self.assertEqual(apply_expo(0.5, expo=0.0), 0.5)

    def test_full_expo_is_cubic(self):
        self.assertAlmostEqual(apply_expo(0.5, expo=1.0), 0.125)

    def test_zero_input_is_zero(self):
        self.assertEqual(apply_expo(0.0, expo=0.5), 0.0)


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
