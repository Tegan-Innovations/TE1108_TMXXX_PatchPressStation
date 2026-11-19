"""Execute saved PLC gates and inspect the actual checkbox/server bindings."""
from pathlib import Path
import sys
import json,re,runpy,itertools,hashlib,xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1];P=R/'TwinCAT Patch Press/PatchPress'
machine=E.parse(P/'POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU')
m=machine.find(".//Method[@Name='Cyclic']");raw=m.findtext('Implementation/ST')
commands=E.parse(P/'POUs/00_Application/PRG_HmiCommands.TcPOU').find('.//POU')
cmd=commands.findtext('Implementation/ST')
clean=lambda s:re.sub(r'//[^\n]*','',s)
src=clean(raw)
execute=runpy.run_path(str(R/'engineering/vision-rotary-marker/st_camera_runner.py'))['execute']
run='GVL_EtherCAT.stVSKeyenceCamera.bRunStatus'
def assignment(name):return re.search(r'\b'+re.escape(name)+r'\s*:=.*?;',src,re.S)[0]
permit=assignment('bVisionManualEnableAllowed')
for mode,safe,reject,running in itertools.product([0,1,2,3,4,5,6,7,8],[False,True],[False,True],[False,True]):
 v={'eMachineState':mode,'E_MachineState.Manual':7,'stInputs.stSafety.bSafetyOk':safe,'bRejectChuteStopRequestLatched':reject,run:running}
 execute(permit,v);assert v['bVisionManualEnableAllowed']==(mode==7 and safe and not reject and running)
withdraw=re.search(r'IF NOT '+re.escape(run)+r' THEN.*?END_IF',cmd,re.S)[0]
transfer=re.search(r'GVL_MASTER.stCommand.bVisionManualEnable\s*:=.*?;',cmd,re.S)[0]
enable='GVL_HMI.stCommands.bVisionManualEnable';master='GVL_MASTER.stCommand.bVisionManualEnable'
v={run:False,enable:True}
execute(withdraw,v);execute(transfer,v);assert not v[enable] and not v[master]
v[run]=True;execute(withdraw,v);execute(transfer,v);assert not v[master],'Run recovery must not automatically re-enable'
v[enable]=True;execute(withdraw,v);execute(transfer,v);assert v[master]
for flag in ['bVisionManualSequenceActive','bVisionManualHomeActive']:
 cancel=re.search(r'IF \(eMachineState <> E_MachineState.Manual\)\s+OR NOT bVisionManualEnableAllowed\s+OR NOT stCommand.bVisionManualEnable\s+THEN\s+'+flag+r' := FALSE;\s*END_IF;',src,re.S)
 assert cancel
 v={'eMachineState':7,'E_MachineState.Manual':7,'stCommand.bVisionManualEnable':True,'bVisionManualEnableAllowed':False,flag:True}
 execute(cancel[0],v);assert not v[flag],'Blocked direct command must not retain sequence ownership'
