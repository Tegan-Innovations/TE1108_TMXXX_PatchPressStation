"""Execute saved settings ST with scripted persistence feedback; no runtime access."""
from pathlib import Path
import re,json,copy,runpy,xml.etree.ElementTree as E,html
root=Path(__file__).resolve().parents[2];plc=root/'TwinCAT Patch Press/PatchPress';base=Path(__file__).parent
h=runpy.run_path(str(root/'engineering/patch-feeding/implementation/st_branch_runner.py'))
fields={}
for label,path in [('Patch','DUTs/03_Stations/PatchDispense/ST_PatchProcessSettings.TcDUT'),('Vision','DUTs/03_Stations/Vision/ST_CameraProcessSettings.TcDUT')]:
 d=E.parse(plc/path).findtext('.//Declaration')
 fields[label]={n:float(v) if t=='LREAL' else int(v) for n,t,v in re.findall(r'(\w+)\s*:\s*(LREAL|UDINT)\s*:=\s*([\d.]+)',d)}
raw=E.parse(plc/'POUs/00_Application/PRG_StationProcessSettings.TcPOU').findtext('.//Implementation/ST')
code=re.sub(r'//[^\n]*','',raw)
for label,fs in fields.items():
 candidates=[f'stDefault{label}',f'GVL_Persistent.st{label}ProcessSettings',f'GVL_HMI.st{label}ProcessEdit',f'GVL_HMI.st{label}ProcessApplied']
 for lhs in candidates:
  for rhs in candidates:
   code=code.replace(lhs+' := '+rhs+';', '\n'.join(lhs+'.'+f+' := '+rhs+'.'+f+';' for f in fs))
before,after=re.split(r'fbWritePersistentData\([^;]*\);',code)
def initial():
 v={k:0 for k in re.findall(h['var'],before+after)}
 for n,x in [('Stopped',3),('ReadyToStart',5)]:v['E_MachineState.'+n]=x
 v['GVL_MASTER.stStatus.eMachineState']=3
 for label,fs in fields.items():
  for f,x in fs.items():v[f'stDefault{label}.{f}']=x;v[f'GVL_Persistent.st{label}ProcessSettings.{f}']=x
 return v
def scan(v,fb_busy=False,fb_error=False,**updates):
 v.update(updates);h['execute'](before,v)
 v['fbWritePersistentData.BUSY']=fb_busy;v['fbWritePersistentData.ERR']=fb_error;v['fbWritePersistentData.ERRID']=1793 if fb_error else 0
 h['execute'](after,v);return v
v=initial();scan(v)
assert v['GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity']==30
assert v['GVL_Motion.stPatchFeedSettings.lrPatchFeedRollVelocity']==10
for state in range(8):
 v=initial();scan(v);scan(v,**{'GVL_MASTER.stStatus.eMachineState':state,'GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity':20,'GVL_HMI.bPatchSettingsApply':True})
 assert v['GVL_HMI.bStationSettingsAllowed']==(state in [3,5])
 assert v['GVL_Persistent.stPatchProcessSettings.lrDriveMotorVelocity']==(20 if state in [3,5] else 30)
 assert not v['GVL_HMI.bPatchSettingsApply']
print('PASS all machine modes: only Stopped/Ready accept; commands consumed without a queued apply')
for bit in ['GVL_MASTER.stStatus.stPatchDispense.bBusy','GVL_MASTER.stStatus.stHeatStake.bBusy','GVL_MASTER.stStatus.stVision.bBusy','GVL_Motion.stPatchFeedStatus.bBusy','GVL_Motion.stPatchFeedStatus.bDriveBusy','GVL_Motion.AxisDriveMotor.bMoving','GVL_Motion.AxisPatchFeedRollMotor.bMoving','GVL_Motion.AxisWasteRollMotor.bMoving']:
 v=initial();scan(v);scan(v,**{bit:True,'GVL_HMI.bPatchSettingsApply':True,'GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity':20})
 assert v['GVL_Persistent.stPatchProcessSettings.lrDriveMotorVelocity']==30,bit
for label,bounds in [('Patch',[(0.1,30),(0.1,10),(0.1,50),(100,15000),(0,2000)]),('Vision',[(0,1000),(1000,3000)])]:
 for (field,default),(lo,hi) in zip(fields[label].items(),bounds):
  for value in [lo,hi,lo-1,hi+1]+([float('nan')] if field.startswith('lr') else []):
   v=initial();scan(v);scan(v,**{f'GVL_HMI.st{label}ProcessEdit.{field}':value,f'GVL_HMI.b{label}SettingsApply':True})
   assert v[f'GVL_Persistent.st{label}ProcessSettings.{field}']==(value if lo<=value<=hi else default),(field,value)
