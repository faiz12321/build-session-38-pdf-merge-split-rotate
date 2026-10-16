"""Create three small fictional labeled PDFs only in a NEW sample folder.

Every existing sample path is refused. Files are created exclusively.
An interrupted setup can leave a partial new folder; do not delete old
work to force a retry. Start in a different new empty lesson folder.
"""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def make(path, labels, size):
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    for label in labels:
        page = writer.add_blank_page(width=size[0], height=size[1])
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):
            DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        content = DecodedStreamObject()
        content.set_data(('BT /F1 22 Tf 60 650 Td (%s) Tj ET' % label).encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(content)
    with Path(path).open('xb') as handle:
        writer.write(handle)


def setup(root):
    root = Path(root)
    root.mkdir()
    make(root / 'contract.pdf', ['FICTIONAL CONTRACT - PAGE 1', 'FICTIONAL CONTRACT - PAGE 2'], (612, 792))
    make(root / 'invoice.pdf', ['FICTIONAL INVOICE - PAGE 1', 'FICTIONAL INVOICE - PAGE 2', 'FICTIONAL INVOICE - PAGE 3'], (595, 842))
    make(root / 'notes.pdf', ['FICTIONAL NOTES - PAGE 1'], (612, 792))


if __name__ == '__main__':
    try:
        setup(Path(__file__).resolve().parent / 'sample')
    except FileExistsError:
        raise SystemExit('Stopped: sample already exists. Nothing was replaced or deleted.')
    print('Created three fictional labeled PDFs in a new sample folder (2, 3 and 1 pages).')
