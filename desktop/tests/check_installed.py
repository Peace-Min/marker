"""Acceptance check using only an installed interpreter, engine and model set."""
import argparse
import json
from pathlib import Path
import re
from check_engine import fixtures, run_case

parser = argparse.ArgumentParser()
parser.add_argument('installation', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
root, output = args.installation.resolve(), args.output.resolve()
assert (root / 'Marker.Desktop.exe').is_file() or (root / 'Marker.Desktop').is_file()
assert (root / 'Wiki/README.html').is_file() and (root / 'Wiki/README.en.html').is_file()
inputs = output / '입력 files'
fixtures(inputs)
report = run_case(root / 'engine', output, 'installed-digital-scan-debug',
                  [inputs / '그림 포함.pdf', inputs / '스캔 이미지.png'], disable=False, debug=True)
results = output / 'installed-digital-scan-debug/results'
markdown = list(results.rglob('*.md'))
assert len(markdown) == 2
for path in markdown:
    text = path.read_text(encoding='utf-8')
    assert 'Offline conversion succeeded.' in text, (path, text)
    for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text):
        assert (path.parent / image).is_file()
assert list(results.rglob('pdf_page_0.png')), 'Debug page image was not saved'
(output / 'installed-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS installed engine, image links, scanned OCR, debug files, and offline Wiki', flush=True)