print('PASS every field boundary, invalid values and NaN; movement/busy gates')
v=initial();scan(v)
scan(v,**{'GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity':20,'GVL_HMI.stPatchProcessEdit.udiReleaseMs':0,'GVL_HMI.bPatchSettingsApply':True})
assert v['GVL_Persistent.stPatchProcessSettings.lrDriveMotorVelocity']==30,'Reject entire transaction'
scan(v,**{'GVL_HMI.bPatchSettingsCancel':True,'GVL_HMI.bPatchSettingsApply':True})
assert v['GVL_HMI.stPatchProcessEdit.udiReleaseMs']==5000 and not v['GVL_HMI.bPatchSettingsCancel']
scan(v,fb_busy=True,**{'GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity':20,'GVL_HMI.bPatchSettingsApply':True})
assert v['bWriteStart'] and v['GVL_HMI.bStationSettingsSaving']
scan(v,fb_busy=True,**{'GVL_HMI.stVisionProcessEdit.udiMovingTriggerDelayMs':200,'GVL_HMI.bVisionSettingsApply':True})
assert v['GVL_Persistent.stVisionProcessSettings.udiMovingTriggerDelayMs']==100,'No accept while saving'
scan(v)
assert v['GVL_HMI.sPatchSettingsMessage']=='Applied and saved'
scan(v,fb_busy=True,**{'GVL_HMI.bVisionSettingsApply':True});scan(v,fb_error=True)
assert v['GVL_HMI.bStationSettingsSaveError'] and 'SAVE FAILED' in v['GVL_HMI.sVisionSettingsMessage']
assert v['GVL_HMI.stVisionProcessApplied.udiMovingTriggerDelayMs']==200,'Applied remains explicit on save failure'
scan(v,fb_busy=True,**{'GVL_HMI.bVisionSettingsApply':True});scan(v)
assert not v['GVL_HMI.bStationSettingsSaveError'] and v['GVL_HMI.sVisionSettingsMessage']=='Applied and saved'
restarted=initial();restarted.update({k:x for k,x in v.items() if k.startswith('GVL_Persistent.')});scan(restarted)
assert restarted['GVL_HMI.stVisionProcessEdit.udiMovingTriggerDelayMs']==200
print('PASS atomic reject, Cancel priority, repeated Apply, save busy/success/error/retry and restart hydration')
v=initial();v['GVL_Persistent.stPatchProcessSettings.lrDriveMotorVelocity']=100;scan(v)
assert v['GVL_HMI.stPatchProcessEdit.lrDriveMotorVelocity']==30 and 'defaults loaded' in v['GVL_HMI.sPatchSettingsMessage']
print('PASS invalid retained settings load bounded defaults with explicit message')

hmi=root/'TwinCAT Patch Press/PatchPress_HMI';config=json.loads((hmi/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
ids=[];used=set()
for label,name in [('Patch','settings_PatchDispense'),('Vision','settings_VisionStation')]:
 s=(hmi/f'Contents/Screens/Settings/{name}.content').read_text(encoding='utf-8-sig')
 ids+=re.findall(r'\bid="([^"]+)"',s)
 assert 'JavaScript' not in s and '<script ' in s
 for value in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',s,re.S):
  events=json.loads(value)
  if isinstance(events,list) and events and events[0]['actions'][-1]['symbolExpression'].endswith('b'+label+'SettingsApply%/s%'):
   actions=events[0]['actions'];assert len(actions)==len(fields[label])+1
   for a in actions[:-1]:assert a['asyncWait'] and a['value']['objectType']=='Symbol' and a['value']['symbolExpression'].endswith('::Value%/ctrl%')
 for field in fields[label]:
  edit=f'ADS.PLC1.GVL_HMI.st{label}ProcessEdit.{field}'
  applied=f'ADS.PLC1.GVL_HMI.st{label}ProcessApplied.{field}'
  assert edit+'|BindingMode=TwoWay' in s and applied in s
 for binding in re.findall(r'%s%(ADS[^%|]+)(?:\|[^%]+)?%/s%',s):used.add(html.unescape(binding))
 for kind in ['Apply','Cancel']:assert f'b{label}Settings{kind}' in s
assert len(ids)==len(set(ids))
for key in used:
 assert key in config['SYMBOLS'],key
 assert config['SYMBOLS'][key]['MAPPING']=='PLC1::'+key.removeprefix('ADS.PLC1.').replace('.','::')
 assert config['USERGROUPS']['Operator']['SYMBOLS'][key]==1
for label in ['Patch','Vision']:
 for kind in ['Apply','Cancel']:
  key=f'ADS.PLC1.GVL_HMI.b{label}Settings{kind}'
  assert config['USERGROUPS']['Engineer']['SYMBOLS'][key]==3
nav=(hmi/'Contents/Screens/Settings.content').read_text(encoding='utf-8-sig');assert 'Contents/Screens/Settings/settings_VisionStation.content' in nav
project=E.parse(hmi/'PatchPress_HMI.hmiproj');assert any(x.get('Include','').endswith('settings_VisionStation.content') for x in project.iter())
main=E.parse(plc/'POUs/MAIN.TcPOU').findtext('.//ST');assert main.index('PRG_StationProcessSettings();')<main.index('PRG_Main();')
print('PASS native bindings, unique control IDs, exact ADS mappings, role permissions, navigation and scan order')
