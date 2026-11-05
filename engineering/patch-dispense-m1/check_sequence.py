"""Execute saved station ST against scripted feedback; no ADS or equipment access."""
from pathlib import Path
import re,json,runpy
import xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
h=runpy.run_path(str(root/'engineering/patch-feeding/implementation/st_branch_runner.py'))
plc=root/'TwinCAT Patch Press/PatchPress'
t=E.parse(plc/'POUs/03_Stations/PatchDispense/FB_PatchDispenseStation.TcPOU')
raw=next(m.findtext('Implementation/ST') for m in t.findall('.//Method') if m.get('Name')=='Cyclic')
def prepare(source):
    source=re.sub(r'//[^\n]*','',source)
    source=re.sub(r"'(?:''|[^'])*'",'0',source)
    source=re.sub(r'\bton\w+\([^;]*\);','',source,flags=re.S)
    stack=[];out=[]
    for line in source.splitlines():
        m=re.match(r'\s*CASE (\w+) OF\s*$',line)
        if m:stack.append([m[1],True]);continue
        if re.match(r'\s*END_CASE\s*;?$',line):out.append('END_IF');stack.pop();continue
        m=re.match(r'\s*(\d+):\s*(.*)',line)
        if m and stack:
            name,first=stack[-1];out.append(('IF ' if first else 'ELSIF ')+name+' = '+m[1]+' THEN '+m[2]);stack[-1][1]=False
        else:out.append(line)
    assert not stack
    return '\n'.join(out)
code=prepare(raw)
enum='E_PatchStationState.'
states={enum+k:v for k,v in [('Disabled',0),('Homing',10),('Ready',20),('Processing',30),('Complete',40),('Fault',100)]}
def initial(feed_only=False,step=10):
    v={token:0 for token in re.findall(h['var'],code)}
    v.update(states)
    v.update({'bEnableInternal':True,'bCommissionedInternal':True,'bSafetyOkInternal':True,
        'bUseVerticalFeedbackInternal':True,
        'bSupervisionEnableInternal':True,'bVerticalUpInternal':True,'bDriveStandstillInternal':True,
        'bSupportRetractedInternal':True,'eStateInternal':30,'usiStepInternal':step,'bFeedOnlyInternal':feed_only})
    return v
def scan(v,**kw):
    v.update(kw);h['execute'](code,v)
    assert not (v['bVerticalUpRequestInternal'] and v['bVerticalDownRequestInternal'])
    assert not (v['bSupportExtendRequestInternal'] and v['bSupportRetractRequestInternal'])
    return v
for initially_present in [False,True]:
    v=initial();scan(v)
    assert v['bSupportExtendRequestInternal'] and not v['bDriveRunRequestInternal']
    scan(v,bSupportRetractedInternal=False,bSupportExtendedInternal=True)
    assert v['usiStepInternal']==20
    scan(v,bPatchOpticalLeftInternal=initially_present)
    assert v['bDriveRunRequestInternal'] and bool(v['bAirBlowRequestInternal'])==initially_present
    if not initially_present:
        assert v['usiStepInternal']==20
        scan(v,bPatchOpticalLeftInternal=True,bDriveMovingInternal=True,bDriveStandstillInternal=False,bDriveBusyInternal=True)
    scan(v,bPatchOpticalLeftInternal=True,bDriveMovingInternal=True,bDriveStandstillInternal=False,bDriveBusyInternal=True)
    assert v['usiStepInternal']==21 and v['bAirBlowRequestInternal']
    scan(v,bPatchOpticalLeftInternal=False)
    assert v['usiStepInternal']==22 and not v['bDriveRunRequestInternal'] and not v['bVerticalDownRequestInternal']
    scan(v,bDriveMovingInternal=False)
    assert v['usiStepInternal']==22 and not v['bVerticalDownRequestInternal']
    scan(v,bDriveStandstillInternal=True,bDriveBusyInternal=False)
    assert v['usiStepInternal']==40
    scan(v)
    assert v['bVerticalDownRequestInternal'] and v['bAirBlowRequestInternal']
    scan(v,bVerticalUpInternal=False,bVerticalDownInternal=True)
    assert v['usiStepInternal']==50 and not v['bAirBlowRequestInternal']
    scan(v)
    assert v['usiStepInternal']==50 and not v['bVerticalUpRequestInternal'] and not v['bAirBlowRequestInternal']
    scan(v,**{'tonRelease.Q':True})
    assert v['usiStepInternal']==60
    scan(v,**{'tonRelease.Q':False})
    assert v['bVerticalUpRequestInternal'] and not v['bSupportRetractRequestInternal']
    scan(v,bVerticalUpInternal=True,bVerticalDownInternal=False)
    assert v['usiStepInternal']==30
    scan(v)
    assert v['bSupportRetractRequestInternal']
    scan(v,bSupportRetractedInternal=True,bSupportExtendedInternal=False)
    assert v['bCompleteInternal'] and v['stResultInternal.bValid'] and v['stResultInternal.bPassed']
