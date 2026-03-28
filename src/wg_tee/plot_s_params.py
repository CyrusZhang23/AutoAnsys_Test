"""
S 参数曲线图（Matplotlib）

- ``load_s_csv``：自动识别分号或逗号分隔；按表头匹配 ``Freq`` 与 ``dB(S(i,j))``（忽略 imag 列）。
- ``plot_s_params``：绘制 S11、S21、S31，默认输出 JPG。

不依赖 PyAEDT；便于在仅有 CSV 时重画图。

CLI：``wg-plot-s``；``wg-run-sim`` 在求解后自动调用 ``plot_s_params``。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from wg_tee.paths import default_hfss_project_path, resolve_s_params_csv

# Headers from PyAEDT ``export_data_to_csv`` for dB(S(i,j)) traces.
_SPAIR = (
    (1, 1, "S11"),
    (2, 1, "S21"),
    (3, 1, "S31"),
)


def _find_col(headers: list[str], pred) -> int | None:
    for i, h in enumerate(headers):
        if pred(h):
            return i
    return None


def _column_for_sij(headers: list[str], i: int, j: int) -> int | None:
    """Match ``dB(S(1,1))``-style column (real part only for dB)."""
    pat = re.compile(rf"S\s*\(\s*{i}\s*,\s*{j}\s*\)", re.IGNORECASE)

    def ok(h: str) -> bool:
        if "imag" in h.lower():
            return False
        return pat.search(h) is not None

    return _find_col(headers, ok)


def _freq_col(headers: list[str]) -> int | None:
    return _find_col(headers, lambda h: "freq" in h.lower())


def load_s_csv(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    path = path.resolve()
    with path.open(newline="", encoding="utf-8-sig") as f:
        first = f.readline()
        f.seek(0)
        delim = ";" if first.count(";") >= first.count(",") else ","
        reader = csv.reader(f, delimiter=delim)
        try:
            headers = next(reader)
        except StopIteration as e:
            raise ValueError(f"Empty file: {path}") from e
        rows = list(reader)
    if not headers:
        raise ValueError("Empty header")
    if not rows:
        raise ValueError(f"No data rows in {path}")

    ic = _freq_col(headers)
    if ic is None:
        raise ValueError(f"No frequency column (expected 'Freq' in header): {headers}")

    col_idx: dict[str, int] = {}
    for ii, jj, label in _SPAIR:
        jc = _column_for_sij(headers, ii, jj)
        if jc is None:
            raise ValueError(f"No column found for S({ii},{jj}) in header: {headers}")
        col_idx[label] = jc

    freq: list[float] = []
    series: dict[str, list[float]] = {lb: [] for _, _, lb in _SPAIR}

    for parts in rows:
        if ic >= len(parts):
            continue
        try:
            fq = float(parts[ic])
        except ValueError:
            continue
        freq.append(fq)
        for _, _, label in _SPAIR:
            jc = col_idx[label]
            if jc >= len(parts):
                series[label].append(float("nan"))
                continue
            try:
                series[label].append(float(parts[jc]))
            except ValueError:
                series[label].append(float("nan"))

    if not freq:
        raise ValueError("No numeric frequency samples parsed")
    return freq, series


def plot_s_params(
    csv_path: Path,
    image_path: Path | None,
    *,
    title: str | None = None,
    image_format: str = "jpeg",
) -> Path:
    import matplotlib.pyplot as plt

    freq_ghz, series = load_s_csv(csv_path)
    ext = ".jpg" if image_format.lower() in ("jpeg", "jpg") else ".png"
    out = image_path or csv_path.with_suffix(ext)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for label in ("S11", "S21", "S31"):
        if label in series and len(series[label]) == len(freq_ghz):
            ax.plot(freq_ghz, series[label], label=label)
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("dB")
    ax.grid(True, which="both", alpha=0.35)
    ax.legend()
    ax.set_title(title or csv_path.name)

    fmt = "jpeg" if image_format.lower() in ("jpeg", "jpg") else "png"
    fig.savefig(out, dpi=150, format=fmt)
    plt.close(fig)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot S11/S21/S31 (dB) from HFSS-exported CSV")
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help=f"Input CSV (default: {resolve_s_params_csv(default_hfss_project_path(), None)})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output image path (default: same basename as CSV, extension from --format)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=("jpg", "jpeg", "png"),
        default="jpg",
        help="Image format (default: jpg)",
    )
    parser.add_argument("--title", type=str, default=None, help="Figure title")
    args = parser.parse_args()

    csv_path = args.csv or resolve_s_params_csv(default_hfss_project_path(), None)
    if not csv_path.is_file():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    fmt = "jpeg" if args.format in ("jpg", "jpeg") else "png"
    out = plot_s_params(csv_path, args.output, title=args.title, image_format=fmt)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
