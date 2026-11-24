import numpy as np
from PIL import Image, ImageDraw


def _base_scene(width=480, height=320):
    img = Image.new("RGB", (width, height), (35, 55, 85))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        c = int(30 + 180 * y / height)
        draw.line([(0, y), (width, y)], fill=(c // 2, c, 220 - c // 2))
    draw.rectangle([35, 40, 185, 190], fill=(220, 70, 60), outline=(250, 240, 230), width=3)
    draw.ellipse([215, 55, 365, 205], fill=(60, 195, 110), outline=(20, 40, 30), width=3)
    draw.polygon([(390, 195), (455, 65), (325, 265)], fill=(240, 200, 50))
    for i in range(6):
        x0 = 40 + i * 70
        shade = 30 + i * 40
        draw.rectangle([x0, 230, x0 + 55, 290], fill=(shade, shade, shade))
    return np.asarray(img, dtype=np.float64)


def get_sample_images():
    rng = np.random.default_rng(42)
    base = _base_scene()

    low_contrast = np.clip(95.0 + (base / 255.0) * 65.0, 0, 255).astype(np.uint8)
    dark_underexposed = np.clip(base * 0.28, 0, 255).astype(np.uint8)
    overexposed = np.clip(150.0 + base * 0.41, 0, 255).astype(np.uint8)

    gauss_noise = np.clip(base + rng.normal(0.0, 26.0, base.shape), 0, 255).astype(np.uint8)

    sp_noise = base.copy()
    mask = rng.random(base.shape[:2])
    sp_noise[mask < 0.03] = 0.0
    sp_noise[mask > 0.97] = 255.0
    sp_noise = sp_noise.astype(np.uint8)

    return {
        "Цветная сцена (эталон)": Image.fromarray(base.astype(np.uint8), mode="RGB"),
        "Малоконтрастное (узкий диапазон)": Image.fromarray(low_contrast, mode="RGB"),
        "Тёмное (недодержанное)": Image.fromarray(dark_underexposed, mode="RGB"),
        "Засвеченное (передержанное)": Image.fromarray(overexposed, mode="RGB"),
        "Гауссовский шум (σ = 26)": Image.fromarray(gauss_noise, mode="RGB"),
        "Импульсный шум (соль и перец)": Image.fromarray(sp_noise, mode="RGB"),
    }
