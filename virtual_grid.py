import numpy as np


class VirtualGrid:
    def __init__(self, x_min=-15, x_max=15, y_min=-15, y_max=15, record_steps=False):
        self.x_min = int(x_min)
        self.x_max = int(x_max)
        self.y_min = int(y_min)
        self.y_max = int(y_max)
        self.width = self.x_max - self.x_min + 1
        self.height = self.y_max - self.y_min + 1
        self.record_steps = record_steps
        self.buffer = [0.0] * (self.width * self.height)
        self.steps = []

    def clear(self):
        self.buffer = [0.0] * (self.width * self.height)
        self.steps = []

    def set_pixel(self, x, y, intensity=1.0, info=None):
        ix = int(x)
        iy = int(y)
        if self.x_min <= ix <= self.x_max and self.y_min <= iy <= self.y_max:
            idx = (iy - self.y_min) * self.width + (ix - self.x_min)
            val = float(intensity)
            if val > self.buffer[idx]:
                self.buffer[idx] = val
        if self.record_steps:
            row = {
                "Шаг": len(self.steps) + 1,
                "X": ix,
                "Y": iy,
                "Интенсивность": round(float(intensity), 3),
            }
            if info:
                row.update(info)
            self.steps.append(row)

    def to_matrix(self):
        return np.array(self.buffer, dtype=np.float64).reshape((self.height, self.width))
