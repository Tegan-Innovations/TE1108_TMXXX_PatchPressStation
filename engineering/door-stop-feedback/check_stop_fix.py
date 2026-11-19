from pathlib import Path
import json,re,xml.etree.ElementTree as E,itertools
base=Path(__file__).parent;root=base.parents[1];c=json.loads((base/'stop-fix-final.json').read_text());old=c['before']['implementation'];new=c['proposal']['newImplementation']
test=root/'engineering/patch-dispense-m1/check_sequence.py';ctx={'__file__':str(test)};s=test.read_text();exec(s[:s.index('for initially_present')],ctx);h=ctx['h'];prepare=ctx['prepare']
def expr(raw,pattern):return re.sub(r'//[^\n]*','',re.search(pattern,raw,re.S).group(1)).strip()
permit=lambda raw:expr(raw,r'bDrivePermit := (.*?),\s*bDriveRunRequest')
lock=lambda raw:expr(raw,r'stOutputsInternal.bMainDoorLockRequest :=\s*(.*?);')
enable=expr(new,r'bEnableAutomatic := (.*?),\s*bManualEnable')
axis=E.parse(root/'TwinCAT Patch Press/PatchPress/POUs/02_Components/Motion/FB_PatchFeedAxis.TcPOU').find(".//Method[@Name='Cyclic']").findtext('Implementation/ST')
start=axis.index('IF (usiState = 0)');end=axis.index('// No MC_Power',start);axiscode=prepare(axis[start:end]+re.search(r'bBusy := \(usiState.*?;',axis).group())
enums={'E_MachineState.Stopping':2,'E_MachineState.Stopped':3,'E_MachineState.Initialising':4,'E_MachineState.ReadyToStart':5,'E_MachineState.AutoCycle':6,'E_MachineState.Manual':7,'MC_Positive_Direction':1,'MC_Negative_Direction':2}
def initial(axisstate):
 v={x:0 for x in re.findall(h['var'],axiscode+permit(new)+lock(new)+enable)};v.update(enums)
 v.update({'eMachineState':5,'ePreviousMachineState':5,'usiState':axisstate,'bPatchDispenseCommissioned':True,'stInputs.bMainDoorClosed':True,'GVL_Safety.bAirSupplySafe':True,'bSafetyOk':True,'stAxis.bStandstill':axisstate!=30,'fbPower.Status':True,'fbHalt.Done':True,'bAirAndDoorEnable':False})
 v['stMainDoorStatus.bLockRequest']=True
 return v
v=initial(0);v['fbPower.Status']=False;v['eMachineState']=2;v['bControlRequest']=h['expression'](permit(old),v);h['execute'](axiscode,v)
assert v['usiState']==10 and v['bBusy'];v['fbPatchFeedManager.stStatus.bBusy']=v['bBusy'];assert h['expression'](lock(old),v)
print('PASS reproduced old Stopping permission powering idle M1 and reasserting door lock')
for mode,axisstate in itertools.product([5,7,6],[0,20,30,40,50]):
 v=initial(axisstate);v['ePreviousMachineState']=mode;v['eMachineState']=2;v['fbPatchFeedManager.stStatus.bBusy']=axisstate not in [0,20]
 assert h['expression'](lock(new),v),'entry handoff must retain lock'
 history=[]
 for scan in range(8):
  v['ePreviousMachineState']=2;v['bControlRequest']=h['expression'](permit(new),v);assert not v['bControlRequest']
  v['stAxis.Axis.Status.Disabled']=v['usiState']==50
  h['execute'](axiscode,v);v['fbPatchFeedManager.stStatus.bBusy']=v['bBusy'];history.append(v['usiState'])
  assert h['expression'](lock(new),v)==bool(v['bBusy'])
  if not v['bBusy']:break
 assert v['usiState']==0,(mode,axisstate,history)
 assert 10 not in history,'Stopping must not initiate power'
print('PASS Ready/Manual/Auto entry handoff, idle/moving/halt/disable axis states, controlled halt retained until idle and no M1 restart')
for state,previous,busy,active,hot in itertools.product(range(9),range(9),[False,True],[False,True],[False,True]):
 v=initial(0);v.update(eMachineState=state,ePreviousMachineState=previous,bAirAndDoorEnable=active,bMainDoorHotLockRequired=hot);v['fbPatchFeedManager.stStatus.bBusy']=busy
 assert h['expression'](lock(new),v)==h['expression'](enable,v)
 if hot:assert h['expression'](lock(new),v)
 if state==3 and not active and not hot:assert not h['expression'](lock(new),v)
print('PASS supervisor/output lock-demand parity across 648 combinations; hot retention and cold Stopped release')
for previous in [0,1,3]:
 v=initial(0);v.update(eMachineState=2,ePreviousMachineState=previous);v['stMainDoorStatus.bLockRequest']=False
 assert not h['expression'](lock(new),v),'PowerUp/recovery must not create a new door lock request'
print('PASS entry hold only retains an existing request; no new PowerUp/recovery locking')
assert c['before']['declaration']==c['proposal']['newDeclaration']
print('PASS method declaration/interface unchanged')
