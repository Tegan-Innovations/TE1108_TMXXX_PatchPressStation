"""Current saved-camera regression scenarios; no historical artifacts or runtime access."""
from pathlib import Path
import re,runpy
import xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
h=runpy.run_path(str(Path(__file__).with_name('st_camera_runner.py')))
execute,initial=h['execute'],h['initial']
camera=E.parse(root/'TwinCAT Patch Press/PatchPress/POUs/02_Components/VS Keyence Camera/FB_VSCamera.TcPOU')
def method(name):return next(x.findtext('Implementation/ST') for x in camera.findall('.//Method') if x.get('Name')==name)
def clean(name):return re.sub(r'//[^\n]*','',method(name))
trigger=clean('RequestTrigger')
head,cases=trigger.split('CASE usiTriggerHandshake OF',1)
cases=cases.split('END_CASE',1)[0]
labels=list(re.finditer(r'(?m)^    (\d+:|ELSE)[ \t]*$',cases))
blocks={int(m[1][:-1]) if m[1].endswith(':') else None:cases[m.end():labels[i+1].start() if i+1<len(labels) else len(cases)] for i,m in enumerate(labels)}
capture=re.sub(r'tonInspectionRecovery\([^;]*\);','',clean('Cyclic'))
getter=clean('GetResultsReady')
ack=clean('RequestResultsAck')
reader=re.sub(r'tonInspectionRecovery\([^;]*\);','',clean('GetResults'))
loop=re.search(r'FOR uiErrorIndex := 1 TO 4 DO(.*?)END_FOR',reader,re.S)
reader=reader[:loop.start()]+''.join(loop[1].replace('[uiErrorIndex]',f'[{i}]') for i in range(1,5))+reader[loop.end():]

def new(program=0):
    v = initial(program)
    v.update({k: False for k in ['bResetRequest', 'bRecoverInspection', 'bRecoveryFailed',
        'bInspectionFailureForTrigger', 'bInspectionErrorLatched', 'bClearError0', 'bClearError1',
        'tonInspectionRecovery.Q', 'stCameraIO.abErrorClear[1]', 'stCameraIO.abErrorClear[2]']})
    v.update({'udiError0Code': 0, 'udiError1Code': 0})
    for i in range(1, 5):
        v[f'aInspectionError0[{i}]'] = v[f'aInspectionError1[{i}]'] = 0
    return v

def request(v, enabled=True):
    v['bEnable'] = enabled
    execute(head, v)
    if enabled and not v['bResetRequest'] and not v['bRecoverInspection'] and not v['bRecoveryFailed'] and v['usiTriggerHandshake'] != 35:
        execute(blocks.get(v['usiTriggerHandshake'], blocks[None]), v)

def ready(v):
    execute(getter, v)
    return v['GetResultsReady']

def accept(v):
    request(v)
    assert v['usiTriggerHandshake'] == 10
    v['stCameraIO.bTriggerAcknowledge'] = True
    request(v)
    assert v['usiTriggerHandshake'] == 20

for p in range(4):
    for channel in (1, 2):
        for code in (10130, 40008):
            v = new(p)
            accept(v)
            v[f'stCameraIO.abError[{channel}]'] = True
            v[f'udiError{channel-1}Code'] = code
            request(v)
            assert v['bRecoverInspection'] and not ready(v)
            execute(capture, v)
            assert v[f'stCameraIO.abErrorClear[{channel}]']
            assert not v['stCameraIO.bTrigger']
            assert v[f'stCapturedVisionResults.aInspectionCompleted[{p+1}]']
            assert not v[f'stCapturedVisionResults.aInspectionPassed[{p+1}]']
            assert v[f'aInspectionError{channel-1}[{p+1}]'] == code
            v[f'stCameraIO.abError[{channel}]'] = False
            v['stCameraIO.bTriggerAcknowledge'] = False
            v['stCameraIO.bResultsReady'] = True
            execute(capture, v)
            assert not ready(v) and v['stCameraIO.bResultAck']
            v['stCameraIO.bResultsReady'] = False
            v['stCameraIO.bTriggerReady'] = False
            execute(capture, v)
            assert not ready(v)
            v['stCameraIO.bTriggerReady'] = True
            execute(capture, v)
            assert ready(v) and not v['bRecoveryFailed']
            v['bResetResults'] = False
            execute(reader, v)
            assert not v[f'stVisionResults.aInspectionPassed[{p+1}]']
            v['bEnable'] = True
            execute(ack, v)
            assert not v['bResultPending']
            # Later programs retain the failed verdict and error identity.
            request(v, False)
            v['stCameraIO.bResultsReady'] = False
            v['bEnable'] = False
            execute(ack, v)
            v['stCameraIO.bCurrentProgramNumber'] = (p+1) % 4
            accept(v)
            v['stCameraIO.bResultsReady'] = True
            execute(capture, v)
            assert not v[f'stCapturedVisionResults.aInspectionPassed[{p+1}]']
            assert v[f'aInspectionError{channel-1}[{p+1}]'] == code
