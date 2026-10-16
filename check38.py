"""Limited fixture checks, not a validator for real PDFs or feature preservation."""
import hashlib
import json
import sys
from pathlib import Path
from pypdf import PdfReader


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pages(path):
    return [(p.extract_text().strip(), tuple(float(x) for x in p.mediabox), int(p.get('/Rotate', 0)) % 360)
            for p in PdfReader(path).pages]


def verify(root):
    sources = [root / (name + '.pdf') for name in ['contract', 'invoice', 'notes']]
    before = json.loads((root / 'sources.sha256.json').read_text())
    assert before == {p.name: digest(p) for p in sources}, 'Source bytes changed'
    original = sum((pages(p) for p in sources), [])
    expected = ['FICTIONAL CONTRACT - PAGE 1', 'FICTIONAL CONTRACT - PAGE 2',
        'FICTIONAL INVOICE - PAGE 1', 'FICTIONAL INVOICE - PAGE 2',
        'FICTIONAL INVOICE - PAGE 3', 'FICTIONAL NOTES - PAGE 1']
    assert [x[0] for x in original] == expected, 'Unexpected fixture labels'
    assert pages(root / 'merged.pdf') == original, 'Merged content/order/geometry/rotation differs'
    assert pages(root / 'first.pdf') == original[:2], 'Split content/order differs'
    notes = pages(root / 'notes.pdf')[0]
    assert pages(root / 'rotated.pdf') == [(notes[0], notes[1], (notes[2] + 90) % 360)], 'Rotation differs'
    print('PASS: all source SHA256 digests unchanged; six fixture labels and their order match.')
    print('PASS: merged page geometry/rotation match; split selects first two labels; notes rotation is 90 degrees.')
    print('These checks do not prove visual appearance or document-feature preservation. Inspect the PDFs.')


def snapshot(root):
    manifest = root / 'sources.sha256.json'
    try:
        manifest.lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(manifest)
    data = {name + '.pdf': digest(root / (name + '.pdf')) for name in ['contract', 'invoice', 'notes']}
    with manifest.open('x', encoding='ascii') as handle:
        json.dump(data, handle, sort_keys=True)
    print('Saved source SHA256 digests in a new manifest; existing manifests are refused.')


if __name__ == '__main__':
    root = Path(__file__).resolve().parent / 'sample'
    if sys.argv[1:] == ['snapshot']:
        snapshot(root)
    elif sys.argv[1:] == ['verify']:
        verify(root)
    else:
        raise SystemExit('Usage: python check38.py snapshot|verify')
