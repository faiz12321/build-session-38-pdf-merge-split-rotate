# Merge, split and rotate fictional PDF pages locally

Small Python page-copying practice, using three generated fictional PDFs. It is not a whole-document converter, backup or PDF security sandbox.

## Before you practise

Use a new empty lesson folder and Python 3.12. In your chosen Python environment, install the pinned dependency:

    python -m pip install pypdf==6.19.0

Installation downloads a third-party dependency. The visible PDF commands process files locally, with no upload or network code; that does not control cloud sync, telemetry or other software on your computer. Only use trusted, ordinary PDF copies. Inputs must resolve to regular files; input links/reparse points, hardlinks, special files and traversal are refused. Encrypted files are rejected. Large or complex PDFs can use substantial memory or fail. Output reports expose names, paths and errors. Keep private output private.

## Run

    python make_sample.py
    python check38.py snapshot
    python pdfkit.py count sample/contract.pdf sample/invoice.pdf sample/notes.pdf
    python pdfkit.py merge sample/merged.pdf sample/contract.pdf sample/invoice.pdf sample/notes.pdf
    python pdfkit.py split sample/merged.pdf sample/first.pdf 1-2
    python pdfkit.py rotate sample/notes.pdf sample/rotated.pdf 90
    python check38.py verify
    python -m unittest -v

Use normal Python, not `python -O`: the fixture helper uses assertions. Page ranges are 1-based and inclusive. Optional `--page N` rotates one page, otherwise all pages are rotated. Degrees must be 90, 180 or 270, added clockwise to existing page rotation.

## Data safety and limits

Setup refuses every existing sample path and exclusively creates three small fictional labeled PDFs in a new folder. Outputs check the destination itself with lstat, then use `xb` after serialization into memory: every existing destination is refused, including an input path, hardlink, symlink, empty file or directory. The explicit link check is needed because xb followed a dangling symlink in the Windows fixture. Manifests use exclusive creation too. There is no overwrite option. Do not delete old data to force a retry. An interrupted setup or disk/write failure can leave a partial NEW folder or output; it is not automatically deleted. Keep originals and inspect saved results. Concurrent hostile filesystem changes are not tested.

`add_page` copies pages. It does not promise preservation of forms, digital signatures, outlines, attachments, metadata, all annotations, accessibility or every document-level feature. Do not use this lesson for signed or interactive documents that must retain those features. Equal page counts cannot prove correct content or order. The fixture checker compares six known extracted text labels, order, page geometry, rotation and source SHA256; it cannot prove visual appearance or feature preservation for arbitrary PDFs.

## Evidence

51 small temporary-fixture tests cover content/order/rotation, existing/empty/directory/input/hardlink/symlink outputs, source bytes and modification times, bad arguments/inputs, encrypted input refusal, serialization failure, setup collisions and checker failure cases. Named-pipe and symlink tests skip only when the platform lacks the operation. These are limited checks, not proof for every document, filesystem or failure. Two Windows and two Ubuntu full replays pass 51 tests; Windows skips two unavailable named-pipe tests. Each platform pair differs only in test timing. Source, merged, split and rotated fixture PDFs were rendered locally and their actual labels, order and rotation inspected. This is not a real-document test.

The recorder writes exact visible source files to a unique temporary directory, runs exact command argument lists, records full output and exit codes, verifies overwrite refusal leaves output bytes/mtime unchanged, and removes only its recording directory. Dependency installation happens before the visible command sequence. Paired outputs can differ in Python version, test timing or platform-specific skips.

## Sources and licenses

- Page copying and document-feature cautions: https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html
- Rotation: https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html
- Third-party license: https://pypdf.readthedocs.io/en/6.19.0/meta/faq.html

This lesson's source is MIT licensed (LICENSE). pypdf has a separate BSD-3-Clause license and is installed separately, not bundled. The generated page labels are fictional. No real contract, invoice or personal document was tested.

## Link/error follow-up

Two Windows and two Ubuntu full replays run exact visible source versions. Final 51 small fixture tests pass (two Unix-pipe cases skip on Windows); symlink creation can skip where unavailable. Displayed stdout is first Windows output, not normalized or mixed. Pair differences are unittest time. Raw runner dependency-install output is retained before visible commands where present; installation is a separate prerequisite, not a recorded lesson command.
Only link/error changes: refuse input/ancestor symbolic links/reparse points, hardlinks, special files and traversal before PDF and manifest reads. Output ancestors are checked before serialization/exclusive new-file creation. Setup checks linked parents/traversal and refuses existing sample paths, with no reset/deletion. Fixture-helper CLI read/metadata/PDF/fixture errors now briefly exit 2 instead of tracebacks; pdfkit operation errors remain exit 1 and parser errors remain exit 2.
Original PDF page count/merge/split/rotation, page-copy semantics, full serialization before exclusive output creation, and fixture SHA256/label/order/geometry/rotation checks are unchanged. No existing destination is replaced. Write failure can leave a partial NEW file; it is not deleted. Docs-only correction: README now lists rotation choices 90,180,270,matching the unchanged tool,not the former typo300.
Use only trusted ordinary PDF copies, not links. Encrypted inputs remain refused. No atomic snapshot, hostile-race defense, resource bound, PDF security sandbox, whole-document-feature or visual-appearance guarantee. Stop editors/sync. PDF processing uses memory; forms, signatures, metadata, outlines and other features are not promised. Paths/errors/output documents may be private. Keep originals and inspect saved results. Assertions require normal Python, not python -O. Small fictional fixtures are not proof on every document/filesystem. No desktop-app test. Recorder removes only its own temporary fixture folder. Decisions/feedback are teaching text, not recorded output.
Windows paired run: https://github.com/faiz12321/lesson-lab/actions/runs/38979759471
Ubuntu paired run: https://github.com/faiz12321/lesson-lab/actions/runs/38979977465
