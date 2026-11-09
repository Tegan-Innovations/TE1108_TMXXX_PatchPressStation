"""Execute the saved final valve arbitration and actual output mapping, offline."""
from pathlib import Path
import re,json,hashlib,runpy,itertools,xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1];P=R/'TwinCAT Patch Press/PatchPress'
machine=E.parse(P/'POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU')
root=machine.find('.//POU');cyclic=root.find("Method[@Name='Cyclic']");raw=cyclic.findtext('Implementation/ST')
a=raw.index('// Single-solenoid head valve:');b=raw.index('stOutputs := stOutputsInternal;',a)
block=re.sub(r'//[^\n]*','',raw[a:b])
execute=runpy.run_path(str(R/'engineering/vision-rotary-marker/st_camera_runner.py'))['execute']
def state():
 return {'stInputs.stSafety.bSafetyOk':True,'stInputs.stSafety.bProcessSafetyPermitted':True,
 'GVL_Safety.bAirSupplySafe':True,'eMachineState':6,'ePreviousMachineState':6,
 'E_MachineState.Fault':1,'E_MachineState.Initialising':4,'E_MachineState.ReadyToStart':5,
 'stInputs.bHeatStakeHeadUp':False,'stInputs.bHeatStakeHeadDown':True,
 'bHeatStakeHeadUpRecoveryLatched':False,'bHeatStakeHeadDownHeld':False,
 'bHeatStakeHeadUpRequest':False,'bHeatStakeHeadDownRequest':False}
def scan(v):
 execute(block,v)
 assert v['stOutputsInternal.bHeatStakeHeadUp']!=v['stOutputsInternal.bHeatStakeHeadDown']
 return v['stOutputsInternal.bHeatStakeHeadUp']
# Every combination of safety/air/fault conditions forces and retains UP.
for safety,process,air,fault in itertools.product([False,True],repeat=4):
 v=state();v.update({'stInputs.stSafety.bSafetyOk':safety,'stInputs.stSafety.bProcessSafetyPermitted':process,
 'GVL_Safety.bAirSupplySafe':air,'eMachineState':1 if fault else 6,'bHeatStakeHeadDownHeld':True,'bHeatStakeHeadDownRequest':True})
 up=scan(v);assert up==(not safety or not process or not air or fault)
 if up:
  v.update({'stInputs.stSafety.bSafetyOk':True,'stInputs.stSafety.bProcessSafetyPermitted':True,'GVL_Safety.bAirSupplySafe':True,'eMachineState':3,'stCommand.bReset':True})
  assert scan(v) and v['bHeatStakeHeadUpRecoveryLatched'],'Reset/safety restore alone must not re-arm DOWN'
# Continuous DOWN at the sensor and through request gaps (including dwell entry).
v=state();v['bHeatStakeHeadDownRequest']=True;assert not scan(v)
v['bHeatStakeHeadDownRequest']=False
for up,down in itertools.product([False,True],repeat=2):
 v.update({'stInputs.bHeatStakeHeadUp':up,'stInputs.bHeatStakeHeadDown':down})
 for _ in range(1000):assert not scan(v),'Position feedback must not pulse the command'
v['bHeatStakeHeadUpRequest']=True;assert scan(v)
v['bHeatStakeHeadUpRequest']=False
for _ in range(1000):assert scan(v),'UP remains active after its sensor and request end'
v.update({'bHeatStakeHeadUpRequest':True,'bHeatStakeHeadDownRequest':True});assert scan(v),'UP has priority'
# Startup and failed/incomplete initialization cannot allow descent.
for previous,mode,up,down in itertools.product([3,4,5,6,7],[3,4,5,6,7],[False,True],[False,True]):
 v=state();v.update({'bHeatStakeHeadUpRecoveryLatched':True,'ePreviousMachineState':previous,
 'eMachineState':mode,'stInputs.bHeatStakeHeadUp':up,'stInputs.bHeatStakeHeadDown':down})
 scan(v);assert v['bHeatStakeHeadUpRecoveryLatched']!= (previous==4 and mode==5 and up and not down)
