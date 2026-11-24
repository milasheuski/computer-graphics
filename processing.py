import numpy as np
from PIL import Image
from buffer import PixelBuffer


def separable_convolve(buffer, kernel_x, kernel_y, pad_strategy="reflect", workers=4):
    rx = len(kernel_x) // 2
    ry = len(kernel_y) // 2

    def pass_horizontal(padded):
        width = padded.shape[1] - 2 * rx
        out = np.zeros((padded.shape[0], width) + padded.shape[2:], dtype=np.float64)
        for i, weight in enumerate(kernel_x):
            out += padded[:, i:i + width] * weight
        return out

    horiz = buffer.parallel_strips(
        pass_horizontal,
        pad_y=0,
        pad_x=rx,
        strategy=pad_strategy,
        workers=workers
    )

    def pass_vertical(padded):
        height = padded.shape[0] - 2 * ry
        out = np.zeros((height,) + padded.shape[1:], dtype=np.float64)
        for j, weight in enumerate(kernel_y):
            out += padded[j:j + height, :] * weight
        return out

    return horiz.parallel_strips(
        pass_vertical,
        pad_y=ry,
        pad_x=0,
        strategy=pad_strategy,
        workers=workers
    )


def mean_filter(image, size, pad_strategy="reflect", workers=4):
    buf = PixelBuffer.from_image(image, "RGB")
    kernel_1d = np.ones(size, dtype=np.float64) / size
    return separable_convolve(buf, kernel_1d, kernel_1d, pad_strategy, workers).to_image("RGB")


def gaussian_filter(image, size, sigma, pad_strategy="reflect", workers=4):
    buf = PixelBuffer.from_image(image, "RGB")
    coords = np.arange(size, dtype=np.float64) - size // 2
    kernel_1d = np.exp(-(coords ** 2) / (2.0 * sigma ** 2))
    kernel_1d /= kernel_1d.sum()
    return separable_convolve(buf, kernel_1d, kernel_1d, pad_strategy, workers).to_image("RGB")


def histogram(image):
    pixels = np.asarray(image.convert("L"))
    return np.bincount(pixels.ravel(), minlength=256)


def linear_contrast(image):
    pixels = np.asarray(image.convert("L"), dtype=np.float64)
    minimum = pixels.min()
    maximum = pixels.max()
    if maximum == minimum:
        return image.convert("L")
    result = (pixels - minimum) * 255.0 / (maximum - minimum)
    return Image.fromarray(np.clip(np.rint(result), 0, 255).astype(np.uint8), mode="L")


def equalize_channel(channel):
    counts = np.bincount(channel.ravel(), minlength=256)
    cumulative = counts.cumsum()
    non_zero = cumulative[counts > 0]
    if non_zero.size == 0:
        return channel.copy()
    first = non_zero[0]
    if channel.size == first:
        return channel.copy()
    table = (cumulative - first) * 255.0 / (channel.size - first)
    table = np.clip(np.rint(table), 0, 255).astype(np.uint8)
    return table[channel]


def equalize_gray(image):
    pixels = np.asarray(image.convert("L"))
    return Image.fromarray(equalize_channel(pixels), mode="L")


def equalize_rgb(image):
    pixels = np.asarray(image.convert("RGB"))
    channels = [equalize_channel(pixels[:, :, i]) for i in range(3)]
    return Image.fromarray(np.stack(channels, axis=2), mode="RGB")


def rgb_to_hsv(rgb):
    arr = rgb.astype(np.float64) / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    h = np.zeros_like(cmax)
    mask = delta > 1e-12
    rm = mask & (cmax == r)
    gm = mask & (cmax == g) & (~rm)
    bm = mask & (~rm) & (~gm)

    h[rm] = ((g[rm] - b[rm]) / delta[rm]) % 6.0
    h[gm] = ((b[gm] - r[gm]) / delta[gm]) + 2.0
    h[bm] = ((r[bm] - g[bm]) / delta[bm]) + 4.0
    h = h / 6.0

    s = np.where(cmax > 1e-12, delta / cmax, 0.0)
    v = cmax
    return h, s, v


def hsv_to_rgb(h, s, v):
    h6 = (h * 6.0) % 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])

    rgb = np.stack([r, g, b], axis=2) * 255.0
    return np.clip(np.rint(rgb), 0, 255).astype(np.uint8)


