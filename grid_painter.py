import math
import matplotlib.pyplot as plt
import numpy as np


class GridPainter:
    @staticmethod
    def render(grid, overlay=None, title=""):
        matrix = grid.to_matrix()
        fig, ax = plt.subplots(figsize=(7.2, 7.2), dpi=130)
        extent = [grid.x_min - 0.5, grid.x_max + 0.5, grid.y_min - 0.5, grid.y_max + 0.5]
        ax.imshow(
            matrix,
            cmap="Greys",
            vmin=0.0,
            vmax=1.0,
            origin="lower",
            extent=extent,
            interpolation="nearest",
        )
        x_edges = np.arange(grid.x_min - 0.5, grid.x_max + 1.5, 1.0)
        y_edges = np.arange(grid.y_min - 0.5, grid.y_max + 1.5, 1.0)
        ax.set_xticks(x_edges, minor=True)
        ax.set_yticks(y_edges, minor=True)
        ax.grid(which="minor", color="#D0D7DE", linestyle="-", linewidth=0.6)
        ax.tick_params(which="minor", bottom=False, left=False)

        span = max(grid.width, grid.height)
        tick_step = 1 if span <= 35 else (2 if span <= 60 else 5)
        ax.set_xticks(np.arange(grid.x_min, grid.x_max + 1, tick_step))
        ax.set_yticks(np.arange(grid.y_min, grid.y_max + 1, tick_step))

        if grid.x_min <= 0 <= grid.x_max:
            ax.axvline(0, color="#1F6FEB", linewidth=1.2, alpha=0.8)
        if grid.y_min <= 0 <= grid.y_max:
            ax.axhline(0, color="#1F6FEB", linewidth=1.2, alpha=0.8)

        if overlay:
            kind = overlay.get("type")
            if kind == "line":
                ax.plot(
                    [overlay["x0"], overlay["x1"]],
                    [overlay["y0"], overlay["y1"]],
                    color="#CF222E",
                    linewidth=1.6,
                    linestyle="--",
                    label="Идеальный отрезок",
                )
                ax.scatter(
                    [overlay["x0"], overlay["x1"]],
                    [overlay["y0"], overlay["y1"]],
                    color="#CF222E",
                    s=32,
                    zorder=5,
                )
            elif kind == "circle":
                theta = np.linspace(0, 2 * math.pi, 360)
                cx = overlay["xc"] + overlay["r"] * np.cos(theta)
                cy = overlay["yc"] + overlay["r"] * np.sin(theta)
                ax.plot(cx, cy, color="#CF222E", linewidth=1.6, linestyle="--", label="Идеальная окружность")
                ax.scatter([overlay["xc"]], [overlay["yc"]], color="#CF222E", s=32, zorder=5)
            ax.legend(loc="upper right", fontsize=8)

        ax.set_xlim(grid.x_min - 0.5, grid.x_max + 0.5)
        ax.set_ylim(grid.y_min - 0.5, grid.y_max + 0.5)
        ax.set_xlabel("X (целочисленный центр пикселя = (x, y))")
        ax.set_ylabel("Y (целочисленный центр пикселя = (x, y))")
        ax.set_title(title, fontsize=11)
        fig.tight_layout()
        return fig