# Fault during descent -> retained UP -> completed initialization -> fresh DOWN.
v=state();v.update({'bHeatStakeHeadDownHeld':True,'eMachineState':1});assert scan(v)
v.update({'eMachineState':4,'ePreviousMachineState':3,'stInputs.bHeatStakeHeadUp':True,'stInputs.bHeatStakeHeadDown':False});assert scan(v)
v.update({'eMachineState':5,'ePreviousMachineState':4});assert scan(v) and not v['bHeatStakeHeadUpRecoveryLatched']
v.update({'eMachineState':7,'ePreviousMachineState':5,'bHeatStakeHeadDownRequest':True});assert not scan(v)
assert b<raw.index('ePreviousMachineState := eMachineState;')
decl=root.findtext('Declaration')
assert 'bHeatStakeHeadUpRecoveryLatched : BOOL := TRUE;' in decl
assert 'bHeatStakeHeadDownHeld : BOOL := FALSE;' in decl
mapping=E.parse(P/'POUs/04_IO_Mapping/PRG_TerminalMapping.TcPOU').find(".//Method[@Name='WriteOutputs']")
mapcode=mapping.findtext('Implementation/ST')
assert 'stTerm9_EL2809.iEL2809_Ch7 := GVL_IO.stOutputs.bHeatStakeHeadUp;' in mapcode
assert 'stFestoModule4_VABX.bCoil4 := FALSE;' in mapcode
assert 'stFestoModule4_VABX.bCoil5 := TRUE;' in mapcode
assert 'stFestoModule4_VABX.bCoil3 := GVL_IO.stOutputs.bHeatStakeHeadUnlock;' in mapcode
for signal in ['stTerm9_EL2809.iEL2809_Ch7','stFestoModule4_VABX.bCoil4','stFestoModule4_VABX.bCoil5']:
 assert len(re.findall(re.escape(signal)+r'\s*:=',mapcode))==1
for key,node in [('machine',root),('cyclic',cyclic),('mapping',mapping)]:
 snap=json.loads((B/(key+'.readback.json')).read_text(encoding='utf-8'))
 for xpath,hashkey in [('Declaration','declarationHash'),('Implementation/ST','implementationHash')]:
  assert hashlib.sha256((node.findtext(xpath) or '').encode()).hexdigest()==snap[hashkey]
 before=json.loads((B/(key+'.before.json')).read_text(encoding='utf-8'))
 expected=json.loads((B/(key+'.change.json')).read_text(encoding='utf-8'))
 def canonical(s,digest):
  for _ in range(3):
   if hashlib.sha256(s.encode()).hexdigest()==digest:return s
   s=s.encode('cp1252').decode('utf-8')
  raise AssertionError('Snapshot encoding/hash mismatch')
 canonical(before['implementation'],before['implementationHash'])
 assert canonical(snap['implementation'],snap['implementationHash'])==(node.findtext('Implementation/ST') or '')
 assert canonical(expected['newImplementation'],snap['implementationHash'])==(node.findtext('Implementation/ST') or '')
 assert canonical(expected['newDeclaration'],snap['declarationHash'])==node.findtext('Declaration')
H=R/'TwinCAT Patch Press/PatchPress_HMI/Contents/Hardware'
for name,replacements in {'T09_EL2809.content':{'CH07 spare':'CH07 - Heat Stake Valve (1=Up / 0=Down)'},'Festo_Module4.content':{'CH05 - Coil 4 - Heat Stake Head Down':'CH05 - Coil 4 - Retired (OFF)','CH06 - Coil 5 - Heat Stake Head Up':'CH06 - Coil 5 - Head Pilot Supply (ON)'}}.items():
 before=(B/(name+'.before')).read_text(encoding='utf-8-sig')
 for old,new in replacements.items():before=before.replace(old,new)
 assert (H/name).read_text(encoding='utf-8-sig')==before
config=E.parse(R/'TwinCAT Patch Press/TwinCAT Patch Press.tsproj')
assert any(l.get('VarA')=='PlcTask Outputs^GVL_EtherCAT.stTerm9_EL2809.iEL2809_Ch7' and l.get('VarB')=='Channel 7^Output' for l in config.iter('Link'))
print('PASS continuous UP/DOWN through sensor arrival and request gaps, UP priority, safety/air/fault retention, Reset inhibition, completed HOME rearm, exact mapping, unchanged Unlock/HMI bindings and XAE/disk hashes')