def equalize_hsv(image):
    rgb = np.asarray(image.convert("RGB"))
    h, s, v = rgb_to_hsv(rgb)
    v_uint8 = np.clip(np.rint(v * 255.0), 0, 255).astype(np.uint8)
    v_eq = equalize_channel(v_uint8).astype(np.float64) / 255.0
    return Image.fromarray(hsv_to_rgb(h, s, v_eq), mode="RGB")


def clahe_channel(channel, grid_size=8, clip_limit=2.0):
    h, w = channel.shape
    gh = max(2, min(grid_size, h // 8))
    gw = max(2, min(grid_size, w // 8))

    tile_h = int(np.ceil(h / gh))
    tile_w = int(np.ceil(w / gw))
    pad_h = tile_h * gh - h
    pad_w = tile_w * gw - w
    padded = np.pad(channel, ((0, pad_h), (0, pad_w)), mode="reflect")

    luts = np.zeros((gh, gw, 256), dtype=np.float64)
    tile_pixels = tile_h * tile_w
    actual_clip = max(1, int(clip_limit * tile_pixels / 256.0))

    for ty in range(gh):
        for tx in range(gw):
            tile = padded[ty * tile_h:(ty + 1) * tile_h, tx * tile_w:(tx + 1) * tile_w]
            hist = np.bincount(tile.ravel(), minlength=256).astype(np.int64)
            excess = np.maximum(0, hist - actual_clip).sum()
            hist = np.minimum(hist, actual_clip)
            bonus, rem = divmod(int(excess), 256)
            hist += bonus
            if rem > 0:
                step = max(1, 256 // rem)
                hist[:rem * step:step] += 1
            cdf = hist.cumsum()
            cdf_min = cdf[hist > 0][0] if np.any(hist > 0) else 0
            denom = max(1, tile_pixels - cdf_min)
            luts[ty, tx] = np.clip((cdf - cdf_min) * 255.0 / denom, 0, 255)

    ys = (np.arange(h) + 0.5) / tile_h - 0.5
    xs = (np.arange(w) + 0.5) / tile_w - 0.5

    y0 = np.clip(np.floor(ys).astype(np.int32), 0, gh - 1)
    y1 = np.clip(y0 + 1, 0, gh - 1)
    wy = np.clip(ys - y0, 0.0, 1.0)[:, None]

    x0 = np.clip(np.floor(xs).astype(np.int32), 0, gw - 1)
    x1 = np.clip(x0 + 1, 0, gw - 1)
    wx = np.clip(xs - x0, 0.0, 1.0)[None, :]

    yy0, xx0 = np.meshgrid(y0, x0, indexing="ij")
    yy1, xx1 = np.meshgrid(y1, x1, indexing="ij")

    c00 = luts[yy0, xx0, channel]
    c01 = luts[yy0, xx1, channel]
    c10 = luts[yy1, xx0, channel]
    c11 = luts[yy1, xx1, channel]

    top = c00 * (1.0 - wx) + c01 * wx
    bottom = c10 * (1.0 - wx) + c11 * wx
    result = top * (1.0 - wy) + bottom * wy
    return np.clip(np.rint(result), 0, 255).astype(np.uint8)


def clahe_gray(image, grid_size=8, clip_limit=2.0):
    pixels = np.asarray(image.convert("L"))
    return Image.fromarray(clahe_channel(pixels, grid_size, clip_limit), mode="L")


def clahe_rgb(image, grid_size=8, clip_limit=2.0):
    pixels = np.asarray(image.convert("RGB"))
    channels = [clahe_channel(pixels[:, :, i], grid_size, clip_limit) for i in range(3)]
    return Image.fromarray(np.stack(channels, axis=2), mode="RGB")


def clahe_hsv(image, grid_size=8, clip_limit=2.0):
    rgb = np.asarray(image.convert("RGB"))
    h, s, v = rgb_to_hsv(rgb)
    v_uint8 = np.clip(np.rint(v * 255.0), 0, 255).astype(np.uint8)
    v_clahe = clahe_channel(v_uint8, grid_size, clip_limit).astype(np.float64) / 255.0
    return Image.fromarray(hsv_to_rgb(h, s, v_clahe), mode="RGB")