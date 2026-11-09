from pathlib import Path
import json,re,runpy,hashlib,itertools,xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1]
p=R/'TwinCAT Patch Press/PatchPress/POUs/00_Application/PRG_HmiStatus.TcPOU'
code=E.parse(p).findtext('.//POU/Implementation/ST')
a=code.index('// ReadyToStart indication');b=code.index('GVL_HMI.stStatus.stHeatStake :=',a)
block=re.sub(r'//[^\n]*','',code[a:b])
execute=runpy.run_path(str(R/'engineering/vision-rotary-marker/st_camera_runner.py'))['execute']
keys=set(re.findall(r'GVL_\w+(?:\.\w+)+',block));out='GVL_HMI.stStatus.stPatchDispense.bReady'
def state():
 v={k:False for k in keys};v.update({'GVL_MASTER.stStatus.eMachineState':5,'E_MachineState.ReadyToStart':5,
 'GVL_MASTER.stStatus.stPatchDispense.eState':20,'E_PatchStationState.Ready':20,
 'GVL_Motion.AxisDriveMotor.Axis.NcToPlc.AxisId':1,
 'GVL_MASTER.stStatus.stPatchDispense.bCommissioned':True,'GVL_MASTER.stStatus.stPatchDispense.bHome':True,
 'GVL_MASTER.stInputs.stSafety.bSafetyOk':True,'GVL_MASTER.stInputs.stSafety.bMotionSafetyPermitted':True,
 'GVL_MASTER.stInputs.bMainDoorClosed':True,'GVL_Safety.bAirSupplySafe':True,
 'GVL_Motion.AxisDriveMotor.Axis.Status.Disabled':True})
 return v
base=state();execute(block,base);assert base[out], 'Idle disabled M1 must permit standby indication'
for standstill,disabled in itertools.product([False,True],repeat=2):
 v=state();v['GVL_Motion.AxisDriveMotor.bStandstill']=standstill;v['GVL_Motion.AxisDriveMotor.Axis.Status.Disabled']=disabled
 execute(block,v);assert v[out]==(standstill or disabled)
for key in keys-{out,'GVL_MASTER.stStatus.eMachineState','GVL_MASTER.stStatus.stPatchDispense.eState','GVL_Motion.AxisDriveMotor.Axis.NcToPlc.AxisId','GVL_Motion.AxisDriveMotor.bStandstill'}:
 v=state();v[key]=not v[key];execute(block,v);assert not v[out],key
for axis in [0,1,2]:
 for stage in [0,10,20,30,40,100]:
  v=state();v['GVL_Motion.AxisDriveMotor.Axis.NcToPlc.AxisId']=axis;v['GVL_MASTER.stStatus.stPatchDispense.eState']=stage
  execute(block,v);assert v[out]==(axis!=0 and stage==20)
for mode,old in itertools.product([0,1,2,3,4,6,7,8,9],[False,True]):
 v=state();v['GVL_MASTER.stStatus.eMachineState']=mode;v[out]=old
 execute(block,v);assert v[out]==old
 # Stop/reset/fault/recovery machine modes do not invoke the standby projection.
assert set(re.findall(r'(GVL_\w+(?:\.\w+)+)\s*:=',block))=={out},'Only HMI Ready may be assigned'
before=json.loads((B/'before.json').read_text(encoding='utf-8'));original=before['implementation']
for _ in range(3):
 if hashlib.sha256(original.encode()).hexdigest()==before['implementationHash']:break
 original=original.encode('cp1252').decode('utf-8')
assert hashlib.sha256(original.encode()).hexdigest()==before['implementationHash']
assert code[:a]+code[b:]==original,'Change escaped the standby indication block'
snap=json.loads((B/'readback.json').read_text(encoding='utf-8'))
assert hashlib.sha256(code.encode()).hexdigest()==snap['implementationHash']
fixture=R/'engineering/hmi-io/verified-sections.json';entries=json.loads(fixture.read_text(encoding='utf-8'))
for i,e in enumerate(entries):
 if e['path']==snap['path']:entries[i]=snap
fixture.write_text(json.dumps(entries,indent=2),encoding='utf-8')
print('PASS disabled/standstill standby readiness, every missing prerequisite, faults/busy/motion/axis availability, non-ReadyToStart preservation, output scope and exact XAE/disk change')
