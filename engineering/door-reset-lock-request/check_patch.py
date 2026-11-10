"""Offline execution of saved door supervisor and machine output expressions."""
from pathlib import Path
import json,re,runpy,xml.etree.ElementTree as E,itertools
root=Path(__file__).resolve().parents[2];base=Path(__file__).parent
plc=root/'TwinCAT Patch Press/PatchPress'
change=json.loads((base/'change.json').read_text())
machine=E.parse(plc/'POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU').find(".//Method[@Name='Cyclic']")
saved=machine.findtext('Implementation/ST')
normalize=lambda s:s.replace('\u00c3\u201a\u00c2\u00b0','\u00b0').replace('\u00c2\u00b0','\u00b0')
assert normalize(saved.strip())==normalize(change['newImplementation'].strip())
assert machine.findtext('Declaration').strip()==change['declaration'].strip()
block=change['movedBlock']
added='// Use the state after the machine CASE transitions in this scan.\n// Stopped -> Initialising must not drop an existing hot-door lock request.\n'
assert saved.count(block)==1
assert normalize(saved.replace(added+block+'\n',''))==normalize(change['implementation'].replace(block,''))
assert saved.index(block)>saved.index('CASE eMachineState OF')
assert saved.index(block)>saved.index('stIndexStatus := fbIndex.GetStatus();')
assert saved.index(block)<saved.index('fbMainDoorLock.Cyclic(')
assert saved.index(block)<saved.index('stOutputsInternal.bMainDoorLockRequest :=')
print('PASS exact single-block relocation; declaration and all other implementation text preserved')

h=runpy.run_path(str(root/'engineering/patch-feeding/implementation/st_branch_runner.py'))
test=root/'engineering/patch-dispense-m1/check_sequence.py'
ctx={'__file__':str(test)};source=test.read_text();exec(source[:source.index('for initially_present')],ctx)
prepare=ctx['prepare']
door=E.parse(plc/'POUs/02_Components/Door/FB_MainDoorLock.TcPOU')
door_raw=door.find(".//Method[@Name='Cyclic']").findtext('Implementation/ST')
door_code=prepare(door_raw)
init_code=prepare(door.find(".//Method[@Name='Initialise']").findtext('Implementation/ST'))
enums={}
for name in ['E_MainDoorLockState','E_MainDoorLockFault']:
 text=E.parse(plc/f'DUTs/01_Core/{name}.TcDUT').findtext('.//Declaration')
 enums.update({name+'.'+n:int(v) for n,v in re.findall(r'(\w+)\s*:=\s*(\d+)',text)})
states={'PowerUp':0,'Fault':1,'Stopping':2,'Stopped':3,'Initialising':4,'ReadyToStart':5,'AutoCycle':6,'Manual':7,'Dwell':8}
enums.update({'E_MachineState.'+k:v for k,v in states.items()})
for name,value in enums.items():
 door_raw=door_raw.replace(name+':',str(value)+':')
door_code=prepare(door_raw)
def initial():
 v={k:0 for k in re.findall(h['var'],door_code+init_code+block)};v.update(enums)
 v.update(eState=30,bDoorClosed=True,bDoorLocked=True,bDoorUnsafe=False,bProcessSafePosition=True)
 v['stStatusInternal.bDoorLocked']=True
 return v
def enable(v,state):
 v['eMachineState']=state;h['execute'](re.sub(r'//[^\n]*','',block),v);return v['bAirAndDoorEnable']
for previous,current in itertools.product(states.values(),repeat=2):
 v=initial();enable(v,previous);result=enable(v,current)
 assert result==(current in [4,5,6,7,8])
print('PASS enable expression for every before/after machine-state pair; same active-state policy')
output=re.search(r'stOutputsInternal.bMainDoorLockRequest :=(.*?);',saved,re.S).group(0)
stopped=change['implementation'].split('E_MachineState.Stopped:\n',1)[1].split('E_MachineState.Initialising:\n',1)[0]
stopped=re.sub(r'//[^\n]*','',stopped)
stopped=re.sub(r'ton\w+\([^;]*\);','',stopped)
stopped=stopped.replace('fbMainDoorLock.Initialise();','')
def hot_reset(fixed):
 v=initial()
 v.update({k:0 for k in re.findall(h['var'],stopped) if k not in v})
 v.update({'stCommand.bReset':True,'stInputs.stSafety.bSafetyOk':True,'stInputs.bMainDoorClosed':True,
           'bAirSupplyLatched':True,'eMachineState':3,'bMainDoorHotLockRequired':True})
 enable(v,3)
 h['execute'](stopped,v)
 assert v['eMachineState']==4
 h['execute'](init_code,v)
 if fixed:enable(v,4)
 # Hot-lock requirement only applies while Stopped, as in actual saved code.
 v['bMainDoorHotLockRequired']=False
 h['execute'](output,v)
 first=v['stOutputsInternal.bMainDoorLockRequest']
 # Illustrative feedback model: lock follows previous output. No equipment claim.
 v.update(bDoorLocked=first,bEnableAutomatic=enable(v,4),bResetRequest=False)
 h['execute'](door_code,v)
 return first,v
first,old=hot_reset(False)
assert not first and old['eFault']==40 and old['eState']==999
first,new=hot_reset(True)
assert first and new['eFault']==0 and new['eState']==30
print('PASS original 10 ms lock-request gap reproduced; corrected reset maintains hot-lock request and avoids induced mismatch in scripted feedback model')
for closed,locked,unsafe in itertools.product([False,True],repeat=3):
 v=initial();v.update(bEnableAutomatic=True,bDoorClosed=closed,bDoorLocked=locked,bDoorUnsafe=unsafe)
 h['execute'](door_code,v)
 assert (v['eState']==999)==(unsafe or not closed or not locked)
 assert (v['eFault']==40)==(unsafe or not closed or not locked)
print('PASS all Locked-state feedback combinations: real closed/locked loss and unsafe still fault immediately')
v=initial();v.update(eState=10,bDoorLocked=False,bEnableAutomatic=True)
h['execute'](door_code,v);assert v['eState']==20 and v['eFault']==0
v['bDoorLocked']=True;h['execute'](door_code,v);assert v['eState']==30
v=initial();v.update(bEnableAutomatic=False,bStopRequest=True)
h['execute'](door_code,v);assert v['eState']==40
v['bDoorLocked']=False;h['execute'](door_code,v);assert v['eState']==10
for state,code in [(20,10),(40,20)]:
 v=initial();v.update(eState=state,bDoorLocked=(state==40));v['tonTransition.Q']=True
 h['execute'](door_code,v);assert v['eState']==999 and v['eFault']==code
print('PASS cold lock acquisition, stopped unlock and both timeout faults preserved')
