"""Limited fixture checks, not a validator for real PDFs or feature preservation."""
import hashlib
import json
import sys
import stat
from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PyPdfError


def safe_input(value, directory=False):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Links/reparse points are unsupported.')
    info = path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise NotADirectoryError('Expected an ordinary directory.')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise OSError('Expected an ordinary singly linked file.')
    return path

def safe_output(value):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    safe_input(path.parent, directory=True)
    return Path(value)


def digest(path):
    return hashlib.sha256(safe_input(path).read_bytes()).hexdigest()


def pages(path):
    return [(p.extract_text().strip(), tuple(float(x) for x in p.mediabox), int(p.get('/Rotate', 0)) % 360)
            for p in PdfReader(safe_input(path)).pages]


def verify(root):
    root = safe_input(root, directory=True)
    sources = [root / (name + '.pdf') for name in ['contract', 'invoice', 'notes']]
    before = json.loads(safe_input(root / 'sources.sha256.json').read_text())
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
    root = safe_input(root, directory=True)
    manifest = safe_output(root / 'sources.sha256.json')
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


def main(argv):
    if argv not in (['snapshot'], ['verify']):
        print('Usage: python check38.py snapshot|verify', file=sys.stderr)
        return 2
    try:
        root = Path(__file__).absolute().parent / 'sample'
        if argv == ['snapshot']:
            snapshot(root)
        else:
            verify(root)
    except (OSError, ValueError, AssertionError, PyPdfError) as error:
        print('Stopped: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
