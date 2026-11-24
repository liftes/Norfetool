"""TexBuild contract tests; fake subprocess outputs never run a TeX engine.

Set TEXBUILDER_MODULE_PATH to test a staged module before installation.
The source module is loaded directly to avoid package-level plotting effects.
"""

from pathlib import Path
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(os.environ.get(
    'TEXBUILDER_MODULE_PATH',
    str(Path(__file__).resolve().parents[1] / 'norfetools/TexBuilder.py'),
))


class TexBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('_tested_tex_builder', MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        cls.builder = cls.module.TexBuild

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nt TeX # project ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.sources = {}
        for name in ('Manuscript.tex', 'SupportingInformation.tex',
                     '#3st/ResponsetoReviewers.tex', 'nested/Other.tex'):
            self.add_source(name)
        self.calls = []

    def add_source(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = ('% Original source: ' + name + '\n'
                   '\\documentclass{article}\n\\begin{document}\n'
                   'Source content must remain unchanged.\n\\end{document}\n')
        path.write_text(content, encoding='utf-8')
        self.sources[path] = content
        return path

    def compile_details(self, command, cwd):
        cwd = Path(cwd).resolve()
        out_arg = next(part.split('=', 1)[1] for part in command
                       if part.startswith(('-outdir=', '-output-directory=')))
        out = Path(out_arg)
        if not out.is_absolute():
            out = cwd / out
        out = out.resolve()
        job = next(part.split('=', 1)[1] for part in command if part.startswith('-jobname='))
        return cwd, out, job

    def fake_compile(self, command, *, cwd, check, **kwargs):
        self.assertTrue(check)
        cwd, out, job = self.compile_details(command, cwd)
        out.mkdir(parents=True, exist_ok=True)
        for suffix, data in (
            ('.aux', 'Stable labels for ' + job),
            ('.pdf', 'Fake PDF for ' + job),
            ('.log', 'Output written successfully.\n'),
        ):
            (out / (job + suffix)).write_text(data, encoding='utf-8')
        self.calls.append({'command': command, 'cwd': cwd, 'out': out, 'job': job})
        return subprocess.CompletedProcess(command, 0)

    def build(self, texFiles=None, compiler=None, **kwargs):
        if texFiles is None:
            texFiles = ['Manuscript.tex', 'SupportingInformation.tex']
        with patch.object(self.module.shutil, 'which', return_value='/mock/latexmk'), \
             patch.object(self.module.subprocess, 'run', side_effect=compiler or self.fake_compile), \
             contextlib.redirect_stdout(io.StringIO()):
            return self.builder.build(texRootDir=self.root, texFiles=texFiles, **kwargs)

    def assert_sources_unchanged(self):
        for path, content in self.sources.items():
            self.assertEqual(path.read_text(encoding='utf-8'), content)

    def test_list_shorthand_builds_both_modes(self):
        result = self.build()
        self.assertTrue(result['compiled'])
        self.assertEqual(set(result['outputs']), {'clean', 'highlighted'})
        self.assertEqual(len(self.calls), 8)
        for mode, prefix in (('clean', ''), ('highlighted', 'Highlighted')):
            for stem in ('Manuscript', 'SupportingInformation'):
                output = result['outputs'][mode][stem]
                self.assertEqual(output, self.root / 'build' / (prefix + stem + '.pdf'))
                self.assertTrue(output.is_file())
                self.assertTrue((self.root / 'build' / mode / (stem + '.aux')).is_file())
        self.assert_sources_unchanged()

    def test_each_mode_accepts_a_different_file_list(self):
        result = self.build(texFiles={
            'clean': ['Manuscript.tex', 'SupportingInformation.tex'],
            'highlighted': ['Manuscript.tex'],
        })
        self.assertEqual(set(result['outputs']['clean']), {'Manuscript', 'SupportingInformation'})
        self.assertEqual(set(result['outputs']['highlighted']), {'Manuscript'})
        self.assertEqual(len(self.calls), 6)
        self.assertFalse((self.root / 'build/HighlightedSupportingInformation.pdf').exists())

    def test_dry_run_writes_nothing_and_needs_no_installed_latexmk(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with patch.object(self.module.shutil, 'which', return_value=None), \
             patch.object(self.module.subprocess, 'run') as process:
            result = self.builder.build(self.root, ['Manuscript.tex'], dryRun=True)
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(before, after)
        self.assertFalse(result['compiled'])
        self.assertEqual(len(result['commands']), 2)
        process.assert_not_called()

    def test_source_directory_and_output_directory_are_independent(self):
        result = self.build(texFiles={'clean': ['nested/Other.tex']})
        self.assertTrue(result['compiled'])
        for call in self.calls:
            self.assertEqual(call['cwd'], self.root / 'nested')
            self.assertEqual(call['out'], self.root / 'build/clean')
            pretex = next(x for x in call['command'] if x.startswith('-usepretex='))
            self.assertIn(r'\def\ntauxdir{../build/clean}', pretex)
        self.assert_sources_unchanged()

    def test_relative_custom_build_directory(self):
        result = self.build(texFiles={'clean': ['Manuscript.tex']}, buildDir='artifacts')
        self.assertEqual(result['outputs']['clean']['Manuscript'],
                         self.root / 'artifacts/Manuscript.pdf')
        self.assertTrue((self.root / 'artifacts/clean/Manuscript.aux').is_file())
        self.assertFalse((self.root / 'build').exists())

    def test_duplicate_stems_are_rejected_case_insensitively(self):
        self.add_source('other/manuscript.tex')
        with self.assertRaises(ValueError):
            self.build(texFiles=['Manuscript.tex', 'other/manuscript.tex'], dryRun=True)
        self.assertFalse((self.root / 'build').exists())

    def test_missing_source_is_rejected_without_writing_files(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.build(texFiles=['Missing.tex'], dryRun=True)
        self.assertFalse((self.root / 'build').exists())

    def test_invalid_engine_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build(engine='not-a-tex-engine', dryRun=True)
        self.assertEqual(self.calls, [])

    def test_rtor_compiles_last_with_its_own_engine_and_import_directory(self):
        result = self.build(rtorTex='#3st/ResponsetoReviewers.tex',
                            engine='pdflatex', rtorEngine='xelatex')
        self.assertEqual(len(self.calls), 9)
        self.assertEqual(self.calls[-1]['job'], 'ResponsetoReviewers')
        self.assertEqual(self.calls[-1]['cwd'], self.root / '#3st')
        self.assertEqual(self.calls[-1]['out'], self.root / 'build/response')
        self.assertTrue(any(x in self.calls[-1]['command'] for x in ('-xelatex', '-pdfxe')))
        for call in self.calls[:-1]:
            self.assertIn('-pdf', call['command'])
            self.assertNotEqual(call['job'], 'ResponsetoReviewers')
        pretex = next(x for x in self.calls[-1]['command'] if x.startswith('-usepretex='))
        self.assertIn(r'\def\ntresponseauxdir{../build/highlighted}', pretex)
        self.assertEqual(result['response'], self.root / 'build/ResponsetoReviewers.pdf')
        self.assertTrue(result['response'].is_file())
        self.assert_sources_unchanged()

    def test_custom_mode_definitions_are_injected(self):
        result = self.build(texFiles={'clean': ['Manuscript.tex']}, dryRun=True,
                            modeDefinitions={'clean': r'\def\showchanges{0}'})
        command = result['commands'][0]['command']
        self.assertTrue(any(r'\def\showchanges{0}' in part for part in command))

    def test_process_failure_preserves_previously_published_pdf(self):
        build_dir = self.root / 'build'
        build_dir.mkdir()
        previous = build_dir / 'Manuscript.pdf'
        previous.write_text('Previous accepted output', encoding='utf-8')

        def fail_highlighted(command, *, cwd, check, **kwargs):
            _, directory, _ = self.compile_details(command, cwd)
            if directory.name == 'highlighted':
                raise subprocess.CalledProcessError(1, command)
            return self.fake_compile(command, cwd=cwd, check=check, **kwargs)

        with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
            self.build(compiler=fail_highlighted)
        self.assertEqual(previous.read_text(encoding='utf-8'), 'Previous accepted output')
        self.assertFalse((build_dir / 'SupportingInformation.pdf').exists())

    def test_unresolved_citations_are_not_published(self):
        def unresolved(command, *, cwd, check, **kwargs):
            result = self.fake_compile(command, cwd=cwd, check=check, **kwargs)
            _, out, job = self.compile_details(command, cwd)
            (out / (job + '.log')).write_text(
                'Package natbib Warning: There were undefined citations.\n', encoding='utf-8')
            return result

        with self.assertRaises(RuntimeError):
            self.build(texFiles={'clean': ['Manuscript.tex']}, compiler=unresolved)
        self.assertFalse((self.root / 'build/Manuscript.pdf').exists())

    def test_unstable_external_labels_stop_at_the_round_limit(self):
        def never_stable(command, *, cwd, check, **kwargs):
            result = self.fake_compile(command, cwd=cwd, check=check, **kwargs)
            _, out, job = self.compile_details(command, cwd)
            (out / (job + '.aux')).write_text(str(len(self.calls)), encoding='utf-8')
            return result

        with self.assertRaises(RuntimeError):
            self.build(texFiles={'clean': ['Manuscript.tex']},
                       compiler=never_stable, maxRounds=3)
        self.assertEqual(len(self.calls), 3)
        self.assertFalse((self.root / 'build/Manuscript.pdf').exists())

    def test_rtor_failure_does_not_publish_other_outputs(self):
        def fail_response(command, *, cwd, check, **kwargs):
            _, out, _ = self.compile_details(command, cwd)
            if out.name == 'response':
                raise subprocess.CalledProcessError(1, command)
            return self.fake_compile(command, cwd=cwd, check=check, **kwargs)

        with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
            self.build(rtorTex='#3st/ResponsetoReviewers.tex', compiler=fail_response)
        self.assertFalse((self.root / 'build/Manuscript.pdf').exists())
        self.assertFalse((self.root / 'build/ResponsetoReviewers.pdf').exists())

    def test_child_aux_files_participate_in_convergence(self):
        def child_labels(command, *, cwd, check, **kwargs):
            result = self.fake_compile(command, cwd=cwd, check=check, **kwargs)
            _, out, _ = self.compile_details(command, cwd)
            child = out / 'sections'
            child.mkdir(exist_ok=True)
            (child / 'part.aux').write_text('initial' if len(self.calls) == 1 else 'updated', encoding='utf-8')
            return result

        self.build(texFiles={'clean': ['Manuscript.tex']}, compiler=child_labels)
        self.assertEqual(len(self.calls), 3)

    def test_final_output_collisions_are_rejected(self):
        self.add_source('HighlightedManuscript.tex')
        with self.assertRaises(ValueError):
            self.build(texFiles={'clean': ['HighlightedManuscript.tex'],
                                 'highlighted': ['Manuscript.tex']}, dryRun=True)

    def test_rtor_requires_highlighted_data(self):
        with self.assertRaises(ValueError):
            self.build(texFiles={'clean': ['Manuscript.tex']},
                       rtorTex='#3st/ResponsetoReviewers.tex', dryRun=True)

    def test_hash_in_aux_directory_uses_literal_hash(self):
        result = self.build(texFiles={'clean': ['Manuscript.tex']},
                            buildDir='results#one', dryRun=True)
        pretex = next(part for part in result['commands'][0]['command']
                      if part.startswith('-usepretex='))
        self.assertIn(r'\string#', pretex)
        self.assertNotIn('##', pretex)

    def test_lualatex_engine_is_supported(self):
        result = self.build(texFiles={'clean': ['Manuscript.tex']}, engine='lualatex', dryRun=True)
        self.assertIn('-lualatex', result['commands'][0]['command'])

    def test_unsupported_aux_path_characters_are_rejected(self):
        with self.assertRaises(ValueError):
            self.build(texFiles={'clean': ['Manuscript.tex']}, buildDir='results%one', dryRun=True)
        self.assertFalse((self.root / 'results%one').exists())


    def pretex(self, command):
        return next(part for part in command if part.startswith('-usepretex='))

    def test_flat_layout_compiles_every_job_in_build_directory(self):
        result = self.build(flatOutput=True)
        directory = self.root / 'build'
        self.assertTrue(result['compiled'])
        self.assertEqual(len(self.calls), 8)
        self.assertEqual({call['job'] for call in self.calls}, {
            'Manuscript', 'SupportingInformation',
            'HighlightedManuscript', 'HighlightedSupportingInformation',
        })
        for call in self.calls:
            self.assertEqual(call['out'], directory)
            for suffix in ('.pdf', '.aux', '.log'):
                self.assertTrue((directory / (call['job'] + suffix)).is_file())
        for mode, prefix in (('clean', ''), ('highlighted', 'Highlighted')):
            for stem, output in result['outputs'][mode].items():
                self.assertEqual(output, directory / (prefix + stem + '.pdf'))
                self.assertEqual(output.read_text(encoding='utf-8'), 'Fake PDF for ' + prefix + stem)
        self.assertFalse(any(path.is_dir() for path in directory.iterdir()))
        self.assert_sources_unchanged()

    def test_flat_custom_prefix_controls_jobs_and_import_macros(self):
        result = self.build(flatOutput=True, highlightedPrefix='Review_v2-')
        self.assertEqual(result['outputs']['highlighted']['Manuscript'],
                         self.root / 'build/Review_v2-Manuscript.pdf')
        for call in self.calls:
            pretex = self.pretex(call['command'])
            prefix = 'Review_v2-' if call['job'].startswith('Review_v2-') else ''
            self.assertIn(r'\def\ntauxdir{build}', pretex)
            self.assertIn(r'\def\ntauxprefix{' + prefix + '}', pretex)
            self.assertIn(r'\def\ntpdfprefix{' + prefix + '}', pretex)
        self.assert_sources_unchanged()

    def test_split_layout_custom_prefix_preserves_aux_names(self):
        result = self.build(highlightedPrefix='Marked_')
        self.assertEqual(result['outputs']['highlighted']['Manuscript'],
                         self.root / 'build/Marked_Manuscript.pdf')
        for call in self.calls:
            self.assertIn(call['job'], ('Manuscript', 'SupportingInformation'))
            pretex = self.pretex(call['command'])
            self.assertIn(r'\def\ntauxprefix{}', pretex)
            expected = 'Marked_' if call['out'].name == 'highlighted' else ''
            self.assertIn(r'\def\ntpdfprefix{' + expected + '}', pretex)
        self.assertTrue((self.root / 'build/highlighted/Manuscript.aux').is_file())

    def test_flat_response_runs_last_and_imports_prefixed_highlighted_aux(self):
        result = self.build(flatOutput=True, highlightedPrefix='Changes_',
                            rtorTex='#3st/ResponsetoReviewers.tex')
        self.assertEqual(len(self.calls), 9)
        response = self.calls[-1]
        self.assertEqual(response['job'], 'ResponsetoReviewers')
        self.assertEqual(response['cwd'], self.root / '#3st')
        self.assertTrue(all(call['out'] == self.root / 'build' for call in self.calls))
        self.assertTrue(any(flag in response['command'] for flag in ('-xelatex', '-pdfxe')))
        pretex = self.pretex(response['command'])
        self.assertIn(r'\def\ntresponseauxdir{../build}', pretex)
        self.assertIn(r'\def\ntresponseauxprefix{Changes_}', pretex)
        self.assertEqual(result['response'], self.root / 'build/ResponsetoReviewers.pdf')
        self.assertEqual(result['response'].read_text(encoding='utf-8'),
                         'Fake PDF for ResponsetoReviewers')
        self.assertTrue((self.root / 'build/Changes_Manuscript.aux').is_file())
        self.assert_sources_unchanged()

    def test_split_response_import_prefix_is_empty(self):
        result = self.build(rtorTex='#3st/ResponsetoReviewers.tex',
                            highlightedPrefix='Changes_', dryRun=True)
        pretex = self.pretex(result['commands'][-1]['command'])
        self.assertIn(r'\def\ntresponseauxdir{../build/highlighted}', pretex)
        self.assertIn(r'\def\ntresponseauxprefix{}', pretex)

    def test_flat_nested_source_with_custom_directory(self):
        result = self.build(texFiles={'highlighted': ['nested/Other.tex']},
                            flatOutput=True, buildDir='artifacts', highlightedPrefix='R3_')
        for call in self.calls:
            self.assertEqual(call['cwd'], self.root / 'nested')
            self.assertEqual(call['out'], self.root / 'artifacts')
            self.assertEqual(call['job'], 'R3_Other')
            self.assertIn(r'\def\ntauxdir{../artifacts}', self.pretex(call['command']))
        self.assertEqual(result['outputs']['highlighted']['Other'], self.root / 'artifacts/R3_Other.pdf')
        self.assertFalse((self.root / 'build').exists())

    def test_flat_dry_run_is_complete_and_writes_nothing(self):
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*'))
        with patch.object(self.module.shutil, 'which', return_value=None), \
             patch.object(self.module.subprocess, 'run') as process:
            result = self.builder.build(self.root, ['Manuscript.tex'],
                                        flatOutput=True, highlightedPrefix='R3-',
                                        rtorTex='#3st/ResponsetoReviewers.tex', dryRun=True)
        self.assertEqual(before, sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*')))
        self.assertFalse(result['compiled'])
        self.assertEqual(len(result['commands']), 3)
        details = [self.compile_details(record['command'], record['cwd']) for record in result['commands']]
        self.assertEqual([job for _, _, job in details], ['Manuscript', 'R3-Manuscript', 'ResponsetoReviewers'])
        self.assertTrue(all(out == self.root / 'build' for _, out, _ in details))
        process.assert_not_called()

    def test_custom_prefix_collision_is_rejected_case_insensitively(self):
        self.add_source('review_manuscript.tex')
        for flat in (False, True):
            with self.subTest(flatOutput=flat), self.assertRaises(ValueError):
                self.build(texFiles={'clean': ['review_manuscript.tex'],
                                     'highlighted': ['Manuscript.tex']},
                           highlightedPrefix='Review_', flatOutput=flat, dryRun=True)
        self.assertFalse((self.root / 'build').exists())
        self.assertEqual(self.calls, [])

    def test_flat_response_cannot_overwrite_a_highlighted_job(self):
        self.add_source('#3st/HighlightedManuscript.tex')
        with self.assertRaises(ValueError):
            self.build(texFiles=['Manuscript.tex'], flatOutput=True,
                       rtorTex='#3st/HighlightedManuscript.tex', dryRun=True)
        self.assertFalse((self.root / 'build').exists())

    def test_empty_prefix_is_allowed_without_colliding_outputs(self):
        for flat in (False, True):
            with self.subTest(flatOutput=flat):
                result = self.build(texFiles={'highlighted': ['Manuscript.tex']},
                                    flatOutput=flat, highlightedPrefix='', dryRun=True)
                self.assertEqual(result['outputs']['highlighted']['Manuscript'],
                                 self.root / 'build/Manuscript.pdf')
        for flat in (False, True):
            with self.subTest(collision=True, flatOutput=flat), self.assertRaises(ValueError):
                self.build(texFiles=['Manuscript.tex'], flatOutput=flat, highlightedPrefix='', dryRun=True)
        self.assertFalse((self.root / 'build').exists())

    def test_invalid_prefixes_are_rejected_before_any_output(self):
        invalid = ('../', 'a/b', r'a\b', 'a b', 'a#', 'a%', 'a$', 'a&',
                   'a{', 'a}', 'a~', 'a^', 'a\n', 'a\r', 'a:', '中文', 3, None, True)
        for prefix in invalid:
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                self.build(highlightedPrefix=prefix, flatOutput=True, dryRun=True)
        self.assertFalse((self.root / 'build').exists())
        self.assertEqual(self.calls, [])

    def test_flat_output_requires_a_boolean(self):
        for value in (0, 1, 'true', '', None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build(flatOutput=value, dryRun=True)
        self.assertFalse((self.root / 'build').exists())

    def test_flat_validation_checks_highlighted_job_log(self):
        def unresolved(command, *, cwd, check, **kwargs):
            result = self.fake_compile(command, cwd=cwd, check=check, **kwargs)
            _, out, job = self.compile_details(command, cwd)
            if job == 'R3_Manuscript':
                (out / (job + '.log')).write_text(
                    'Package natbib Warning: There were undefined citations.\n', encoding='utf-8')
            return result

        with self.assertRaises(RuntimeError):
            self.build(texFiles=['Manuscript.tex'], flatOutput=True,
                       highlightedPrefix='R3_', compiler=unresolved)
        self.assertTrue(any(call['job'] == 'R3_Manuscript' for call in self.calls))
        self.assert_sources_unchanged()

    def test_flat_validation_requires_prefixed_aux_and_pdf(self):
        for suffix in ('.aux', '.pdf'):
            with self.subTest(suffix=suffix):
                def missing_output(command, *, cwd, check, **kwargs):
                    result = self.fake_compile(command, cwd=cwd, check=check, **kwargs)
                    _, out, job = self.compile_details(command, cwd)
                    if job == 'R3_Manuscript':
                        (out / (job + suffix)).unlink()
                    return result

                with self.assertRaises(RuntimeError):
                    self.build(texFiles=['Manuscript.tex'], flatOutput=True,
                               highlightedPrefix='R3_', compiler=missing_output)
        self.assert_sources_unchanged()


if __name__ == '__main__':
    unittest.main()
