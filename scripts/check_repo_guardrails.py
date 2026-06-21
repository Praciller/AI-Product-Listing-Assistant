import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGES = ("docs/screenshots/", "fixtures/images/", "tests/fixtures/images/")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".ppm"}
DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SECRET_PATTERNS = (
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rb"sk-[0-9A-Za-z_-]{20,}"),
    re.compile(rb"gh[pousr]_[0-9A-Za-z]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
UNSAFE_CLAIMS = (
    re.compile(r"guaranteed SEO ranking", re.I),
    re.compile(r"production-ready listing automation", re.I),
    re.compile(r"guaranteed marketplace[- ]approval", re.I),
)


def repository_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / name.decode() for name in result.stdout.split(b"\0") if name]


def check_file(path: Path) -> list[str]:
    if not path.is_file():
        return []

    relative = path.relative_to(ROOT).as_posix()
    lower = relative.lower()
    issues = []
    if lower == ".env" or (lower.startswith(".env.") and lower != ".env.example"):
        issues.append(f"tracked environment file: {relative}")
    if any(part in {"upload", "uploads", "uploaded-images", "uploaded_product_images"} for part in Path(lower).parts):
        issues.append(f"private upload path: {relative}")
    if path.suffix.lower() in IMAGE_SUFFIXES and not lower.startswith(ALLOWED_IMAGES):
        issues.append(f"image outside approved fixture/screenshot path: {relative}")
    if path.suffix.lower() in DB_SUFFIXES:
        issues.append(f"local database file: {relative}")
    if path.stat().st_size > MAX_SIZE:
        issues.append(f"file exceeds 5 MiB: {relative}")

    content = path.read_bytes()
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        issues.append(f"possible secret value: {relative}")
    if relative != "scripts/check_repo_guardrails.py" and path.suffix.lower() in {
        ".md", ".py", ".ts", ".tsx", ".toml", ".yml", ".yaml"
    }:
        text = content.decode("utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in UNSAFE_CLAIMS):
            issues.append(f"unsafe unqualified claim: {relative}")
    return issues


def main() -> int:
    issues = [issue for path in repository_files() for issue in check_file(path)]
    if issues:
        print("Repository guardrails failed:")
        print("\n".join(f"- {issue}" for issue in issues))
        return 1
    print("Repository guardrails passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