print('PASS full dispense with Input6 initially 0 or 1; motor standstill, air cutoff, dwell, vertical UP before nest DOWN')
v=initial(feed_only=True,step=20)
for inputs in [dict(bPatchOpticalLeftInternal=True),dict(bDriveMovingInternal=True,bDriveStandstillInternal=False,bDriveBusyInternal=True),dict(bPatchOpticalLeftInternal=False),dict(bDriveMovingInternal=False,bDriveStandstillInternal=True,bDriveBusyInternal=False)]:
    scan(v,**inputs)
    assert not any(v[k] for k in ['bAirBlowRequestInternal','bVerticalUpRequestInternal','bVerticalDownRequestInternal','bSupportExtendRequestInternal','bSupportRetractRequestInternal'])
assert v['bCompleteInternal'] and not v['stResultInternal.bValid']
print('PASS feed-only performs no pneumatic actuation or product PASS')
for interrupted in [10,20,21,22,40,50,60,30]:
    v=initial(step=interrupted)
    scan(v,bStopRequestInternal=True,bDriveStandstillInternal=False,bDriveBusyInternal=True,bVerticalUpInternal=interrupted in [10,20,21,22,30],bVerticalDownInternal=interrupted not in [10,20,21,22,30],bSupportRetractedInternal=False,bSupportExtendedInternal=True)
    assert v['usiStepInternal']==90 and not v['bSupportRetractRequestInternal'] and not v['bVerticalUpRequestInternal']
    scan(v,bDriveStandstillInternal=True,bDriveBusyInternal=False,bVerticalUpInternal=False,bVerticalDownInternal=True)
    scan(v)
    assert v['bVerticalUpRequestInternal'] and not v['bSupportRetractRequestInternal']
    scan(v,bVerticalUpInternal=True,bVerticalDownInternal=False)
    scan(v)
    assert v['bSupportRetractRequestInternal']
print('PASS stop at every process step stops M1 then raises vertical then lowers nest')
for key in ['tonFeed.Q','tonVertical.Q','tonHomeVerticalUp.Q','tonSupportExtendTimeout.Q','tonSupportRetractTimeout.Q']:
    v=initial();scan(v,**{key:True})
    assert v['bFaultInternal'] and not any(v[k] for k in ['bDriveRunRequestInternal','bAirBlowRequestInternal','bSupportExtendRequestInternal','bSupportRetractRequestInternal','bVerticalUpRequestInternal','bVerticalDownRequestInternal'])
v=initial();scan(v,bVerticalDownInternal=True)
assert v['bFaultInternal']
v=initial(step=21);scan(v,bSafetyOkInternal=False)
assert v['eStateInternal']==0 and not v['bDriveRunRequestInternal'] and not v['bAirBlowRequestInternal']
print('PASS feedback conflicts, bounded feed/vertical/support faults and safety withdrawal clear outputs')
v=initial(step=50);scan(v,bSupportRetractedInternal=False,bSupportExtendedInternal=True,bVerticalUpInternal=False,bVerticalDownInternal=False)
assert v['bFaultInternal'], 'lost DOWN during release dwell'
v=initial(step=20);scan(v,bSupportRetractedInternal=False,bSupportExtendedInternal=True,bVerticalUpInternal=False)
assert v['bFaultInternal'], 'lost UP during feeding'
v=initial(step=10);scan(v,bVerticalUpInternal=False)
assert not v['bSupportExtendRequestInternal'], 'vertical clearance before raising nest'
print('PASS vertical UP loss, DOWN loss during dwell and clearance before raising nest')

# HOME now waits for actual vertical feedback, not a timed claim.
v=initial();v.update({'bHomeRequestInternal':True,'bHomingAllowedInternal':True,'eStateInternal':0})
scan(v);scan(v,**{'tonHomeSupportRetract.Q':True});scan(v,**{'tonHomeSupportRetract.Q':False});scan(v,bVerticalUpInternal=False)
assert not v['bHomeInternal'] and v['bVerticalUpRequestInternal']
scan(v,bVerticalUpInternal=True)
assert v['bHomeInternal']
print('PASS HOME uses existing support pulse and real vertical UP feedback')

