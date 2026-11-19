"""Run actual saved manual action CASE plus the maintained unlock command."""
from pathlib import Path
import re,json,hashlib,runpy,itertools
import xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1]
p=R/'TwinCAT Patch Press/PatchPress/POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU'
node=E.parse(p).find(".//Method[@Name='Cyclic']");raw=node.findtext('Implementation/ST')
a=raw.index('// Manual UNLOCK is a maintained');b=raw.index('// Support toggle:',a)
hold=re.sub(r'//[^\n]*','',raw[a:b]).replace('fbHeatStake.IsBusy()','bFixtureStationBusy')
execute=runpy.run_path(str(R/'engineering/vision-rotary-marker/st_camera_runner.py'))['execute']
for mode,cycle,busy,old,unlocked,lock in itertools.product([0,1,2,3,4,5,6,7,8],[False,True],[False,True],[False,True],[False,True],[False,True]):
 v={'eMachineState':mode,'E_MachineState.Manual':7,'bHeatStakeManualStakeCycleActive':cycle,
 'bFixtureStationBusy':busy,'bHeatStakeHeadUnlockRequest':old,'bHeatStakeManualHeadUnlocked':unlocked,'bHeatStakeHeadLockRequest':lock}
 execute(hold,v)
 expected=((old or unlocked) and not lock) if mode==7 and not cycle and not busy else old
 assert v['bHeatStakeHeadUnlockRequest']==expected
# Execute the real 1 s manual action and real maintained command each scan.
h=runpy.run_path(str(R/'engineering/el6910/st_function_test.py'));Engine,Parser,Timer=h['Engine'],h['Parser'],h['Timer']
class Ton(Timer):
 def __init__(self):super().__init__();self.pt=0
 def call(self,values):
  self.pt=values.get('PT',self.pt);super().call(dict(values,PT=self.pt))
case=raw[raw.index('CASE usiHeatStakeManualActionStep OF'):raw.index('END_CASE',raw.index('CASE usiHeatStakeManualActionStep OF'))+8]
case_ast=Parser(case).block();hold_ast=Parser(hold).block()
Engine.cache['HEAT_UNLOCK_TEST']=({},[])
e=Engine('HEAT_UNLOCK_TEST',{})
e.v.update({n:False for n in re.findall(r'\b[A-Za-z_]\w*\b',case+hold)})
e.v.update({'eMachineState':7,'E_MachineState':{'Manual':7},'bFixtureStationBusy':False,
 'bHeatStakeManualStakeCycleActive':False,'usiHeatStakeManualActionStep':10,
 'tonHeatStakeManualAction':Ton(),'stInputs':{'bHeatStakeHeadUp':True,'bHeatStakeHeadDown':False,'bStation2SupportRetracted':True},
 'stConfig':{'tHeatStakeHeadMoveTimeout':5000},'stHeatStakeProcessSettings':{'rDownPressureBar':1.0},'GVL_Safety':{'bAirSupplySafe':True}})
def scan():
 e.v['bHeatStakeHeadUnlockRequest']=False;e.v['bHeatStakeHeadLockRequest']=False
 e.execute(case_ast);e.execute(hold_ast)
 return e.v['bHeatStakeHeadUnlockRequest']
for _ in range(100):assert scan()
assert e.v['bHeatStakeManualHeadUnlocked'] and e.v['usiHeatStakeManualActionStep']==0
for _ in range(2000):assert scan(),'Unlock must remain active while waiting in Manual'
e.v['usiHeatStakeManualActionStep']=30;e.v['stInputs']['bHeatStakeHeadUp']=False
for _ in range(100):assert scan()
e.v['stInputs']['bHeatStakeHeadDown']=True;assert scan();assert e.v['usiHeatStakeManualActionStep']==0
for _ in range(500):assert scan(),'Reaching DOWN must not relock'
e.v['usiHeatStakeManualActionStep']=40;e.v['stInputs']['bHeatStakeHeadDown']=False
for _ in range(100):assert scan()
e.v['stInputs']['bHeatStakeHeadUp']=True;assert scan();assert e.v['usiHeatStakeManualActionStep']==0
e.v['usiHeatStakeManualActionStep']=20
assert not scan(),'Lock must drop Unlock on the first Lock scan'
for _ in range(100):assert not scan()
assert not e.v['bHeatStakeManualHeadUnlocked'] and e.v['usiHeatStakeManualActionStep']==0
for _ in range(100):assert not scan()
before=json.loads((B/'before.json').read_text(encoding='utf-8'))
after=json.loads((B/'readback.json').read_text(encoding='utf-8'))
def canonical(text,digest):
 for _ in range(3):
  if hashlib.sha256(text.encode()).hexdigest()==digest:return text
  text=text.encode('cp1252').decode('utf-8')
 raise AssertionError('Snapshot hash mismatch')
assert raw[:a]+raw[b:]==canonical(before['implementation'],before['implementationHash'])
assert hashlib.sha256(raw.encode()).hexdigest()==after['implementationHash']
assert before['declarationHash']==after['declarationHash']
assert 'stOutputsInternal.bHeatStakeHeadUnlock := bHeatStakeHeadUnlockRequest;' in raw
mapping=E.parse(R/'TwinCAT Patch Press/PatchPress/POUs/04_IO_Mapping/PRG_TerminalMapping.TcPOU').findtext(".//Method[@Name='WriteOutputs']/Implementation/ST")
assert 'stFestoModule4_VABX.bCoil3 := GVL_IO.stOutputs.bHeatStakeHeadUnlock;' in mapping
print('PASS all mode/owner/lock combinations; actual Unlock timer, idle/DOWN/UP hold, immediate Lock withdrawal, automatic/initializing/fault noninterference, exact source scope and XAE/disk hash')
