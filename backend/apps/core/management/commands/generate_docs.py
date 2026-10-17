import os

from django.core.management.base import BaseCommand, CommandError

from core import docgen


def _read(path):
    with open(path, encoding='utf-8', newline='') as handle:
        return handle.read()


def _write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)


def _what_differs(docs, stale):
    """The first lines that differ in the first stale generated file, so a failure says what to look at."""
    import difflib
    built = docgen.standalone_files()
    for name in stale:
        if name.startswith('generated/') and name[len('generated/'):] in built:
            path = os.path.join(docs, name)
            current = _read(path).replace('\r\n', '\n').splitlines() if os.path.exists(path) else []
            diff = [d for d in difflib.unified_diff(current, built[name[len('generated/'):]].splitlines(), 'in the file', 'from the code', lineterm='', n=0)
                    if not d.startswith(('---', '+++', '@@'))]
            if diff:
                return '\nFirst differences in ' + name + ':\n' + '\n'.join(diff[:10])
    return ''


class Command(BaseCommand):
    help = (
        'Writes the parts of the documents that are read from the code: docs/generated/*.md and the blocks between '
        '<!-- BEGIN GENERATED:name --> and <!-- END GENERATED:name --> in the SDS, SRS, ER diagram and structure documents. '
        '--check changes nothing and fails if anything is out of date.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='Compare only; exit with an error if something is out of date.')
        parser.add_argument('--docs-dir', help='Documents folder (default: docs at the repo root).')

    def handle(self, *args, **opts):
        docs = opts['docs_dir'] or docgen.docs_dir()
        generated = os.path.join(docs, 'generated')
        stale, problems = [], []

        for name, text in docgen.standalone_files().items():
            path = os.path.join(generated, name)
            if not os.path.exists(path) or _read(path).replace('\r\n', '\n') != text:
                stale.append(f'generated/{name}')
                if not opts['check']:
                    os.makedirs(generated, exist_ok=True)
                    _write(path, text)

        by_doc = {}
        for block, (_standalone, injected, doc) in docgen.BLOCKS.items():
            by_doc.setdefault(doc, []).append((block, injected))
        for doc, blocks in by_doc.items():
            path = os.path.join(docs, doc)
            if not os.path.exists(path):
                problems.append(f'{doc} is missing from {docs}')
                continue
            raw = _read(path)
            crlf = '\r\n' in raw
            text = raw.replace('\r\n', '\n')
            new = text
            for block, injected in blocks:
                replaced = docgen.inject(new, block, injected())
                if replaced is None:
                    problems.append(f'{doc} has no <!-- BEGIN GENERATED:{block} --> ... <!-- END GENERATED:{block} --> markers')
                else:
                    new = replaced
            if new != text:
                stale.append(doc)
                if not opts['check']:
                    _write(path, new.replace('\n', '\r\n') if crlf else new)

        if problems:
            raise CommandError('\n'.join(problems))
        if opts['check']:
            if stale:
                raise CommandError('Out of date: ' + ', '.join(stale) + '. Run: python manage.py generate_docs' + _what_differs(docs, stale))
            self.stdout.write('Generated documentation is up to date.')
        else:
            self.stdout.write(('Updated: ' + ', '.join(stale)) if stale else 'Already up to date.')