machine=E.parse(plc/'POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU')
s=next(m.findtext('Implementation/ST') for m in machine.findall('.//Method') if m.get('Name')=='Cyclic')
assert 'AND bPatchVerticalIndexReady' in s
assert 'bVerticalUp := stInputs.bMembraneTransferRetracted' in s
assert 'bVerticalDown := stInputs.bMembraneTransferExtended' in s
assert 'bIndexerManualEnable' in s and 'AND NOT fbPatchDispense.IsBusy() AND NOT fbPatchFeedManager.stStatus.bDriveBusy' in s
arb=s[s.index('bPatchHoldUpAllowed :='):s.index('// Same criterion used by the validated Silicone Station:')]
arb=prepare(arb.replace('fbPatchDispense.IsBusy()','bStationBusy'))
v={token:0 for token in re.findall(h['var'],arb)}
v.update({'E_MachineState.AutoCycle':6,'E_MachineState.Manual':7,'E_MachineState.Initialising':4,
    'E_MachineState.Stopping':2,'eMachineState':6,'bPatchDispenseCommissioned':True,'stInputs.stSafety.bSafetyOk':True,
    'stInputs.bMainDoorClosed':True,'GVL_Safety.bAirSupplySafe':True,'bStationBusy':True})
h['execute'](arb,v)
assert not v['stOutputsInternal.bPatchVerticalUp'], 'Auto hold must not interrupt sequence dwell/stop recovery'
v['bPatchSequenceDownRequest']=True;h['execute'](arb,v)
assert v['stOutputsInternal.bPatchVerticalDown'] and not v['stOutputsInternal.bPatchVerticalUp']
v.update({'bStationBusy':False,'bPatchSequenceDownRequest':False});h['execute'](arb,v)
assert v['stOutputsInternal.bPatchVerticalUp']
v.update({'eMachineState':7,'stCommand.bIndexerManualEnable':True,'bPatchManualAllowed':False});h['execute'](arb,v)
assert v['stOutputsInternal.bPatchVerticalUp'], 'Manual indexing holds UP even with Patch manual enable off'
v.update({'eMachineState':2,'stIndexStatus.bBusy':True});h['execute'](arb,v)
assert v['stOutputsInternal.bPatchVerticalUp'], 'controlled Stop must retain UP while an index is completing'
v['stInputs.stSafety.bSafetyOk']=False;h['execute'](arb,v)
assert not v['stOutputsInternal.bPatchVerticalUp'] and not v['stOutputsInternal.bPatchVerticalDown']
print('PASS actuator arbitration: Auto/Manual index hold-UP, exclusive sequence/dwell control, opposite coils and safety withdrawal')
mapping=(plc/'POUs/04_IO_Mapping/PRG_TerminalMapping.TcPOU').read_text(encoding='utf-8-sig')
assert 'bPatchOpticalLeft := GVL_EtherCAT.stTerm19_EL1809.iEL1809_Ch6' in mapping
assert '// bPatchOpticalRight := GVL_EtherCAT.stTerm19_EL1809.iEL1809_Ch5;' in mapping
content=(root/'TwinCAT Patch Press/PatchPress_HMI/Contents/Screens/ManualTabs/PatchTab.content').read_text()
config=json.loads((root/'TwinCAT Patch Press/PatchPress_HMI/Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
for control,symbol in [('TcHmiButton_PatchDispense','stCommands.bPatchDispenseRequest'),('TcHmiButton_PatchRunSequence','stCommands.bPatchManualRunSequence'),('TcHmiHtmlHost_PatchReady','stStatus.stPatchDispense.bReady'),('TcHmiHtmlHost_PatchBusy','stStatus.stPatchDispense.bBusy'),('TcHmiHtmlHost_PatchFault','stStatus.stPatchDispense.bFault')]:
    block=re.search(r'<div\b[^>]*\bid="'+control+r'"[^>]*>.*?</div>',content,re.S).group()
    assert 'ADS.PLC1.GVL_HMI.'+symbol in block
    assert 'ADS.PLC1.GVL_HMI.'+symbol in config['SYMBOLS']
for script in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',content,re.S):json.loads(script)
print('PASS physical mapping, index gates, native saved HMI actions/status bindings and server symbol declarations')