print('PASS four programs / both error channels / known codes: FAIL retained, clear bounded, no retrigger, handshake before consumption')

for condition in ('unknown', 'unmapped', 'preexisting', 'unacknowledged', 'program', 'run', 'mixed'):
    v = new()
    if condition != 'preexisting':
        accept(v)
    v['stCameraIO.abError[1]'] = True
    v['udiError0Code'] = 10130
    if condition == 'unknown': v['udiError0Code'] = 99999
    if condition == 'unmapped': v['udiError0Code'] = 0
    if condition == 'unacknowledged':
        v['usiTriggerHandshake'] = 10
        v['stCameraIO.bTriggerAcknowledge'] = False
    if condition == 'program': v['stCameraIO.bCurrentProgramNumber'] = 1
    if condition == 'run': v['stCameraIO.bRunStatus'] = False
    if condition == 'mixed':
        v['stCameraIO.abError[2]'] = True
        v['udiError1Code'] = 99999
    request(v)
    execute(capture, v)
    assert not v['bRecoverInspection'] and not v['bInspectionErrorLatched'], condition
    assert not v['stCameraIO.abErrorClear[1]'] and not v['stCameraIO.abErrorClear[2]']
print('PASS unknown/unmapped/pre-existing/mixed errors, missing ACK, wrong program and RUN loss never converted to product FAIL')

for channel in (1, 2):
    v = new(2)
    accept(v)
    v[f'stCameraIO.abError[{channel}]'] = True
    request(v)
    execute(capture, v)
    assert v['usiTriggerHandshake'] == 35 and not ready(v)
    assert not v[f'stCameraIO.abErrorClear[{channel}]']
    v[f'udiError{channel-1}Code'] = 10130
    request(v)
    execute(capture, v)
    assert v['bRecoverInspection'] and v[f'stCameraIO.abErrorClear[{channel}]']
    assert v[f'aInspectionError{channel-1}[3]'] == 10130
    assert not v['stCapturedVisionResults.aInspectionPassed[3]']

v = new(2)
accept(v)
v['stCameraIO.abError[2]'] = True
request(v)
v['tonInspectionRecovery.Q'] = True
execute(capture, v)
assert v['bRecoveryFailed'] and not v['stCameraIO.abErrorClear[2]'] and not ready(v)
print('PASS delayed numeric code recovers either channel; missing/unsupported code has bounded diagnostic fault without clearing')

for reason in ('timeout', 'newerror', 'program', 'run', 'stop', 'reset'):
    v = new()
    accept(v)
    v['stCameraIO.abError[1]'] = True
    v['udiError0Code'] = 10130
    request(v)
    if reason == 'timeout': v['tonInspectionRecovery.Q'] = True
    if reason == 'newerror': v['udiError0Code'] = 99999
    if reason == 'program': v['stCameraIO.bCurrentProgramNumber'] = 1
    if reason == 'run': v['stCameraIO.bRunStatus'] = False
    if reason == 'stop': request(v, False)
    if reason == 'reset':
        v['bResetRequest'] = True
        request(v)
    execute(capture, v)
    assert not v['stCameraIO.abErrorClear[1]'] and not v['stCameraIO.abErrorClear[2]'], reason
    assert not ready(v), reason
    assert v['bRecoveryFailed'] == (reason not in ('stop', 'reset')), reason
print('PASS recovery timeout/change-of-error/mode/program loss escalates; Stop and Reset withdraw error-clear outputs')

# Existing valid PASS/FAIL and short-pulse latch remain exercised through new source.
for passed in (False, True):
    v = new()
    accept(v)
    v['stCameraIO.bResultsReady'] = True
    v['stCameraIO.bGeneralPass'], v['stCameraIO.bGeneralFail'] = passed, not passed
    execute(capture, v)
    v['stCameraIO.bResultsReady'] = False
    execute(capture, v)
    assert ready(v) and v['stCapturedVisionResults.aInspectionPassed[1]'] == passed
    v['bResetResults'] = True
    execute(reader, v)
    assert not v['bResultPending'] and not v['bInspectionErrorLatched']
    assert all(v[f'aInspectionError0[{i}]'] == 0 and v[f'aInspectionError1[{i}]'] == 0 for i in range(1,5))
print('PASS normal PASS/FAIL pulse capture and new-piece reset')
print('Source/model checks only: camera error-clear behavior, physical sequence and HMI require commissioning.')
