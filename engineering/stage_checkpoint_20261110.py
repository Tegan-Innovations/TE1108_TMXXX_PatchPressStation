"""Stage only reviewed feeder/door changes, preserving unrelated working edits."""
from pathlib import Path
import subprocess,json,copy
root=Path(__file__).resolve().parents[1]
def git(*args,**kwargs):return subprocess.check_output(['git',*args],cwd=root,**kwargs)
assert not git('diff','--cached','--name-only').strip(),'Existing staged work must be preserved'
plc='TwinCAT Patch Press/PatchPress/'
hmi='TwinCAT Patch Press/PatchPress_HMI/'
files=[plc+p for p in ['DUTs/02_Components/Motion/ST_PatchFeedSettings.TcDUT','DUTs/03_Stations/PatchDispense/ST_PatchProcessSettings.TcDUT','POUs/00_Application/PRG_StationProcessSettings.TcPOU','POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU','POUs/03_Stations/PatchDispense/FB_PatchDispenseStation.TcPOU']]
files+=[hmi+'Contents/Screens/Settings/settings_PatchDispense.content','engineering/checkpoint-20261110.md','engineering/stage_checkpoint_20261110.py','engineering/station-settings/check_settings.py']
evidence={'patch-feeder-speed-delay':['HANDOVER.md'],'patch-left-only':['HANDOVER.md'],'patch-m1-stop-delay':['HANDOVER.md','changes.json','check_delay.py','mapping-diagnosis.md','read_hmi.mjs','prepare_mapping_repair.mjs','settings_PatchDispense.content.before','TcHmiSrv.Config.default.json.before'],'door-reset-lock-request':['HANDOVER.md','change.json','check_patch.py','verification.json']}
for folder,names in evidence.items():files.extend('engineering/'+folder+'/'+n for n in names)
config=hmi+'Server/TcHmiSrv/TcHmiSrv.Config.default.json'
before=json.loads(git('show','HEAD:'+config).decode('utf-8-sig'))
working=json.loads((root/config).read_text(encoding='utf-8-sig'))
for kind in ['Edit','Applied']:
 old=f'ADS.PLC1.GVL_HMI.stPatchProcess{kind}.udiAirBlowDelayMs';new=old.replace('udiAirBlowDelayMs','udiDriveStopDelayMs')
 before['SYMBOLS'][new]=copy.deepcopy(working['SYMBOLS'][new])
 for group in before['USERGROUPS'].values():group['SYMBOLS'][new]=group['SYMBOLS'][old]
schema=before['DEFINITIONS']['ADS']['ADS-PLC1.ST_PatchProcessSettings']
schema['properties']['udiDriveStopDelayMs']={'allOf':[{'$ref':'tchmi:general#/definitions/UDINT'}]}
if 'udiDriveStopDelayMs' not in schema['required']:schema['required'].append('udiDriveStopDelayMs')
git('add','--',*files)
data=(json.dumps(before,indent=4,ensure_ascii=False)+'\n').encode('utf-8')
blob=git('hash-object','-w','--stdin',input=data).decode().strip()
git('update-index','--cacheinfo','100644',blob,config)
subprocess.run(['git','diff','--cached','--check','--',*files[:7]],cwd=root,check=True)
print('Staged explicit feature files and HMI configuration delta; unrelated files untouched')
