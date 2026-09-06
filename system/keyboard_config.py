"""Merge the global CapsLock preset without replacing unrelated keyd mappings."""
import re

MAPPINGS = {'j': 'up', 'k': 'down', 'l': 'left', 'semicolon': 'right'}


def configure(text):
    if not text.strip():
        text = '[ids]\n*\n\n[main]\n'
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    def set_values(section, values):
        headers = [(i, m.group(1).strip()) for i, line in enumerate(lines)
                   if (m := re.fullmatch(r'\s*\[([^\]]+)\]\s*\n?', line))]
        matches = [i for i, name in headers if name == section]
        if len(matches) > 1:
            raise ValueError('Duplicate keyd section: ' + section)
        if not matches:
            lines.extend(['\n', '[' + section + ']\n'])
            start, end = len(lines)-1, len(lines)
        else:
            start = matches[0]
            end = next((i for i, _ in headers if i > start), len(lines))
        pending = dict(values)
        seen = set()
        for i in range(start+1, end):
            key = lines[i].split('=', 1)[0].strip() if '=' in lines[i] else ''
            if key in values:
                if key in seen:
                    raise ValueError('Duplicate keyd mapping: ' + section + '.' + key)
                seen.add(key)
                lines[i] = key + ' = ' + pending.pop(key) + '\n'
        lines[end:end] = [key + ' = ' + value + '\n' for key, value in pending.items()]

    if not re.search(r'^\s*\[ids\]\s*$', text, re.M):
        raise ValueError('Existing keyd configuration has no [ids] section; review device selection first')
    set_values('main', {'capslock': 'overload(agents_capslock, f24)'})
    set_values('agents_capslock', MAPPINGS)
    set_values('global', {'overload_tap_timeout': '250'})
    return ''.join(lines)
