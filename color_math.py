

from typing import List, Tuple


def clamp(value: float, minimum: float, maximum: float) -> Tuple[float, bool]:
    if value < minimum:
        return minimum, True
    if value > maximum:
        return maximum, True
    return value, False


def rgb_to_cmyk(r: int, g: int, b: int) -> Tuple[float, float, float, float]:
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    k = 1.0 - max(r_norm, g_norm, b_norm)

    if k >= 1.0:
        return 0.0, 0.0, 0.0, 100.0

    c = (1.0 - r_norm - k) / (1.0 - k)
    m = (1.0 - g_norm - k) / (1.0 - k)
    y = (1.0 - b_norm - k) / (1.0 - k)
    return tuple(round(value * 100.0, 1) for value in (c, m, y, k))


def cmyk_to_rgb(c, m, y, k) -> Tuple[Tuple[int, int, int], List[str]]:
    warnings: List[str] = []
    values = []

    for name, value in zip("CMYK", (c, m, y, k)):
        corrected, was_clamped = clamp(value, 0.0, 100.0)
        values.append(corrected)
        if was_clamped:
            warnings.append(f"{name} обрезан до диапазона [0, 100] %")

    c_norm, m_norm, y_norm, k_norm = (value / 100.0 for value in values)
    rgb = (
        round(255.0 * (1.0 - c_norm) * (1.0 - k_norm)),
        round(255.0 * (1.0 - m_norm) * (1.0 - k_norm)),
        round(255.0 * (1.0 - y_norm) * (1.0 - k_norm)),
    )
    return tuple(int(value) for value in rgb), warnings


def rgb_to_hls(r: int, g: int, b: int) -> Tuple[float, float, float]:
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    maximum = max(r_norm, g_norm, b_norm)
    minimum = min(r_norm, g_norm, b_norm)
    delta = maximum - minimum
    lightness = (maximum + minimum) / 2.0

    if delta == 0:
        hue = 0.0
        saturation = 0.0
    else:
        denominator = maximum + minimum if lightness <= 0.5 else 2.0 - maximum - minimum
        saturation = delta / denominator

        if maximum == r_norm:
            hue = ((g_norm - b_norm) / delta) % 6.0
        elif maximum == g_norm:
            hue = ((b_norm - r_norm) / delta) + 2.0
        else:
            hue = ((r_norm - g_norm) / delta) + 4.0
        hue *= 60.0

    return round(hue, 1), round(lightness * 100.0, 1), round(saturation * 100.0, 1)


def hls_to_rgb(h, l, s) -> Tuple[Tuple[int, int, int], List[str]]:
    warnings: List[str] = []
    hue = h % 360.0
    if h != hue:
        warnings.append("H приведён к диапазону [0, 360)")

    lightness, lightness_clamped = clamp(l, 0.0, 100.0)
    saturation, saturation_clamped = clamp(s, 0.0, 100.0)
    if lightness_clamped:
        warnings.append("L обрезан до диапазона [0, 100] %")
    if saturation_clamped:
        warnings.append("S обрезан до диапазона [0, 100] %")

    lightness /= 100.0
    saturation /= 100.0

    if saturation == 0:
        gray = int(round(lightness * 255.0))
        return (gray, gray, gray), warnings

    chroma = (1.0 - abs(2.0 * lightness - 1.0)) * saturation
    hue_sector = hue / 60.0
    x_value = chroma * (1.0 - abs(hue_sector % 2.0 - 1.0))
    match = lightness - chroma / 2.0

    if hue_sector < 1:
        temporary = (chroma, x_value, 0.0)
    elif hue_sector < 2:
        temporary = (x_value, chroma, 0.0)
    elif hue_sector < 3:
        temporary = (0.0, chroma, x_value)
    elif hue_sector < 4:
        temporary = (0.0, x_value, chroma)
    elif hue_sector < 5:
        temporary = (x_value, 0.0, chroma)
    else:
        temporary = (chroma, 0.0, x_value)

    rgb = tuple(int(round((value + match) * 255.0)) for value in temporary)
    return rgb, warnings