# A rejected one-scan sequence request cannot run later when RUN recovers.
sequence=re.search(r'IF stCommand.bVisionManualRunSequence\s+AND.*?END_IF;',src,re.S)[0]
v={'stCommand.bVisionManualRunSequence':True,'bVisionManualRunSequenceAllowed':False,'bVisionManualSequenceActive':False}
execute(sequence,v);assert not v['bVisionManualSequenceActive']
v.update({'stCommand.bVisionManualRunSequence':False,'bVisionManualRunSequenceAllowed':True})
execute(sequence,v);assert not v['bVisionManualSequenceActive']
camera=assignment('bManualCameraAllowed');assert run in camera
auto=re.search(r'IF NOT '+re.escape(run)+r' THEN\s*bAutoCycleAllowed.*?END_IF',src,re.S)[0]
ready=src.split('\nE_MachineState.ReadyToStart:',1)[1].split('\nE_MachineState.Dwell:',1)[0]
ready=ready.replace('fbIndex.IsFaulted()','bFixtureIndexFault').replace('fbMainDoorLock.IsReadyForAutomatic()','bFixtureDoorReady')
def initial():
 keys=set(re.findall(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',ready))
 v={k:False for k in keys};v.update({'eMachineState':5,'E_MachineState.Manual':7,'E_MachineState.Stopping':2,'E_MachineState.AutoCycle':6,'E_MachineState.Dwell':8,'stCommand.bStart':True,'bAutoCycleAllowed':True,'bFixtureDoorReady':True,'stHeatStakeTemperatureStatus.bIndexTemperatureReady':True})
 return v
for running,commissioning,hot in itertools.product([False,True],repeat=3):
 v=initial();v.update({run:running,'bCoreCommissioningMode':commissioning,'stHeatStakeTemperatureStatus.bIndexTemperatureReady':hot})
 execute(auto,v);execute(ready,v)
 assert v['eMachineState']==((6 if hot else 8) if running else 5)
v=initial();v[run]=False;execute(auto,v);execute(ready,v);assert v['eMachineState']==5
v.update({run:True,'bAutoCycleAllowed':True,'stCommand.bStart':False});execute(auto,v);execute(ready,v);assert v['eMachineState']==5
v['stCommand.bStart']=True;execute(ready,v);assert v['eMachineState']==6
assert 'rtStart(CLK := GVL_MASTER.stInputs.bStartButton OR GVL_HMI.stCommands.bStart);' in cmd
assert 'GVL_MASTER.stCommand.bStart := rtStart.Q;' in cmd
cancel_auto=re.search(r'IF NOT '+re.escape(run)+r' THEN\s*bProcessStartStations.*?END_IF',src,re.S)[0]
v={run:False,'bProcessStartStations':True};execute(cancel_auto,v);assert not v['bProcessStartStations']
# Admission gate remains after the commissioning guard and before the machine CASE.
assert src.index('fbCommissioningGuard.Cyclic(')<src.index(auto)<src.index('\nE_MachineState.ReadyToStart:')
H=R/'TwinCAT Patch Press/PatchPress_HMI'
view=(H/'Contents/Screens/ManualTabs/VisionTab.content').read_text(encoding='utf-8')
checkbox=re.search(r'<div id="TcHmiCheckbox_VisionStationEnable"[^>]*>',view)[0]
symbol='ADS.PLC1.GVL_HMI.stStatus.bVisionManualEnableAllowed'
assert 'data-tchmi-is-enabled="%s%'+symbol+'%/s%"' in checkbox
c=json.loads((H/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
old=json.loads((B/'server.before.json').read_text(encoding='utf-8-sig'))
entry=c['SYMBOLS'].pop(symbol);assert entry['ACCESS']==1 and entry['MAPPING']=='PLC1::GVL_HMI::stStatus::bVisionManualEnableAllowed'
assert entry['SCHEMA']['allOf'][0]['$ref']=='tchmi:general#/definitions/BOOL';assert c==old
# Later machine changes have their own hash readback; retain the original
# exact checkpoint check by default and allow its behavioral cases to be reused.
for key,node in ([] if '--behavior-only' in sys.argv else [('machine',m),('commands',commands)]):
 before=json.loads((B/(key+'.before.json')).read_text(encoding='utf-8'))
 after=json.loads((B/(key+'.readback.json')).read_text(encoding='utf-8'))
 assert before['declarationHash']==after['declarationHash']
 for xpath,hashkey in [('Declaration','declarationHash'),('Implementation/ST','implementationHash')]:
  assert hashlib.sha256(node.findtext(xpath).encode()).hexdigest()==after[hashkey]
 original=before['implementation']
 for _ in range(3):
  if hashlib.sha256(original.encode()).hexdigest()==before['implementationHash']:break
  original=original.encode('cp1252').decode('utf-8')
 assert hashlib.sha256(original.encode()).hexdigest()==before['implementationHash']
 if key=='machine':
  restored=raw.replace('    AND GVL_EtherCAT.stVSKeyenceCamera.bRunStatus\n    AND NOT stCommand.bStop','    AND NOT stCommand.bStop',1)
  restored=restored.replace('    AND NOT bRejectChuteStopRequestLatched\n    AND GVL_EtherCAT.stVSKeyenceCamera.bRunStatus;','    AND NOT bRejectChuteStopRequestLatched;',1)
  restored=restored.replace('\n\t\tOR NOT bVisionManualEnableAllowed','')
 else:
  restored=cmd[cmd.index('GVL_HMI.stCommands.bVisionSupportExtendRequest :='):]
 assert restored==original,'Unexpected changes outside the intended manual RUN gates'
print('PASS manual RUN admission, enable withdrawal/fresh reselect, owner/request cancellation, automatic admission including commissioning/Dwell, no deferred Start and mapped native checkbox; '+('behavior only (historical hashes skipped)' if '--behavior-only' in sys.argv else 'XAE/disk hashes verified'))
