import argparse
import json
import os
import sys
from datetime import datetime

# Allow importing the project sources without installing a wheel.
# The application code lives under /workspace/gk-healter/src as the `src` package.
_REPO_ROOT = os.environ.get("WORKSPACE", "/workspace")
_APP_ROOT = os.path.join(_REPO_ROOT, "gk-healter")
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from src.logger import setup_logging  # noqa: E402
from src.pardus_verifier import PardusVerifier  # noqa: E402
from src.security_scanner import SecurityScanner  # noqa: E402
from src.report_exporter import ReportExporter  # noqa: E402


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate offline security/verification reports inside container."
    )
    parser.add_argument(
        "--out-dir",
        default="/workspace/artifacts",
        help="Output directory for generated reports.",
    )
    parser.add_argument(
        "--tag",
        default="",
        help="Optional tag suffix for filenames (e.g. pre, post, low_bloat).",
    )
    args = parser.parse_args()

    setup_logging()
    out_dir = os.path.abspath(args.out_dir)
    _ensure_dir(out_dir)

    tag = args.tag.strip()
    if tag:
        tag = f"-{tag}"

    verifier = PardusVerifier()
    pv = verifier.verify()

    scanner = SecurityScanner()
    sec = scanner.run_full_scan()

    exporter = ReportExporter()
    data = exporter.collect_report_data(
        pardus_verification=pv,
        security_results=sec,
    )

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(out_dir, f"gk-healter-report-{ts}{tag}")

    txt_path = exporter.export_txt(data, base + ".txt")
    html_path = exporter.export_html(data, base + ".html")
    json_path = exporter.export_json(data, base + ".json")

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "tag": args.tag,
        "paths": {"txt": txt_path, "html": html_path, "json": json_path},
        "summary": sec.get("summary", {}),
        "is_pardus": bool(pv.get("is_pardus")),
        "pretty_name": pv.get("os_release", {}).get("PRETTY_NAME", "Unknown"),
    }
    with open(base + ".manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

