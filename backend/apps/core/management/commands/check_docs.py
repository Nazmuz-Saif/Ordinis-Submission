import os

from django.core.management.base import BaseCommand, CommandError

from core import docgen, doccheck


class Command(BaseCommand):
    help = 'Fails if a document names an endpoint, model or field the code does not have (unless the line says it is future work).'

    def add_arguments(self, parser):
        parser.add_argument('--docs-dir', help='Folder with the .md documents (default: docs at the repo root).')

    def handle(self, *args, **opts):
        folder = opts['docs_dir'] or os.path.dirname(docgen.out_dir())
        if not os.path.isdir(folder):
            raise CommandError(f'No documents folder at {folder}')
        problems = doccheck.check_dir(folder)
        for problem in problems:
            self.stdout.write(problem)
        if problems:
            raise CommandError(f'{len(problems)} problem(s). Fix the document, or mark the line as future work.')
        self.stdout.write(f'Documents in {folder} match the code.')
