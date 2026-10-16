"""Small PDF page tool. Use only trusted, backed-up, ordinary PDFs.

count FILE... | merge OUT IN... | split IN OUT FIRST-LAST |
rotate IN OUT DEGREES [--page N]

Outputs are created exclusively: every existing destination is refused,
including an input path or a link. Inputs and their links are read, not
rewritten. This copies pages, not the whole PDF document: signatures,
forms, outlines, metadata and other document features are not promised.
Counts alone do not prove content or order. Inspect the saved result.
PDFs are processed in memory. No network, upload or sandbox is provided.
A disk/write failure can leave a partial NEW output; it is not deleted.
"""
import argparse
import io
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError


def reader(path):
    if not Path(path).is_file():
        raise ValueError('Input must be an existing regular file (links are followed).')
    pdf = PdfReader(path)
    if pdf.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported by this lesson.')
    return pdf


def save_new(writer, path):
    # Check links themselves: Windows xb may follow a dangling symlink.
    # This check plus exclusive creation is not a hostile-race guarantee.
    try:
        Path(path).lstat()
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(path)
    # Finish serialization before creating a new destination.
    data = io.BytesIO()
    writer.write(data)
    with open(path, 'xb') as handle:
        handle.write(data.getvalue())


def count(paths):
    counts = [(path, len(reader(path).pages)) for path in paths]
    for path, n in counts:
        print('%s: %d page%s' % (path, n, '' if n == 1 else 's'))
    if len(counts) > 1:
        print('Total: %d pages' % sum(n for _, n in counts))


def merge(out, inputs):
    writer = PdfWriter()
    for path in inputs:
        for page in reader(path).pages:
            writer.add_page(page)
    save_new(writer, out)
    print('Wrote %s with %d pages.' % (out, len(writer.pages)))


def split(source, out, page_range):
    parts = page_range.split('-')
    if len(parts) > 2 or not all(p.isascii() and p.isdigit() for p in parts):
        raise ValueError('Range must be a positive page number or FIRST-LAST.')
    first, last = int(parts[0]), int(parts[-1])
    pdf = reader(source)
    if not 1 <= first <= last <= len(pdf.pages):
        raise ValueError('Range %s does not fit %d pages.' % (page_range, len(pdf.pages)))
    writer = PdfWriter()
    for page in pdf.pages[first - 1:last]:
        writer.add_page(page)
    save_new(writer, out)
    print('Wrote %s with source pages %d-%d.' % (out, first, last))


def rotate(source, out, degrees, page_no):
    pdf = reader(source)
    if page_no is not None and not 1 <= page_no <= len(pdf.pages):
        raise ValueError('Requested page does not exist.')
    writer = PdfWriter()
    for i, page in enumerate(pdf.pages, 1):
        if page_no is None or i == page_no:
            page.rotate(degrees)
        writer.add_page(page)
    save_new(writer, out)
    print('Wrote %s; rotated %s by %d degrees.' % (out, 'all pages' if page_no is None else 'page %d' % page_no, degrees))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('count'); p.add_argument('inputs', nargs='+')
    p = sub.add_parser('merge'); p.add_argument('out'); p.add_argument('inputs', nargs='+')
    p = sub.add_parser('split'); p.add_argument('source'); p.add_argument('out'); p.add_argument('page_range')
    p = sub.add_parser('rotate'); p.add_argument('source'); p.add_argument('out'); p.add_argument('degrees', type=int, choices=[90, 180, 270]); p.add_argument('--page', type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == 'count': count(args.inputs)
        elif args.command == 'merge': merge(args.out, args.inputs)
        elif args.command == 'split': split(args.source, args.out, args.page_range)
        else: rotate(args.source, args.out, args.degrees, args.page)
    except FileExistsError:
        print('Stopped: destination already exists. Nothing was replaced.', file=sys.stderr)
        return 1
    except (OSError, ValueError, PyPdfError) as error:
        print('Stopped: %s' % error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
