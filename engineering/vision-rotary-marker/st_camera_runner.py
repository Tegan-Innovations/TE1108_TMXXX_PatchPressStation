"""Bounded ST execution helper with camera payload stubs; no hardware access."""
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
                 'XOR': '^', 'CONCAT': 'cat', 'UINT_TO_STRING': 'str', 'UDINT_TO_STRING': 'str', 'UDINT_TO_UINT': 'int', 'GetDate': 'date', 'GetBatchNumber': 'batch'}
        return words.get(token, 'v[' + repr(key(token, state)) + ']')
    parts = re.split(r"('(?:[^']|'')*')", text)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(var, sub, parts[i]).replace('<>', '!=')
        parts[i] = re.sub(r'(?<![<>!:=])=(?!=)', '==', parts[i])
    return eval(' '.join(''.join(parts).split()), {'__builtins__': {}},
                {'v': state, 'int': int, 'str': str, 'cat': lambda a, b: a + b, 'date': lambda: state['rawDate'], 'batch': lambda: state['rawBatch']})

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


def initial(program=0):
    v = {'usiTriggerHandshake': 0, 'nTriggerProgram': program, 'nResultProgram': 0,
         'bResultPending': False, 'bResultAccepted': False, 'bResultRead': False,
         'bResultCapturedForTrigger': False, 'bTriggerRequestActive': False,
         'stCameraIO.bTrigger': False, 'stCameraIO.bTriggerReady': True,
         'stCameraIO.bTriggerAcknowledge': False, 'stCameraIO.bProgramLoadExecute': False,
         'stCameraIO.bResultAck': False, 'stCameraIO.bResultsReady': False,
         'stCameraIO.bRunStatus': True, 'stCameraIO.abError[1]': False,
         'stCameraIO.abError[2]': False, 'stCameraIO.bCurrentProgramNumber': program,
         'stCameraIO.bGeneralPass': True, 'stCameraIO.bGeneralFail': False,
         'rawDate': '20261103', 'rawBatch': 'BATCH123'}
    fields = {'sDate': '', 'nPBUBMagnetOK': 0, 'nPBUBOK': 0, 'nBluePartPresent': 0,
              'nBottomPatchok': 0, 'nTopPatchok': 0, 'bGeneralPass': False, 'bGeneralFail': False}
    fields.update({f'sPatchNumber[{i}]': '' for i in (1, 2)})
    fields.update({f'nClickPartPresent[{i}]': 0 for i in (1, 2)})
    fields.update({f'aInspectionCompleted[{i}]': False for i in range(1, 5)})
    fields.update({f'aInspectionPassed[{i}]': False for i in range(1, 5)})
    for name in ('stEmptyVisionResults', 'stCapturedVisionResults'):
        v.update({name + '.' + k: x for k, x in fields.items()})
    v.update({f'stCameraIO.bToolJudge[{i}]': True for i in range(8)})
    return v
