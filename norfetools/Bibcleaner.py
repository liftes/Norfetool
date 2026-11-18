import os
import re
import unicodedata
from pathlib import Path

class Bib:
    """BibTeX utilities with the legacy API and general name normalization."""

    FIELDS_TO_REMOVE = {
        'file', 'abstract', 'keywords', 'shorttitle', 'urldate',
        'langid', 'isbn', 'lccn', 'copyright'
    }

    _LOWERCASE_WORDS = {
        'of', 'and', 'in', 'on', 'for', 'the', 'with', 'by', 'to', 'at',
        'as', 'from', 'but', 'or', 'nor'
    }

    _FULL_UPPER_ACRONYMS = {
        'ACS', 'JACS', 'PNAS', 'IEEE', 'RSC', 'JCP', 'NIST',
        'AIP', 'SIAM', 'NIPS', 'AAAS', 'APS', 'ES&T'
    }

    @classmethod
    def find_all_tex_files(cls, root_dir):
        tex_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith('.tex'):
                    tex_files.append(os.path.join(dirpath, filename))
        return tex_files

    @classmethod
    def replace_inline_math(cls, tex_file_list):
        for filepath in tex_file_list:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
            content = content.replace(r'\(', '$').replace(r'\)', '$')
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)

    @classmethod
    def generate_clean_bib(cls, input_bib_path, tex_files, output_bib_path):
        # 提取 cite key
        cite_keys = cls._extract_cite_keys(tex_files)
        # 创建中间 bib 文件
        intermediate_path = output_bib_path + ".tmp"
        cls._filter_bib_entries(input_bib_path, cite_keys, intermediate_path)
        # 清理中间 bib 文件并写入目标
        cls._clean_bib_file(intermediate_path, output_bib_path)
        os.remove(intermediate_path)

    # 以下为内部函数

    @classmethod
    def _extract_cite_keys(cls, tex_files):
        cite_keys = set()
        cite_pattern = re.compile(r'\\cite\{([^}]*)\}')
        for filepath in tex_files:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                matches = cite_pattern.findall(content)
                for match in matches:
                    keys = [key.strip() for key in match.split(',')]
                    cite_keys.update(keys)
        return cite_keys

    @classmethod
    def _filter_bib_entries(cls, input_bib_path, used_keys, output_bib_path):
        with open(input_bib_path, 'r', encoding='utf-8') as bib_file:
            content = bib_file.read()
        entry_pattern = re.compile(r'@[\w]+\{([^,]+),[\s\S]*?\n\}', re.MULTILINE)
        entries = list(entry_pattern.finditer(content))
        selected_entries = [entry.group(0).strip() for entry in entries if entry.group(1).strip() in used_keys]
        with open(output_bib_path, 'w', encoding='utf-8') as out_file:
            out_file.write('\n\n'.join(selected_entries))

    @classmethod
    def _clean_bib_file(cls, input_path, output_path):
        entries = cls._parse_bib_file_lines(input_path)
        cleaned = [cls._clean_bib_entry(e) for e in entries]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(cleaned))

    # These are name-format rules, not corrections of bibliographic metadata.
    _SURNAME_PREFIXES = {
        'van', 'von', 'de', 'del', 'della', 'da', 'das', 'do', 'dos',
        'der', 'den', 'ter', 'ten', 'du', 'des', 'la', 'le',
    }
    _ORGANIZATION_WORDS = {
        'academy', 'association', 'bank', 'center', 'centre', 'collaboration',
        'committee', 'company', 'consortium', 'corporation', 'council',
        'department', 'foundation', 'government', 'group', 'inc', 'institute',
        'laboratory', 'limited', 'ltd', 'nations', 'network', 'organization',
        'organisation', 'project', 'research', 'society', 'team', 'union',
        'university', 'who', 'nasa', 'cern', 'oecd', 'unesco',
    }
    # Optional exact literal names for organizations not covered by the rules.
    # Example: Bib.LITERAL_AUTHORS = {'Alpha Beta'}
    LITERAL_AUTHORS = set()

    @staticmethod
    def _name_group_end(text, start):
        """Return the end of one brace group, respecting escaped braces."""
        if start >= len(text) or text[start] != '{':
            raise ValueError('Expected a brace group in an author name')
        depth, pos = 1, start + 1
        while pos < len(text):
            if text[pos] == '\\':
                pos += 2
                continue
            depth += (text[pos] == '{') - (text[pos] == '}')
            if depth == 0:
                return pos + 1
            pos += 1
        raise ValueError('Unbalanced braces in an author name')

    @staticmethod
    def _split_name_parts(text, separator=','):
        """Split an author/list outside protected brace groups only."""
        result, start, pos, depth = [], 0, 0, 0
        while pos < len(text):
            char = text[pos]
            if char == '\\':
                pos += 2
                continue
            depth += (char == '{') - (char == '}')
            if depth < 0:
                raise ValueError('Unexpected closing brace in an author name')
            if depth == 0:
                if separator == 'and':
                    match = re.match(r'\s+and\s+', text[pos:], re.IGNORECASE)
                    size = len(match.group(0)) if match else 0
                else:
                    size = 1 if char == separator else 0
                if size:
                    result.append(text[start:pos].strip())
                    pos += size
                    start = pos
                    continue
            pos += 1
        if depth:
            raise ValueError('Unbalanced braces in an author name')
        result.append(text[start:].strip())
        return result

    @classmethod
    def _split_authors_safe(cls, s):
        return cls._split_name_parts(s, 'and')

    @classmethod
    def _looks_like_person(cls, name):
        """Recognize common braced Latin personal names conservatively.

        This is a formatting heuristic, not a verification of identity or
        cultural name order. Explicit comma form is preferred for ambiguity;
        use LITERAL_AUTHORS for exceptional organization/literal names.
        """
        if name in cls.LITERAL_AUTHORS:
            return False
        if re.search(r'\s+and\s+|\d|[&;]', name, re.IGNORECASE):
            return False
        tokens = re.sub(r'[{},]', ' ', name).split()
        if not 2 <= len(tokens) <= 7:
            return False
        if any(t.casefold().strip('.') in cls._ORGANIZATION_WORDS for t in tokens):
            return False
        for token in tokens:
            if token.casefold().strip('.') in cls._SURNAME_PREFIXES | {'jr', 'sr', 'ii', 'iii', 'iv'}:
                continue
            letters = ''.join(c for c in token if c.isalpha())
            if not letters or not all('LATIN' in unicodedata.name(c, '') for c in letters):
                return False
            if not letters[0].isupper() or (len(letters) > 1 and letters.isupper()):
                return False
        return True

    @classmethod
    def _normalize_author(cls, author):
        author = author.strip()
        if not author:
            return author
        if author in cls.LITERAL_AUTHORS:
            return '{' + author + '}'
        if author.startswith('{') and cls._name_group_end(author, 0) == len(author):
            inner = author[1:-1]
            if not cls._looks_like_person(inner):
                return author
            return cls._normalize_author(inner)

        parts = cls._split_name_parts(author)
        if len(parts) in (2, 3):
            family, given = parts[0], parts[-1]
            suffix = parts[1] if len(parts) == 3 else ''
        elif len(parts) == 1:
            tokens, pos = [], 0
            while pos < len(author):
                if author[pos].isspace():
                    pos += 1
                    continue
                start = pos
                while pos < len(author) and not author[pos].isspace():
                    if author[pos] == '{':
                        pos = cls._name_group_end(author, pos)
                    elif author[pos] == '\\':
                        pos += 2
                    else:
                        pos += 1
                tokens.append(author[start:pos])
            if not tokens:
                return author
            suffix = ''
            if len(tokens) >= 3 and tokens[-1].casefold().strip('.') in {'jr', 'sr', 'ii', 'iii', 'iv'}:
                suffix = tokens.pop()
            split = len(tokens) - 1
            for i, token in enumerate(tokens[:-1]):
                if token.casefold() in cls._SURNAME_PREFIXES and (i > 0 or token[0].islower()):
                    split = i
                    break
            given, family = ' '.join(tokens[:split]), ' '.join(tokens[split:])
        else:
            return author  # Do not guess about unusual comma structures.

        # Normalize an explicit initials artifact; never expand to guessed names.
        given = re.sub(r'\{\\relax\s+([A-Z]{2,5})\}',
                       lambda m: ' '.join(c + '.' for c in m.group(1)), given)
        if not family:
            return author
        result = [family]
        if suffix:
            result.append(suffix)
        if given:
            result.append(given)
        return ', '.join(result)

    @classmethod
    def _clean_author(cls, raw):
        """Accept both name orders and emit unambiguous Family, Given names.

        Preserve author order/count, literal authors, accents and protected
        surnames. No DOI lookups, metadata substitutions or deduplication.
        """
        value = raw.strip()
        if value.startswith('{') and cls._name_group_end(value, 0) == len(value):
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        authors = cls._split_authors_safe(value)
        return '{' + ' and '.join(cls._normalize_author(a) for a in authors) + '}'

    @staticmethod
    def _capitalize_initial(text):
        """Uppercase the first text letter without lowercasing the remainder.

        Leave an initial protected group, TeX command or math expression
        unchanged: its case can be intentional (for example, {pH}).
        """
        for index, char in enumerate(text):
            if char in ('{', '$', chr(92)):
                return text
            if char.isalpha():
                return text[:index] + char.upper() + text[index + 1:]
        return text

    @classmethod
    def _format_journal(cls, journal):
        words = journal.split()
        formatted = []
        for word in words:
            upper = word.upper()
            if upper in cls._FULL_UPPER_ACRONYMS:
                formatted.append(upper)
            elif word.lower() in cls._LOWERCASE_WORDS:
                formatted.append(word.lower())
            else:
                formatted.append(word.capitalize())
        return cls._capitalize_initial(' '.join(formatted))

    @classmethod
    def _parse_bib_file_lines(cls, input_path):
        entries = []
        with open(input_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_entry, brace_level = [], 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('@'):
                if current_entry:
                    entries.append('\n'.join(current_entry))
                    current_entry = []
                current_entry.append(line.rstrip())
                brace_level = line.count('{') - line.count('}')
            elif current_entry:
                current_entry.append(line.rstrip())
                brace_level += line.count('{') - line.count('}')
                if brace_level <= 0:
                    entries.append('\n'.join(current_entry))
                    current_entry = []

        if current_entry:
            entries.append('\n'.join(current_entry))
        return entries

    @classmethod
    def _clean_bib_entry(cls, entry_text):
        lines = entry_text.splitlines()
        header, fields, field_order = lines[0], {}, []
        current_field, buffer, brace_level = None, [], 0

        for line in lines[1:]:
            stripped = line.strip()
            if '=' in stripped and brace_level == 0:
                if current_field:
                    value = '\n'.join(buffer).strip().rstrip(',')
                    fields[current_field.lower()] = value
                    field_order.append(current_field.lower())
                current_field, buffer = stripped.split('=', 1)[0].strip(), [stripped.split('=', 1)[1].strip()]
                brace_level = buffer[0].count('{') - buffer[0].count('}')
            else:
                buffer.append(stripped)
                brace_level += stripped.count('{') - stripped.count('}')

        if current_field and buffer:
            value = '\n'.join(buffer).strip().rstrip(',')
            fields[current_field.lower()] = value
            field_order.append(current_field.lower())

        for f in cls.FIELDS_TO_REMOVE:
            fields.pop(f, None)

        if 'author' in fields:
            fields['author'] = cls._clean_author(fields['author'])
        if 'journal' in fields:
            val = fields['journal'].strip()
            if val.startswith('{') and val.endswith('}'):
                val = val[1:-1]
            fields['journal'] = '{' + cls._format_journal(val) + '}'
        if 'title' in fields:
            val = fields['title']
            # Skip only the field delimiter; preserve inner protection groups.
            if val.startswith(('{', '"')):
                fields['title'] = val[0] + cls._capitalize_initial(val[1:])
            else:
                fields['title'] = cls._capitalize_initial(val)

        new_entry = [header]
        for key in field_order:
            if key in fields:
                new_entry.append(f"  {key} = {fields[key]},")
        new_entry.append('}')
        return '\n'.join(new_entry)

