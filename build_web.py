"""
Build the game bundle for browser deployment.
Run once to set up, then re-run after any code change.
"""
import zipfile, tarfile, os, shutil, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
BUILD = ROOT / "build" / "web"
CDN   = BUILD / "cdn" / "cp312"
WHEEL = "pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"
WHEEL_URL = f"https://pygame-web.github.io/cdn/cp312/{WHEEL}"

SKIP_DIRS  = {".venv", "build", ".git", ".vscode", "__pycache__", "scripts"}
SKIP_EXTS  = {".pyc", ".pyx", ".pyd", ".pyi", ".exe", ".bak", ".log", ".blend", ".so"}

def collect_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel_dir = Path(dirpath).relative_to(ROOT)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if Path(fname).suffix in SKIP_EXTS or fname.startswith("."):
                continue
            files.append((Path(dirpath) / fname, rel_dir / fname))
    return files

def build_bundles(files):
    BUILD.mkdir(parents=True, exist_ok=True)
    apk = BUILD / "hexempire.apk"
    tgz = BUILD / "hexempire.tar.gz"

    with zipfile.ZipFile(apk, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for full, rel in files:
            zf.write(full, f"assets/{rel}")

    with tarfile.open(tgz, "w:gz") as tf:
        for full, rel in files:
            tf.add(full, arcname=f"assets/{rel}")

    print(f"  APK:    {apk}  ({apk.stat().st_size // 1024} KB, {len(files)} files)")
    print(f"  tar.gz: {tgz}  ({tgz.stat().st_size // 1024} KB)")

def ensure_index_html():
    """Copy template.tmpl to build/web/index.html, or warn if the template is missing."""
    tmpl = ROOT / "template.tmpl"
    dest = BUILD / "index.html"
    if tmpl.is_file():
        shutil.copyfile(tmpl, dest)
        print(f"  HTML:   copied template.tmpl → {dest}")
    elif not dest.exists():
        print("\nWARNING: template.tmpl not found and build/web/index.html is missing.")
        print("Run this once to generate the HTML shell:")
        print("  .venv/bin/python -m pygbag --port 8000 --template template.tmpl main.py")
        print("Wait for 'Serving python files' then Ctrl+C.\n")

def ensure_wheel():
    CDN.mkdir(parents=True, exist_ok=True)
    dest = CDN / WHEEL
    if dest.exists():
        print(f"  Wheel:  already cached ({dest.stat().st_size // 1024} KB)")
        return
    print(f"  Wheel:  downloading {WHEEL} ...")
    urllib.request.urlretrieve(WHEEL_URL, dest)
    print(f"  Wheel:  {dest.stat().st_size // 1024} KB downloaded")

if __name__ == "__main__":
    print("=== Building hexempire web bundle ===")
    files = collect_files()
    print(f"\nBundling {len(files)} files...")
    build_bundles(files)
    print("\nChecking pygame_ce WASM wheel...")
    ensure_wheel()
    ensure_index_html()
    print("\nDone. Serve with:")
    print("  python -m http.server 8000 --directory build/web")
    print("Then open: http://localhost:8000")
