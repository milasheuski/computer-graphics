

import unittest

from controller import ColorController


class ControllerTests(unittest.TestCase):
    def test_every_model_is_recalculated_from_rgb(self) -> None:
        state, warnings = ColorController().from_rgb(255, 0, 0)
        self.assertEqual(state.rgb, (255, 0, 0))
        self.assertEqual(state.cmyk, (0.0, 100.0, 100.0, 0.0))
        self.assertEqual(state.hls, (0.0, 50.0, 100.0))
        self.assertEqual(state.hex_value, "#ff0000")
        self.assertEqual(warnings, [])

    def test_invalid_rgb_is_clamped_with_warning(self) -> None:
        state, warnings = ColorController().from_rgb(300, -5, 128)
        self.assertEqual(state.rgb, (255, 0, 128))
        self.assertEqual(len(warnings), 2)


if __name__ == "__main__":
    unittest.main()
