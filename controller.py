

from dataclasses import dataclass
from typing import List, Tuple

from color_math import clamp, cmyk_to_rgb, hls_to_rgb, rgb_to_cmyk, rgb_to_hls


@dataclass(frozen=True)
class ColorState:
    rgb: Tuple[int, int, int]
    cmyk: Tuple[float, float, float, float]
    hls: Tuple[float, float, float]
    hex_value: str


class ColorController:


    @staticmethod
    def _state(rgb: Tuple[int, int, int]) -> ColorState:
        r, g, b = rgb
        return ColorState(
            rgb=rgb,
            cmyk=rgb_to_cmyk(r, g, b),
            hls=rgb_to_hls(r, g, b),
            hex_value=f"#{r:02x}{g:02x}{b:02x}",
        )

    def from_rgb(self, r, g, b) -> Tuple[ColorState, List[str]]:
        warnings: List[str] = []
        corrected = []
        for name, value in zip("RGB", (r, g, b)):
            value, was_clamped = clamp(value, 0, 255)
            rounded = int(round(value))
            corrected.append(rounded)
            if was_clamped:
                warnings.append(f"{name} обрезан до диапазона [0, 255]")
            elif rounded != value:
                warnings.append(f"{name} округлён до целого значения {rounded}")
        return self._state(tuple(corrected)), warnings

    def from_cmyk(self, c, m, y, k) -> Tuple[ColorState, List[str]]:
        rgb, warnings = cmyk_to_rgb(c, m, y, k)
        return self._state(rgb), warnings

    def from_hls(self, h, l, s) -> Tuple[ColorState, List[str]]:
        rgb, warnings = hls_to_rgb(h, l, s)
        return self._state(rgb), warnings

    def from_hex(self, value: str) -> Tuple[ColorState, List[str]]:
        clean_value = value.lstrip("#")
        if len(clean_value) != 6:
            raise ValueError("HEX-цвет должен содержать 6 символов")
        rgb = tuple(int(clean_value[index:index + 2], 16) for index in (0, 2, 4))
        return self._state(rgb), []

    @staticmethod
    def contrast_text(hex_value: str) -> str:
        clean_value = hex_value.lstrip("#")
        r, g, b = (int(clean_value[index:index + 2], 16) for index in (0, 2, 4))
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#111111" if luminance > 160 else "#ffffff"
