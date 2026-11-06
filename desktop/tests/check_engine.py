"""Integration QA against the actual portable engine, with empty model caches."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def make_pdf(path, image=None):
    stream = b'BT /F1 24 Tf 60 740 Td (Marker offline document) Tj 0 -40 Td /F1 14 Tf (Offline conversion succeeded.) Tj ET'
    resources = b'/Font << /F1 4 0 R >>'
    if image:
        resources += b' /XObject << /Im1 6 0 R >>'
        stream += b' q 480 0 0 380 60 220 cm /Im1 Do Q'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << ' + resources + b' >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream']
    if image:
        objects.append(b'<< /Type /XObject /Subtype /Image /Width 800 /Height 600 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n' % len(image) + image + b'\nendstream')
    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(data)
    data.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    path.write_bytes(data)


def fixtures(folder):
    from PIL import Image, ImageDraw, ImageFont
    folder.mkdir(parents=True, exist_ok=True)
    make_pdf(folder / '일반 문서.pdf')
    image = Image.new('RGB', (800, 600), '#e7eef9')
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 300, 240, 500), fill='#2452c4')
    draw.rectangle((300, 180, 440, 500), fill='#32795d')
    draw.rectangle((500, 80, 640, 500), fill='#e9a440')
    draw.line((60, 510, 740, 510), fill='black', width=5)
    jpg = io.BytesIO()
    image.save(jpg, format='JPEG')
    make_pdf(folder / '그림 포함.pdf', jpg.getvalue())
    image = Image.new('RGB', (1000, 400), 'white')
    draw = ImageDraw.Draw(image)
    font_path = 'C:/Windows/Fonts/arial.ttf' if os.name == 'nt' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 32)
    draw.multiline_text((60, 80), 'Marker offline document\nOffline conversion succeeded.', font=font, fill='black', spacing=25)
    image.save(folder / '스캔 이미지.png')
    (folder / '손상.pdf').write_bytes(b'This is not a PDF')


def run_case(engine, folder, name, files, *, fmt='markdown', disable=True, force=False, mode='fast', pages='', expected=0, debug=False):
    run = folder / name
    run.mkdir(parents=True, exist_ok=True)
    request = {'files': [str(item.resolve()) for item in files], 'output': str((run / 'results').resolve()),
               'format': fmt, 'mode': mode, 'force_ocr': force, 'disable_ocr': disable,
               'strip_existing_ocr': False, 'keep_headers': False, 'debug': debug, 'page_range': pages}
    request_path = run / 'request.json'
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
    python = engine / ('python/python.exe' if os.name == 'nt' else 'python/bin/python3')
    environment = os.environ.copy()
    environment.update(MARKER_RUNTIME_DIR=str((run / 'runtime').resolve()), PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH', None)
    started = time.monotonic()
    result = subprocess.run([str(python), '-u', str(engine / 'worker.py'), '--request', str(request_path.resolve())],
                            cwd=run, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=900)
    (run / 'stdout.jsonl').write_text(result.stdout, encoding='utf-8')
    (run / 'stderr.log').write_text(result.stderr, encoding='utf-8')
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert result.returncode == expected, (name, result.returncode, result.stderr[-4000:])
    assert 'OFFLINE_POLICY' not in result.stderr, (name, 'unexpected external connection attempted')
    record = {'case': name, 'exit': result.returncode, 'seconds': round(time.monotonic() - started, 2), 'events': events}
    print('PASS', name, record['seconds'], 'seconds', flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--quick', action='store_true')
    parser.add_argument('--remaining', action='store_true', help='Resume at chunks after the digital/JSON/HTML cases already passed')
    args = parser.parse_args()
    engine, folder = args.engine.resolve(), args.output.resolve()
    source = folder / '입력 files'
    fixtures(source)
    reports = []
    if not args.remaining:
        reports.append(run_case(engine, folder, 'digital-and-images', [source / '일반 문서.pdf', source / '그림 포함.pdf', source / '일반 문서.pdf']))
    results = folder / 'digital-and-images/results'
    assert len(list(results.iterdir())) == 3, 'duplicate file names must not overwrite previous output'
    markdown = list(results.rglob('*.md'))
    assert all('Offline conversion succeeded.' in path.read_text(encoding='utf-8') for path in markdown)
    images = []
    for path in markdown:
        links = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8'))
        for link in links:
            assert (path.parent / link).is_file(), f'broken image reference: {link}'
            images.append(link)
    assert images, 'image-containing PDF must preserve an image'
    for fmt in (('chunks',) if args.remaining else ('json', 'html', 'chunks')):
        reports.append(run_case(engine, folder, fmt, [source / '일반 문서.pdf'], fmt=fmt))
        extension = 'html' if fmt == 'html' else 'json'
        outputs = [path for path in (folder / fmt / 'results').rglob('*.' + extension) if not path.name.endswith('_meta.json')]
        assert outputs
        text = outputs[0].read_text(encoding='utf-8')
        assert 'Offline conversion succeeded.' in text
        if extension == 'json':
            value = json.loads(text)
            if fmt == 'chunks':
                assert value['blocks'][0]['page'] == 0 and 'bbox' in value['blocks'][0]
    reports.append(run_case(engine, folder, 'invalid-file-continues', [source / '손상.pdf', source / '일반 문서.pdf'], expected=2))
    reports.append(run_case(engine, folder, 'invalid-page-range', [source / '일반 문서.pdf'], pages='4-1', expected=1))
    if not args.quick:
        reports.append(run_case(engine, folder, 'scan-ocr', [source / '스캔 이미지.png'], disable=False, force=True))
        scan = next((folder / 'scan-ocr/results').rglob('*.md')).read_text(encoding='utf-8')
        assert 'Offline conversion succeeded.' in scan
        reports.append(run_case(engine, folder, 'balanced', [source / '일반 문서.pdf'], disable=False, mode='balanced'))
    (folder / 'report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Engine QA complete', folder, flush=True)


if __name__ == '__main__':
    main()
