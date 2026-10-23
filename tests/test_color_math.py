

import unittest

from color_math import cmyk_to_rgb, hls_to_rgb, rgb_to_cmyk, rgb_to_hls


class ColorMathTests(unittest.TestCase):
    def test_red_rgb_to_cmyk(self) -> None:
        self.assertEqual(rgb_to_cmyk(255, 0, 0), (0.0, 100.0, 100.0, 0.0))

    def test_red_rgb_to_hls(self) -> None:
        self.assertEqual(rgb_to_hls(255, 0, 0), (0.0, 50.0, 100.0))

    def test_cmyk_red_to_rgb(self) -> None:
        rgb, warnings = cmyk_to_rgb(0, 100, 100, 0)
        self.assertEqual(rgb, (255, 0, 0))
        self.assertEqual(warnings, [])

    def test_hls_green_to_rgb(self) -> None:
        rgb, warnings = hls_to_rgb(120, 50, 100)
        self.assertEqual(rgb, (0, 255, 0))
        self.assertEqual(warnings, [])

    def test_rgb_cmyk_round_trip(self) -> None:
        colors = [(0, 0, 0), (255, 255, 255), (255, 0, 0),
                  (0, 255, 0), (0, 0, 255), (12, 128, 240)]
        for original in colors:
            with self.subTest(rgb=original):
                restored, _ = cmyk_to_rgb(*rgb_to_cmyk(*original))
                for expected, actual in zip(original, restored):
                    self.assertAlmostEqual(expected, actual, delta=1)

    def test_rgb_hls_round_trip(self) -> None:
        colors = [(0, 0, 0), (255, 255, 255), (255, 0, 0),
                  (0, 255, 0), (0, 0, 255), (12, 128, 240)]
        for original in colors:
            with self.subTest(rgb=original):
                restored, _ = hls_to_rgb(*rgb_to_hls(*original))
                for expected, actual in zip(original, restored):
                    self.assertAlmostEqual(expected, actual, delta=1)

    def test_invalid_cmyk_is_clamped_with_warning(self) -> None:
        rgb, warnings = cmyk_to_rgb(120, -10, 0, 0)
        self.assertEqual(rgb, (0, 255, 255))
        self.assertEqual(len(warnings), 2)

    def test_invalid_hls_is_corrected_with_warning(self) -> None:
        rgb, warnings = hls_to_rgb(480, 50, 100)
        self.assertEqual(rgb, (0, 255, 0))
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
