"""Bounded ST branch interpreter for offline scripted feedback tests only."""
import re
import copy

var = r'[A-Za-z_]\w*(?:\[(?:\d+|[A-Za-z_]\w*)\]|\.[A-Za-z_]\w*)*'
tokens = re.compile(rf'ELSIF\b.*?\bTHEN|IF\b.*?\bTHEN|ELSE\b|END_IF\b;?|RETURN;|{var}\s*:=\s*[^;]+;', re.S)

def key(name, state):
    return re.sub(r'\[([A-Za-z_]\w*)\]', lambda m: '[' + str(state[m[1]]) + ']', name)

def expression(text, state):
    def sub(match):
        token = match[0]
        words = {'TRUE': 'True', 'FALSE': 'False', 'AND': 'and', 'OR': 'or', 'NOT': 'not',
                 'XOR': '^', 'UDINT_TO_UINT': 'int', 'GetDate': 'date', 'GetBatchNumber': 'batch'}
        return words.get(token, 'v[' + repr(key(token, state)) + ']')
    parts = re.split(r"('(?:[^']|'')*')", text)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(var, sub, parts[i]).replace('<>', '!=')
        parts[i] = re.sub(r'(?<![<>!:=])=(?!=)', '==', parts[i])
    return eval(' '.join(''.join(parts).split()), {'__builtins__': {}},
                {'v': state, 'int': int, 'date': lambda: state['rawDate'], 'batch': lambda: state['rawBatch']})

def execute(code, state):
    stack, position = [], 0
    for match in tokens.finditer(code):
        assert not code[position:match.start()].strip(), code[position:match.start()]
        position = match.end()
        token = match[0].strip()
        active = all(f['active'] for f in stack)
        if token.startswith('ELSIF'):
            f = stack[-1]
            f['active'] = f['parent'] and not f['taken'] and bool(expression(token[5:-4].strip(), state))
            f['taken'] = f['taken'] or f['active']
        elif token.startswith('IF'):
            selected = active and bool(expression(token[2:-4].strip(), state))
            stack.append({'parent': active, 'active': selected, 'taken': selected})
        elif token.startswith('ELSE'):
            f = stack[-1]
            f['active'] = f['parent'] and not f['taken']
            f['taken'] = True
        elif token.startswith('END_IF'):
            stack.pop()
        elif active:
            if token == 'RETURN;':
                return
            lhs, rhs = (s.strip() for s in token[:-1].split(':=', 1))
            lhs = key(lhs, state)
            if rhs in ('stEmptyVisionResults', 'stCapturedVisionResults'):
                fields = {k[len(rhs)+1:]: copy.deepcopy(v) for k, v in state.items() if k.startswith(rhs + '.')}
                for k in list(state):
                    if k.startswith(lhs + '.'):
                        del state[k]
                state.update({lhs + '.' + k: v for k, v in fields.items()})
            else:
                state[lhs] = expression(rhs, state)
    assert not stack and not code[position:].strip()
