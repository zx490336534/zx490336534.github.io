"""Optional lower-bandwidth covers for high-traffic editorial listings (requires cwebp)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1] / "images"
COVERS = ROOT / "article-covers"
VARIANTS = ROOT / "cover-variants"
WIDTHS = (384, 768)


def render(path):
    results = []
    for width in WIDTHS:
        dest = VARIANTS / str(width) / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".tmp")
        subprocess.run(["cwebp", "-quiet", "-q", "76", "-resize", str(width), "0", "-metadata", "none",
                        str(path), "-o", str(tmp)], check=True)
        if tmp.stat().st_size < path.stat().st_size:
            tmp.replace(dest)
            results.append((path.stat().st_size, dest.stat().st_size))
        else:
            tmp.unlink()
            dest.unlink(missing_ok=True)
    return results


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = [result for group in pool.map(render, COVERS.glob("*.webp")) for result in group]
    print(f"{len(rows)} smaller WebP variants; {sum(n for _, n in rows):,} bytes total")
