import argparse
from pathlib import Path
import re
import markdown2

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
docs = Path(__file__).resolve().parents[1] / "docs"
args.output.mkdir(parents=True, exist_ok=True)
style = "body{font-family:Segoe UI,Noto Sans,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;line-height:1.7;color:#233047}a{color:#2857c5}pre{overflow:auto;padding:16px;background:#f2f5fa}code{background:#f2f5fa}h1,h2{line-height:1.3}li{margin:8px 0}"
for path in docs.glob("*.md"):
    source = path.read_text(encoding="utf-8")
    html = str(markdown2.markdown(source, extras=["fenced-code-blocks", "tables"]))
    html = re.sub(r'href="([^"#]+)\.md([#"]?)', r'href="\1.html\2', html)
    (args.output / (path.stem + ".html")).write_text(f'<!doctype html><html lang="en" charset="utf-8"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Marker Desktop Wiki</title><style>{style}</style><body>{html}</body></html>', encoding="utf-8")
print("Offline HTML Wiki built", args.output)
