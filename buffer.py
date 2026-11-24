from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image


class PixelBuffer:
    def __init__(self, array):
        self.data = np.asarray(array, dtype=np.float64)

    @classmethod
    def from_image(cls, image, mode="RGB"):
        return cls(np.asarray(image.convert(mode), dtype=np.float64))

    def to_image(self, mode="RGB"):
        clipped = np.clip(np.rint(self.data), 0, 255).astype(np.uint8)
        return Image.fromarray(clipped, mode=mode)

    @property
    def shape(self):
        return self.data.shape

    def pad(self, pad_y, pad_x, strategy="reflect"):
        mode = "reflect" if strategy.lower() == "reflect" else "edge"
        if self.data.ndim == 3:
            spec = ((pad_y, pad_y), (pad_x, pad_x), (0, 0))
        else:
            spec = ((pad_y, pad_y), (pad_x, pad_x))
        return np.pad(self.data, spec, mode=mode)

    def parallel_strips(self, func, pad_y=0, pad_x=0, strategy="reflect", workers=4):
        height = self.data.shape[0]
        padded = self.pad(pad_y, pad_x, strategy)
        if workers <= 1 or height < 64:
            return PixelBuffer(func(padded))
        step = max(1, (height + workers - 1) // workers)
        ranges = [
            (y, min(height, y + step))
            for y in range(0, height, step)
        ]

        def run_strip(bounds):
            y0, y1 = bounds
            return func(padded[y0:y1 + 2 * pad_y])

        with ThreadPoolExecutor(max_workers=workers) as pool:
            parts = list(pool.map(run_strip, ranges))
        return PixelBuffer(np.concatenate(parts, axis=0))
