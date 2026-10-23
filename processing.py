import numpy as np
from PIL import Image


def apply_filter(image, kernel):
    pixels = np.asarray(image.convert("RGB"), dtype=float)

    border = kernel.shape[0] // 2
    padded = np.pad(
        pixels,
        ((border, border), (border, border), (0, 0)),
        mode="edge"
    )

    height, width = pixels.shape[:2]
    result = np.zeros_like(pixels)

    for y in range(kernel.shape[0]):
        for x in range(kernel.shape[1]):
            result += (
                padded[y:y + height, x:x + width]
                * kernel[y, x]
            )

    result = np.clip(np.rint(result), 0, 255).astype(np.uint8)

    return Image.fromarray(result)


def mean_filter(image, size):
    kernel = np.ones((size, size)) / (size * size)

    return apply_filter(image, kernel)


def gaussian_filter(image, size, sigma):
    coordinates = np.arange(size) - size // 2
    x, y = np.meshgrid(coordinates, coordinates)

    kernel = np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()

    return apply_filter(image, kernel)


def histogram(image):
    pixels = np.asarray(image.convert("L"))

    return np.bincount(pixels.ravel(), minlength=256)


def linear_contrast(image):
    pixels = np.asarray(image.convert("L"), dtype=float)

    minimum = pixels.min()
    maximum = pixels.max()

    if maximum == minimum:
        return image.convert("L")

    result = (pixels - minimum) * 255 / (maximum - minimum)
    result = np.clip(np.rint(result), 0, 255).astype(np.uint8)

    return Image.fromarray(result)


def equalize_channel(channel):
    counts = np.bincount(channel.ravel(), minlength=256)
    cumulative = counts.cumsum()

    first = cumulative[counts > 0][0]

    if channel.size == first:
        return channel.copy()

    table = (cumulative - first) * 255 / (channel.size - first)
    table = np.clip(np.rint(table), 0, 255).astype(np.uint8)

    return table[channel]


def equalize_gray(image):
    pixels = np.asarray(image.convert("L"))

    return Image.fromarray(equalize_channel(pixels))


def equalize_rgb(image):
    pixels = np.asarray(image.convert("RGB"))

    channels = [
        equalize_channel(pixels[:, :, i])
        for i in range(3)
    ]

    return Image.fromarray(np.stack(channels, axis=2))


def equalize_hsv(image):
    pixels = np.array(image.convert("RGB").convert("HSV"))
    pixels[:, :, 2] = equalize_channel(pixels[:, :, 2])

    return Image.frombytes(
        "HSV",
        image.size,
        pixels.tobytes()
    ).convert("RGB")