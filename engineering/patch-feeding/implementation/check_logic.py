"""Execute bounded saved-ST control branches with scripted PLCopen feedback.

This checks sequencing/ownership, not MC library dynamics or physical safety.
"""
from pathlib import Path
import re
import contextlib
import io
import xml.etree.ElementTree as E

root=Path(__file__).resolve().parents[3]
helper=Path(__file__).with_name('st_branch_runner.py')
h={}
exec(helper.read_text(),h)
plc=root/'TwinCAT Patch Press/PatchPress'
def code(path):
    tree=E.parse(plc/path)
    return re.sub(r'//[^\n]*','',next(x.findtext('Implementation/ST') for x in tree.findall('.//Method') if x.get('Name')=='Cyclic'))
def without_calls(s):
    s=re.sub(r"'(?:''|[^'])*'",'0',s)
    s=re.sub(r'stAxis\.Axis\.ReadStatus\(\);','',s)
    return re.sub(r'\b(?:fb\w+(?:\.Cyclic)?|ton\w+)\([^;]*\);','',s,flags=re.S)
axis=code('POUs/02_Components/Motion/FB_PatchFeedAxis.TcPOU')
axis=without_calls(axis)
pre,cases=axis.split('CASE usiState OF',1)
cases,post=cases.split('END_CASE',1)
labels=list(re.finditer(r'(?m)^    (\d+):',cases))
blocks={int(m[1]):cases[m.end():labels[i+1].start() if i+1<len(labels) else len(cases)] for i,m in enumerate(labels)}
manager=without_calls(code('POUs/03_Stations/PatchDispense/FB_PatchFeedManager.TcPOU'))

def initial(source):
    # Numeric zero is the IEC default for these scripted boolean/numeric inputs.
    v={token:0 for token in re.findall(h['var'],source)}
    v.update({'MC_Positive_Direction':1,'MC_Negative_Direction':-1})
    return v
def axis_scan(v):
    h['execute'](pre,v)
    if v['stAxis.Axis.NcToPlc.AxisId']==0:return
    h['execute'](blocks[v['usiState']],v)
    h['execute'](post,v)

v=initial(axis)
v.update({'stAxis.Axis.NcToPlc.AxisId':3,'bSafetyOk':True,'stAxis.Axis.Status.StandStill':True,
    'bControlRequest':True,'fbPower.Status':True,'lrVelocity':50.0,'eDirection':1})
axis_scan(v)
assert v['usiState']==20 and v['bPowerRequest'] and not v['bMoveExecute']
v['bRunVelocity']=True
axis_scan(v)
assert v['usiState']==30 and v['bMoveExecute'] and v['lrCommandVelocity']==50
v['lrVelocity']=99
axis_scan(v)
assert v['bMoveExecute'] and v['lrCommandVelocity']==50, 'no live retarget/retrigger'
v['stAxis.Axis.Status.StandStill']=False
v['bRunVelocity']=False
axis_scan(v)
assert v['usiState']==40 and v['bHaltExecute'] and v['bPowerRequest'] and not v['bMoveExecute']
v['bRunVelocity']=True
v['stAxis.Axis.Status.StandStill']=True
v['fbHalt.Busy']=True
v['fbVelocity.Busy']=True
axis_scan(v)
assert v['usiState']==40 and not v['bMoveExecute'], 'do not restart during pending stop'
v['fbHalt.Busy']=False;v['fbVelocity.Busy']=False;v['fbHalt.Done']=True
axis_scan(v)
assert v['usiState']==20 and not v['bMoveExecute']
v['fbHalt.Done']=False
v['bControlRequest']=False
axis_scan(v)
assert v['usiState']==40 and v['bPowerRequest']
v['fbHalt.Done']=True
axis_scan(v)
assert v['usiState']==50 and not v['bPowerRequest']
v['stAxis.Axis.Status.Disabled']=True
axis_scan(v)
assert v['usiState']==0 and not v['bMoveExecute']
print('PASS axis power/wait/start, held execute, immutable command, sensor halt, stop completion, no restart during halt, release')

