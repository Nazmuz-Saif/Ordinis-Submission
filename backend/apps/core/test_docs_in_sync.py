"""The documents must match the code. Fix a failure here with:  python manage.py generate_docs"""
import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core import docgen, doccheck, traceability

DOCS = docgen.docs_dir()


class DocumentsMatchTheCodeTests(SimpleTestCase):
    def test_the_generated_parts_are_up_to_date(self):
        try:
            call_command('generate_docs', '--check')
        except CommandError as exc:
            self.fail(f'{exc}')

    def test_no_document_names_something_the_code_does_not_have(self):
        problems = doccheck.check_dir(DOCS)
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))

    def test_every_document_the_generator_fills_exists_and_has_its_markers(self):
        for block, (_standalone, _injected, doc) in docgen.BLOCKS.items():
            path = os.path.join(DOCS, doc)
            self.assertTrue(os.path.exists(path), f'{doc} is missing')
            text = open(path, encoding='utf-8').read()
            self.assertIn(docgen.marker(block, 'BEGIN'), text, f'{doc} lacks the {block} markers')
            self.assertIn(docgen.marker(block, 'END'), text)

    def test_the_sds_api_table_lists_every_real_endpoint(self):
        text = open(os.path.join(DOCS, 'Ordinis_SDS.md'), encoding='utf-8').read()
        from core.api_matrix import discover_routes
        for route in discover_routes():
            path = '/' + route.template.replace('{pk}', '{id}')
            self.assertIn(f'`{path}`', text, f'{path} is not in the SDS API table')

    def test_the_sds_data_dictionary_lists_every_real_model(self):
        text = open(os.path.join(DOCS, 'Ordinis_SDS.md'), encoding='utf-8').read()
        for _app, models_ in docgen.our_models():
            for model in models_:
                self.assertIn(f'#### {model.__name__}\n', text, f'{model.__name__} is not in the SDS data dictionary')


class GeneratorTests(SimpleTestCase):
    def test_inject_replaces_only_what_is_between_the_markers(self):
        begin, end = docgen.marker('x', 'BEGIN'), docgen.marker('x', 'END')
        text = f'before\n{begin}\nold\n{end}\nafter\n'
        self.assertEqual(docgen.inject(text, 'x', 'new\n'), f'before\n{begin}\nnew\n{end}\nafter\n')

    def test_inject_without_markers_says_so(self):
        self.assertIsNone(docgen.inject('nothing here', 'x', 'new'))

    def test_check_fails_when_a_generated_file_is_stale_and_write_fixes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _block, (_s, _i, doc) in docgen.BLOCKS.items():
                path = os.path.join(tmp, doc)
                if not os.path.exists(path):
                    with open(path, 'w', encoding='utf-8') as handle:
                        handle.write(''.join(f'{docgen.marker(b, "BEGIN")}\n{docgen.marker(b, "END")}\n' for b, p in docgen.BLOCKS.items() if p[2] == doc))
            with self.assertRaises(CommandError):
                call_command('generate_docs', '--check', '--docs-dir', tmp)
            call_command('generate_docs', '--docs-dir', tmp)
            call_command('generate_docs', '--check', '--docs-dir', tmp)
            stale = os.path.join(tmp, 'generated', 'api-table.md')
            with open(stale, 'a', encoding='utf-8') as handle:
                handle.write('hand edit\n')
            with self.assertRaises(CommandError):
                call_command('generate_docs', '--check', '--docs-dir', tmp)

    def test_a_missing_document_is_an_error_not_a_silent_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                call_command('generate_docs', '--docs-dir', tmp)


class DocumentCheckerTests(SimpleTestCase):
    def test_a_real_endpoint_and_a_real_class_pass(self):
        text = 'Use `/api/v1/tasks/tasks/{id}/move/` and `Employee.reports_to` and `PermissionRequiredMixin`.'
        self.assertEqual(doccheck.check_text(text), [])

    def test_an_endpoint_that_does_not_exist_is_reported(self):
        problems = doccheck.check_text('Call /api/v1/billing/invoices/ to pay.')
        self.assertEqual(len(problems), 1)
        self.assertIn('/api/v1/billing/invoices/', problems[0])

    def test_a_class_or_field_that_does_not_exist_is_reported(self):
        self.assertEqual(len(doccheck.check_text('The `AuditLog` keeps every change.')), 1)
        self.assertEqual(len(doccheck.check_text('`Employee.salary` holds the pay.')), 1)

    def test_a_line_that_says_it_is_future_work_may_name_missing_things(self):
        self.assertEqual(doccheck.check_text('Future work: `AuditLog` and /api/v1/billing/invoices/.'), [])
        self.assertEqual(doccheck.check_text('`SubscriptionPlan` is not built yet.'), [])

    def test_a_differences_report_may_name_what_was_wrong(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'ST-1_differences.md'), 'w', encoding='utf-8') as handle:
                handle.write('The old text said `KanbanCard` and /api/v1/billing/plans/.\n')
            with open(os.path.join(tmp, 'other.md'), 'w', encoding='utf-8') as handle:
                handle.write('Fine.\n')
            self.assertEqual(doccheck.check_dir(tmp), [])

    def test_a_file_name_is_not_a_class(self):
        self.assertEqual(doccheck.check_text('Read `TESTING.md` first.'), [])


class TraceabilityTests(SimpleTestCase):
    def status(self, rid):
        return next(r[3] for r in traceability.rows() if r[0] == rid)

    def test_the_status_comes_from_the_code(self):
        self.assertEqual(self.status('FR-22'), 'Done')        # leave approval (ST-129)
        self.assertEqual(self.status('FR-17'), 'Partly')      # Task is built, Project is not
        self.assertEqual(self.status('FR-26'), 'Not built')   # Expense is not in the five sprints

    def test_a_partly_requirement_names_what_is_missing(self):
        note = next(r[5] for r in traceability.rows() if r[0] == 'FR-17')
        self.assertIn('model Project', note)

    def test_evaluate_counts_what_exists(self):
        facts = traceability.Facts()
        have, missing = traceability.evaluate({'models': ['Task', 'NoSuchModel'], 'routes': ['/api/v1/auth/login/']}, facts)
        self.assertEqual((len(have), len(missing)), (2, 1))
        self.assertIn('model NoSuchModel', missing)

    def test_every_requirement_of_the_srs_is_in_the_table(self):
        ids = [r[0] for r in traceability.rows()]
        self.assertEqual(ids, [f'FR-{n}' for n in range(1, 37)] + [f'NFR-{n}' for n in range(1, 16)])

    def test_the_count_line_adds_up(self):
        rows = traceability.rows()
        last = traceability.table().strip().splitlines()[-1]
        done = sum(1 for r in rows if r[3] == 'Done')
        self.assertIn(f'{len(rows)} requirements: {done} Done', last)
