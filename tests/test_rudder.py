import unittest

from res.rudder import RUDDER_CENTRE, RUDDER_MAX, RUDDER_MIN, fold_rudder, normalize


class TestNormalize(unittest.TestCase):
    def test_min_maps_to_zero(self):
        self.assertAlmostEqual(normalize(-32768, -32768, 32767), 0.0)

    def test_max_maps_to_one(self):
        self.assertAlmostEqual(normalize(32767, -32768, 32767), 1.0)

    def test_zero_span_returns_zero(self):
        self.assertEqual(normalize(5, 5, 5), 0.0)


class TestFoldRudder(unittest.TestCase):
    AXIS = dict(lt_min=-32768, lt_max=32767, rt_min=-32768, rt_max=32767)

    def fold(self, lt_value, rt_value, **kwargs):
        return fold_rudder(
            lt_value, self.AXIS["lt_min"], self.AXIS["lt_max"],
            rt_value, self.AXIS["rt_min"], self.AXIS["rt_max"],
            **kwargs,
        )

    def test_both_released_centres(self):
        self.assertEqual(self.fold(-32768, -32768), RUDDER_CENTRE)

    def test_left_full_pulls_to_min(self):
        self.assertEqual(self.fold(32767, -32768), RUDDER_MIN)

    def test_right_full_pulls_to_max(self):
        self.assertEqual(self.fold(-32768, 32767), RUDDER_MAX)

    def test_both_full_centres(self):
        self.assertEqual(self.fold(32767, 32767), RUDDER_CENTRE)

    def test_deadzone_suppresses_small_values(self):
        rt_value = -32768 + int(0.02 * 65535)
        self.assertEqual(self.fold(-32768, rt_value), RUDDER_CENTRE)

    def test_invert_mirrors_around_centre(self):
        normal = self.fold(32767, -32768)
        inverted = self.fold(32767, -32768, invert=True)
        self.assertEqual(inverted, RUDDER_MAX - normal)

    def test_output_never_negative(self):
        for lt in (-32768, 0, 32767):
            for rt in (-32768, 0, 32767):
                self.assertGreaterEqual(self.fold(lt, rt), RUDDER_MIN)
                self.assertLessEqual(self.fold(lt, rt), RUDDER_MAX)


if __name__ == "__main__":
    unittest.main()