for reason in ('safety','ncerror','power_timeout','stop_timeout','invalid_velocity','unlinked'):
    v=initial(axis)
    v.update({'stAxis.Axis.NcToPlc.AxisId':3,'bSafetyOk':True,'bControlRequest':True,
        'usiState':30,'bRunVelocity':True,'lrVelocity':50,'eDirection':1})
    if reason=='safety':v['bSafetyOk']=False
    if reason=='ncerror':v['stAxis.Axis.Status.ErrorStop']=True;v['stAxis.Axis.NcToPlc.ErrorCode']=17744
    if reason=='power_timeout':v['usiState']=10;v['tonPower.Q']=True
    if reason=='stop_timeout':v['usiState']=40;v['tonStop.Q']=True
    if reason=='invalid_velocity':v.update({'usiState':20,'lrVelocity':0,'fbPower.Status':True,'stAxis.Axis.Status.StandStill':True})
    if reason=='unlinked':v['stAxis.Axis.NcToPlc.AxisId']=0
    axis_scan(v)
    assert not v['bMoveExecute'],reason
    if reason!='invalid_velocity':assert not v['bPowerRequest'],reason
    if reason!='safety':assert v['bFault'],reason
print('PASS safety withdrawal, NC error propagation, bounded power/stop waits, invalid speed and missing axis link')

v=initial(manager)
v.update({'bPermit':True,'bSafetyOk':True,'stSettings.bWasteRollConfigured':True,'stWasteRoll.bOperational':True})
def scan(**inputs):
    v.update(inputs);h['execute'](manager,v)
scan(bMiddleDown=True)
assert v['bWasteRun']
scan(bMiddleDown=False)
assert v['bWasteRun'], 'retain demand in rocker gap'
scan(bTopUp=True)
assert not v['bWasteRun']
scan(bTopDown=True)
assert v['bWasteRun'], 'DOWN keeps demand even if another upper sensor is present'
scan(bTopDown=False)
assert not v['bWasteRun']
scan(bTopUp=False,bMiddleDown=True)
assert v['bWasteRun']
scan(bPermit=False)
assert not v['bWasteRun']
scan(bPermit=True,bMiddleDown=False,bTopUp=False)
assert not v['bWasteRun'], 'new permission alone cannot restore old latch in sensor gap'
scan(bTopDown=True)
v['tonWasteRun.Q']=True
scan()
assert v['bFaultLatched'] and v['stStatus.udiErrorId']==1101 and not v['bWasteRun']
v['tonWasteRun.Q']=False
scan()
assert v['stStatus.udiErrorId']==1101, 'retain fault cause after timer resets'
scan(bReset=True,bPermit=False)
assert not v['bFaultLatched'] and not v['bWasteRun']
scan(bReset=False)
v['fbDriveMotor.bFault']=True;v['fbDriveMotor.udiErrorId']=17744
scan(bPermit=True)
assert v['bFaultLatched'] and v['stStatus.udiErrorId']==17744 and not v['bWasteRun']
scan(bReset=True,bPermit=False,**{'stDriveMotor.bError':True,'fbDriveMotor.bResetBusy':True})
assert v['bResetPending'] and not v['stStatus.bFault'] and not v['bWasteRun']
scan(bReset=False,**{'fbDriveMotor.bFault':False,'fbDriveMotor.bResetBusy':False})
assert not v['bResetPending'] and not v['bWasteRun']
v['stSettings.bWasteRollConfigured']=False
scan(bPermit=True)
assert not v['bWasteRun']
print('PASS sensor hysteresis, mode/stop loss, no stale demand resume, watchdog cause latch, peer NC error and async operator reset')

