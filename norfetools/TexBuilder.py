"""LaTeX build orchestration; no source rewriting or import-time execution.

The default preamble contract is ``ntbuildmode`` (0/1), ``ntauxdir``
(the current variant's AUX directory), and ``ntresponseauxdir`` (the
highlighted AUX directory imported by an optional response document).
The corresponding filename prefixes are ntauxprefix, ntpdfprefix, and
ntresponseauxprefix; they support flat output without project-specific names.
LaTeX sources must use these definitions where applicable. Custom mode
preambles can be supplied without changing the document files.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

__all__ = ['TexBuild']


class TexBuild:
    """Build clean/highlighted PDF variants and an optional response document.

    Only the Python standard library is used here. Actual builds require
    latexmk, the selected TeX engines and the document's TeX dependencies.
    """

    _ENGINES = {'pdflatex': '-pdf', 'xelatex': '-xelatex', 'lualatex': '-lualatex'}
    _MODES = {'clean': r'\def\ntbuildmode{0}',
              'highlighted': r'\def\ntbuildmode{1}'}

    @classmethod
    def build(cls, texRootDir, texFiles, *, rtorTex=None, engine='pdflatex',
              rtorEngine='xelatex', buildDir='build', maxRounds=6,
              latexmk='latexmk', dryRun=False, modeDefinitions=None,
              flatOutput=False, highlightedPrefix='Highlighted'):
        """Return output paths and commands; raise an exception on failure.

        ``texFiles`` is a sequence of main .tex paths (both variants), or a
        mapping from ``clean``/``highlighted`` to independent path lists.
        Input paths and relative ``buildDir`` are resolved against
        ``texRootDir``. Each source is compiled from its own directory.

        The result is a dict with ``outputs`` (mode -> stem -> PDF Path),
        ``response`` (PDF Path or None), ``commands`` (command/cwd records),
        and ``compiled``. A dry run validates inputs and returns a plan,
        without creating directories or requiring latexmk to be installed.

        ``modeDefinitions`` optionally overrides each mode's raw TeX
        preamble; ntauxdir is appended automatically. Sources are never
        rewritten. The response requires a highlighted build and is run
        last, with its own engine and ntresponseauxdir definition.

        ``highlightedPrefix`` changes the final review PDF prefix (default
        'Highlighted'). ``flatOutput=True`` compiles directly into buildDir,
        using prefixed job names to separate top-level AUX/BibTeX/log files.
        Source imports must use ntauxdir plus ntauxprefix; response imports
        use ntresponseauxdir plus ntresponseauxprefix. ntpdfprefix always
        describes the final PDF prefix. Prefixes allow ASCII letters,
        digits, hyphens and underscores; output-name collisions are rejected.
        Flat projects using include must also distinguish child AUX names
        between variants; input-based projects need no child AUX changes.
        """
        root = Path(texRootDir).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f'Project directory not found: {root}')
        if isinstance(maxRounds, bool) or not isinstance(maxRounds, int) or maxRounds < 2:
            raise ValueError('maxRounds must be an integer of at least 2')
        if not isinstance(flatOutput, bool):
            raise ValueError('flatOutput must be a bool')
        if not isinstance(highlightedPrefix, str) or re.fullmatch(r'[A-Za-z0-9_-]*', highlightedPrefix) is None:
            raise ValueError('highlightedPrefix allows ASCII letters, digits, hyphens and underscores only')
        engine = cls._engine(engine)
        rtorEngine = cls._engine(rtorEngine)
        variants = cls._documents(root, texFiles)
        response = cls._source(root, rtorTex) if rtorTex is not None else None
        if response is not None and 'highlighted' not in variants:
            raise ValueError('rtorTex requires a highlighted variant for its page/line references')
        directory = Path(buildDir).expanduser()
        directory = (root / directory).resolve() if not directory.is_absolute() else directory.resolve()
        definitions = dict(cls._MODES)
        if modeDefinitions is not None:
            if not isinstance(modeDefinitions, Mapping):
                raise ValueError('modeDefinitions must map mode names to TeX strings')
            for mode, definition in modeDefinitions.items():
                if mode not in cls._MODES or not isinstance(definition, str):
                    raise ValueError('Mode definitions require clean/highlighted keys and string values')
                definitions[mode] = definition
        executable = shutil.which(str(latexmk))
        if executable is None and not dryRun:
            raise FileNotFoundError('latexmk was not found; install TeX Live/MiKTeX or pass latexmk=...')
        executable = executable or str(latexmk)
        outputs = {}
        records = {}
        destinations = set()
        for mode, sources in variants.items():
            outputs[mode] = {}
            records[mode] = []
            for source in sources:
                prefix = highlightedPrefix if mode == 'highlighted' else ''
                work_dir = directory if flatOutput else directory / mode
                job_prefix = prefix if flatOutput else ''
                target = directory / (prefix + source.stem + '.pdf')
                cls._reserve_target(target, destinations)
                outputs[mode][source.stem] = target
                preamble = (definitions[mode]
                            + cls._path_definition('ntauxdir', work_dir, source.parent)
                            + rf'\def\ntauxprefix{{{job_prefix}}}'
                            + rf'\def\ntpdfprefix{{{prefix}}}')
                records[mode].append(cls._command(executable, engine, source,
                                                   work_dir, mode, preamble,
                                                   jobName=job_prefix + source.stem))
        response_record = None
        response_target = None
        if response is not None:
            response_target = directory / (response.stem + '.pdf')
            cls._reserve_target(response_target, destinations)
            highlighted_dir = directory if flatOutput else directory / 'highlighted'
            response_dir = directory if flatOutput else directory / 'response'
            response_prefix = highlightedPrefix if flatOutput else ''
            preamble = (cls._path_definition('ntresponseauxdir', highlighted_dir, response.parent)
                        + rf'\def\ntresponseauxprefix{{{response_prefix}}}')
            response_record = cls._command(executable, rtorEngine, response,
                                             response_dir, 'response', preamble)
        plan = [record for group in records.values() for record in group]
        if response_record is not None:
            plan.append(response_record)
        result = {'outputs': outputs, 'response': response_target,
                  'commands': plan, 'compiled': False}
        if dryRun:
            return result

        executed = []
        for mode, group in records.items():
            work_dir = group[0]['outputDir']
            previous = None
            for round_number in range(1, maxRounds + 1):
                print(f'[{mode}] reference round {round_number}/{maxRounds}', flush=True)
                for record in group:
                    cls._run(record, executed)
                # Include child AUX files produced by \include as well as
                # the top-level files imported through xr/xr-hyper.
                signature = tuple((path.relative_to(work_dir).as_posix(),
                                   hashlib.sha256(path.read_bytes()).hexdigest())
                                  for path in sorted(work_dir.rglob('*.aux')))
                if signature == previous:
                    for record in group:
                        cls._validate(record)
                    break
                previous = signature
            else:
                raise RuntimeError(f'{mode}: external references did not stabilize after '
                                   f'{maxRounds} rounds; inspect {work_dir}')
        if response_record is not None:
            cls._run(response_record, executed)
            cls._validate(response_record)

        copies = [(record['outputDir'] / (record['jobName'] + '.pdf'),
                   outputs[mode][record['source'].stem])
                  for mode, group in records.items() for record in group]
        if response_record is not None:
            copies.append((response_record['outputDir'] / (response.stem + '.pdf'), response_target))
        cls._publish([(source, target) for source, target in copies if source != target])
        cls._normalize_output_case([target for _, target in copies])
        result.update(commands=executed, compiled=True)
        return result

    @classmethod
    def _engine(cls, name):
        if not isinstance(name, str) or name.lower() not in cls._ENGINES:
            raise ValueError('engine must be pdflatex, xelatex or lualatex')
        return name.lower()

    @staticmethod
    def _source(root, name):
        path = Path(name).expanduser()
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        if path.suffix.lower() != '.tex' or not path.is_file():
            raise ValueError(f'Main .tex source not found: {path}')
        return path

    @classmethod
    def _documents(cls, root, files):
        if isinstance(files, Mapping):
            if not files or any(mode not in cls._MODES for mode in files):
                raise ValueError('texFiles mode keys must be clean and/or highlighted')
            configured = {mode: files[mode] for mode in cls._MODES if mode in files}
        else:
            configured = {mode: files for mode in cls._MODES}
        variants = {}
        for mode, names in configured.items():
            if isinstance(names, (str, bytes)) or not isinstance(names, Sequence) or not names:
                raise ValueError('Each texFiles entry must be a nonempty list/tuple of main .tex paths')
            sources = [cls._source(root, name) for name in names]
            stems = [source.stem.casefold() for source in sources]
            if len(set(stems)) != len(stems):
                raise ValueError(f'{mode}: duplicate source stems would overwrite AUX/PDF files')
            variants[mode] = sources
        return variants

    @staticmethod
    def _reserve_target(path, seen):
        key = str(path).casefold()
        if key in seen:
            raise ValueError(f'Duplicate final PDF name: {path.name}')
        seen.add(key)

    @staticmethod
    def _path_definition(macro, directory, cwd):
        try:
            relative = Path(os.path.relpath(directory, cwd)).as_posix()
        except ValueError:  # Different Windows drives cannot use a relative path.
            relative = directory.as_posix()
        if any(character in relative for character in '%{}\n\r') or '^^' in relative:
            raise ValueError('TeX auxiliary-directory paths cannot contain %, braces, ^^ or newlines')
        if any(character in relative for character in '#~$&^'):
            # detokenize doubles a parameter-token #, so insert literal hashes
            # via \string instead. Other chunks become ordinary filename text.
            literal = r'\string#'.join(r'\detokenize{' + part + '}'
                                       for part in relative.split('#'))
            return rf'\edef\{macro}{{{literal}}}'
        return rf'\def\{macro}{{{relative}}}'

    @classmethod
    def _command(cls, executable, engine, source, directory, mode, preamble, jobName=None):
        jobName = source.stem if jobName is None else jobName
        command = [executable, cls._ENGINES[engine], '-g', '-interaction=nonstopmode',
                   '-halt-on-error', '-file-line-error',
                   '-outdir=' + str(directory), '-jobname=' + jobName,
                   '-usepretex=' + preamble, source.name]
        return {'mode': mode, 'source': source, 'cwd': source.parent,
                'outputDir': directory, 'jobName': jobName, 'command': command}

    @staticmethod
    def _run(record, executed):
        record['outputDir'].mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(record['command'], cwd=record['cwd'], check=True)
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f'LaTeX build failed for {record["source"]}; '
                               f'inspect {record["outputDir"]}') from error
        executed.append(record)

    @staticmethod
    def _validate(record):
        base = record['outputDir'] / record.get('jobName', record['source'].stem)
        for extension in ('.pdf', '.aux', '.log'):
            path = base.parent / (base.name + extension)
            if not path.is_file() or not path.stat().st_size:
                raise RuntimeError(f'Missing or empty build output: {path}')
        log = base.parent / (base.name + '.log')
        text = log.read_text(encoding='utf-8', errors='replace')
        if re.search(r'There were (?:undefined (?:references|citations)|multiply-defined labels)'
                     r'|Label\(s\) may have changed', text):
            raise RuntimeError(f'Unresolved or unstable references: {log}')

    @staticmethod
    def _normalize_output_case(targets):
        # On Windows an overwritten file can retain its old capitalization.
        for target in targets:
            for existing in target.parent.iterdir():
                if existing.name != target.name and existing.name.casefold() == target.name.casefold():
                    if existing.samefile(target):
                        existing.rename(target)
                        break

    @staticmethod
    def _publish(copies):
        # Stage every copy before replacing any visible PDF. Each individual
        # replacement is atomic; publishing several files is not a transaction.
        staged = []
        try:
            for source, target in copies:
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix='nt-tex-',
                                                 suffix='.tmp', delete=False) as handle:
                    temporary = Path(handle.name)
                staged.append((temporary, target))
                shutil.copyfile(source, temporary)
            for temporary, target in staged:
                os.replace(temporary, target)
        finally:
            for temporary, _ in staged:
                if temporary.exists():
                    temporary.unlink()
