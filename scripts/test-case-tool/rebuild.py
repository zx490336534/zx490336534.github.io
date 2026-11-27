"""Rebuild the embedded standalone app. Pass a local next-ai-test-cases checkout."""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path


BASE = "f4de4e1e45c3766e10880c0aacbcae6271cede69"  # v0.2.3
HERE = Path(__file__).resolve().parent
PAGE = HERE.parents[1] / "tools/test-cases/index.html"
APP = re.compile(r'(<div id="root"></div>\s*<noscript>[^<]*</noscript>\s*<script>)(.*?)(</script>)', re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    upstream = parser.parse_args().upstream.resolve()
    original = PAGE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "app"
        subprocess.run(["git", "clone", "--quiet", "--no-checkout", "--local", str(upstream), source], check=True)
        subprocess.run(["git", "checkout", "--quiet", "--detach", BASE], cwd=source, check=True)
        subprocess.run(["git", "apply", HERE / "composer-draft.patch"], cwd=source, check=True)
        subprocess.run(["pnpm", "install", "--frozen-lockfile"], cwd=source, check=True)
        subprocess.run(["node", "scripts/build-html.mjs"], cwd=source, check=True)
        built = (source / "dist/next-ai-test-cases.html").read_text(encoding="utf-8")
    bundle = APP.search(built)
    if not bundle or len(APP.findall(original)) != 1:
        raise ValueError("Expected one embedded workspace script")
    # The surrounding page carries blog navigation, analytics and the search-engine description.
    updated = APP.sub(lambda match: match[1] + bundle[2] + match[3], original)
    if updated != original:
        PAGE.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
