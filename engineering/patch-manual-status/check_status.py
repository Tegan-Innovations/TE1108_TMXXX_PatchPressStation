from pathlib import Path
import json,re,itertools,runpy,hashlib,xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1];H=R/'TwinCAT Patch Press/PatchPress_HMI'
s=(H/'Contents/Screens/ManualTabs/PatchTab.content').read_text(encoding='utf-8')
old=(B/'PatchTab.before.content').read_text(encoding='utf-8')
c=json.loads((H/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
before=json.loads((B/'server.before.json').read_text(encoding='utf-8-sig'))
def strip_leds(text):return re.sub(r'<div id="TcHmiHtmlHost_Patch[^"]+"[^>]*>.*?</div>','',text,flags=re.S)
assert strip_leds(s)==strip_leds(old),'Non-LED controls changed'
leds=re.findall(r'<div id="(TcHmiHtmlHost_Patch[^"]+)"[^>]*>(.*?)</div>',s,re.S)
assert len(leds)==11
for name,block in leds:
 events=json.loads(re.search(r'data-tchmi-trigger"[^>]*>(.*?)</script>',block,re.S)[1])
 assert any('.onAttached' in e['event'] for e in events),name
 for ref in set(re.findall(r'%s%(ADS\.[^%|]+)',block)):assert ref in c['SYMBOLS'],(name,ref)
 assert '"else"' in block and 'BackgroundColor' in block
air='ADS.PLC1.GVL_MASTER.stOutputs.bPatchDispenserAir'
assert c['SYMBOLS'][air]['ACCESS']==1
assert c['SYMBOLS'][air]['MAPPING']=='PLC1::GVL_MASTER::stOutputs::bPatchDispenserAir'
c['SYMBOLS'].pop(air);assert c==before,'Unrelated server config changed'
for script in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',s,re.S):json.loads(script)
p=R/'TwinCAT Patch Press/PatchPress/POUs/00_Application/PRG_HmiStatus.TcPOU'
code=E.parse(p).findtext('.//POU/Implementation/ST')
start=code.index('// Display aggregate Patch faults');end=code.index('GVL_HMI.stStatus.stHeatStake :=',start)
block=re.sub(r'//[^\n]*','',code[start:end])
execute=runpy.run_path(str(R/'engineering/vision-rotary-marker/st_camera_runner.py'))['execute']
keys=sorted(set(re.findall(r'GVL_\w+(?:\.\w+)+',block)))
inputs=[k for k in keys if not k.startswith('GVL_HMI.stStatus.')]
assert len(inputs)==14,len(inputs)
for bits in itertools.product([False,True],repeat=len(inputs)):
 v=dict(zip(inputs,bits));v.update({k:False for k in keys if k not in v})
 v['GVL_MASTER.stStatus.eMachineState']=7;v['E_MachineState.Manual']=7
 execute(block,v)
 ready=v['GVL_HMI.stStatus.stPatchDispense.bReady'];busy=v['GVL_HMI.stStatus.stPatchDispense.bBusy'];fault=v['GVL_HMI.stStatus.stPatchDispense.bFault']
 assert fault==(v['GVL_MASTER.stStatus.stPatchDispense.bFault'] or v['GVL_Motion.stPatchFeedStatus.bFault'] or v['GVL_Motion.AxisDriveMotor.bError'])
 assert not(ready and(busy or fault))
 assert busy==(v['GVL_MASTER.stStatus.stPatchDispense.bBusy'] or not v['GVL_MASTER.stStatus.stPatchDispense.bHome'] or any(v[k] for k in inputs if k.endswith(('.bBusy','.bMoving','.bStation1SupportExtend','.bStation1SupportRetract','.bPatchVerticalDown','.bPatchDispenserAir'))))
 assert ready==(v['GVL_MASTER.stStatus.stPatchDispense.bReady'] and v['GVL_MASTER.stStatus.stPatchDispense.bHome'] and v['GVL_HMI.stCommands.bPatchManualEnable'] and not busy and not fault)
 for mode in [0,1,2,3,4,5,6]:
  v['GVL_MASTER.stStatus.eMachineState']=mode;v['GVL_HMI.stStatus.stPatchDispense.bReady']=True;v['GVL_HMI.stStatus.stPatchDispense.bBusy']=False
  execute(block,v);assert v['GVL_HMI.stStatus.stPatchDispense.bReady'] and not v['GVL_HMI.stStatus.stPatchDispense.bBusy']
snap=json.loads((B/'readback.json').read_text(encoding='utf-8'))
assert hashlib.sha256(code.encode()).hexdigest()==snap['implementationHash']
fixture=R/'engineering/hmi-io/verified-sections.json';entries=json.loads(fixture.read_text(encoding='utf-8'))
for i,e in enumerate(entries):
 if e['path']==snap['path']:entries[i]=snap
fixture.write_text(json.dumps(entries,indent=2),encoding='utf-8')
print('PASS 11 native LEDs, symbol maps, initial refresh, unchanged command controls; exhaustive Manual/non-Manual status combinations; XAE/disk hash readback')