# Caller/ownership and controlled-stop integration checks use real saved source.
raw=E.parse(plc/'POUs/03_Stations/PatchDispense/FB_PatchFeedManager.TcPOU')
raw=next(x.findtext('Implementation/ST') for x in raw.findall('.//Method') if x.get('Name')=='Cyclic')
call=raw.split('fbDriveMotor.Cyclic(',1)[1].split(');',1)[0]
assert 'bControlRequest := bDrivePermit' in call and 'bRunVelocity := bDriveRunRequest AND bDrivePermit' in call
assert 'eDirection := MC_Negative_Direction' in call
call=raw.split('fbPatchFeedRoll.Cyclic(',1)[1].split(');',1)[0]
assert 'eDirection := MC_Positive_Direction' in call and 'bRunVelocity := bPatchFeedRun' in call
v=initial(manager)
v.update({'bPermit':True,'bSafetyOk':True,'stSettings.bWasteRollConfigured':True})
scan(bPatchFeedStart=True)
assert v['bPatchFeedRun'] and v['stStatus.bPatchFeedRollDemand']
scan(bPatchFeedStart=False)
assert v['bPatchFeedRun'], 'Input14 can clear before Input13 arrives'
scan(bPatchFeedStop=True)
assert not v['bPatchFeedRun']
scan(bPatchFeedStart=True)
assert not v['bPatchFeedRun'], 'Input13 stop priority on overlapping sensors'
scan(bPatchFeedStop=False,bMiddleDown=True)
assert v['bPatchFeedRun'] and v['bWasteRun'], 'independent simultaneous demand'
scan(bPatchFeedStop=True)
assert not v['bPatchFeedRun'] and v['bWasteRun'], 'M2 stop does not clear M3'
scan(bPatchFeedStop=False,bPermit=False)
assert not v['bPatchFeedRun'] and not v['bWasteRun']
scan(bPermit=True,bPatchFeedStart=False,bMiddleDown=False)
assert not v['bPatchFeedRun'], 'permission alone does not restore stale M2 demand'
scan(bPatchFeedStart=True)
scan(**{'tonPatchFeedRun.Q':True})
assert v['stStatus.udiErrorId']==1103 and not v['bPatchFeedRun'] and not v['bWasteRun']
scan(**{'tonPatchFeedRun.Q':False})
assert v['stStatus.udiErrorId']==1103
scan(bReset=True)
assert not v['bPatchFeedRun'] and not v['stStatus.bFault']
scan(bReset=False,bPatchFeedStart=False,**{'fbPatchFeedRoll.bBusy':True})
assert v['stStatus.bBusy'], 'controlled stop waits for M2 alone'
scan(bPatchFeedStart=True,bSafetyOk=False)
assert not v['bPatchFeedRun']
print('PASS M2 start/gap/stop priority, independent M3 demand, permission/safety loss, watchdog/reset and combined stopping status')
machine=code('POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU')
assert machine.count('fbPatchFeedManager.Cyclic(')==1
assert 'AND NOT fbPatchFeedManager.stStatus.bBusy' in machine
assert 'tonStopping(IN := stIndexStatus.bBusy OR fbPatchFeedManager.stStatus.bBusy' in machine
assert 'OR ((eMachineState = E_MachineState.Stopping) AND fbPatchFeedManager.stStatus.bBusy)' in machine
assert 'bProcessSafePosition := NOT fbPatchFeedManager.stStatus.bBusy' in machine
assert 'AND stCommand.bPatchManualEnable' in machine and 'AND NOT stCommand.bStop' in machine
assert 'bPatchFeedStart := stInputs.bBottomRockerUp' in machine
assert 'bPatchFeedStop := stInputs.bBottomRockerDown' in machine
settings=E.parse(plc/'DUTs/02_Components/Motion/ST_PatchFeedSettings.TcDUT').findtext('.//Declaration')
assert 'lrPatchFeedRollVelocity : LREAL := 10.0;' in settings
print('PASS single manager call, M1 explicit dispense demand/negative direction, M2 mapped channels/10 mm/s, Manual/Stop gates and lock retention')
