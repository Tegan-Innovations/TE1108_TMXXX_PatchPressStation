"""Execute saved ST with scripted feedback/timers, and verify native HMI wiring."""
from pathlib import Path
import re,json,copy,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
base=Path(__file__).parent
field='udiDriveStopDelayMs'
test=root/'engineering/station-settings/check_settings.py'
source=test.read_text().replace('==30','==40').replace('else 30','else 40')
source=re.sub(r'==10\b','==200',source)
source=source.replace('[(0.1,30),(0.1,10),(0.1,50),(100,15000),(0,2000)]','[(0.1,40),(0.1,200),(0.1,50),(100,15000),(0,5000),(0,5000)]')
ctx={'__file__':str(test)}
exec(compile(source,str(test),'exec'),ctx)
assert ctx['fields']['Patch'][field]==2000
v=ctx['initial']();ctx['scan'](v)
assert v['GVL_HMI.stPatchProcessApplied.'+field]==2000
ctx['scan'](v,**{'GVL_HMI.stPatchProcessEdit.'+field:2345,'GVL_HMI.bPatchSettingsApply':True})
ctx['scan'](v)
assert v['GVL_HMI.stPatchProcessApplied.'+field]==2345
restarted=ctx['initial']();restarted.update({k:x for k,x in v.items() if k.startswith('GVL_Persistent.')});ctx['scan'](restarted)
assert restarted['GVL_HMI.stPatchProcessEdit.'+field]==2345
print('PASS new setting default 2000 ms, Apply/save/restart; all ranges and handshake gates')

test=root/'engineering/patch-dispense-m1/check_sequence.py'
source=test.read_text().replace("assert 'bPatchOpticalLeft", "mapping = re.sub(r'\\s*:=\\s*', ' := ', mapping)\nassert 'bPatchOpticalLeft",1)
# Existing sequence regression scripts timer completion, equivalent to zero run-on.
source=source.replace("v['tonAirBlowDelay.Q']=True","v['tonAirBlowDelay.Q']=True\n    v['tonDriveStopDelay.Q']=True")
ctx={'__file__':str(test)}
exec(compile(source,str(test),'exec'),ctx)
initial=ctx['initial'];branch_scan=ctx['scan'];expression=ctx['h']['expression']
raw=ctx['raw']
timers={}
for name,setting in [('tonDriveStopDelay',field),('tonAirBlowDelay','udiAirBlowDelayMs'),('tonRelease','udiReleaseMs')]:
 match=re.search(name+r'\(IN := (.*?),\s*PT := UDINT_TO_TIME\(stProcessSettingsInternal\.'+setting+r'\)\);',raw,re.S)
 assert match,name
 timers[name]=(match.group(1),setting)
def scan(v,now,**updates):
 v.update(updates)
 for name,(condition,setting) in timers.items():
  active=expression(condition,v)
  if active:start=v.setdefault('_'+name,now)
  else:v.pop('_'+name,None);start=now
  v[name+'.Q']=active and now-start>=v['stProcessSettingsInternal.'+setting]
 return branch_scan(v)
def new(delay,feed_only=False):
 v=initial(feed_only=feed_only,step=20)
 v.update({'stProcessSettingsInternal.'+field:delay,'stProcessSettingsInternal.udiAirBlowDelayMs':3000,'stProcessSettingsInternal.udiReleaseMs':5000,
  'bSupportRetractedInternal':False,'bSupportExtendedInternal':True,'bDriveMovingInternal':True,'bDriveStandstillInternal':False,'bDriveBusyInternal':True})
 return v
for delay in [0,1,100,2000,5000]:
 for feed_only in [False,True]:
  for right in [False,True]:
   v=new(delay,feed_only)
   scan(v,0,bPatchOpticalLeftInternal=False,bPatchOpticalRightInternal=right)
   assert v['usiStepInternal']==20 and not v['tonDriveStopDelay.Q']
   scan(v,10,bPatchOpticalLeftInternal=True)
   scan(v,110)
   assert v['usiStepInternal']==21 and '_tonDriveStopDelay' not in v
   scan(v,120,bPatchOpticalLeftInternal=False)
   assert v['usiStepInternal']==(22 if delay==0 else 23)
   assert v['bDriveRunRequestInternal']==(delay>0)
   if delay:
    # A subsequent patch must neither restart the timer nor prevent stopping.
    scan(v,120+delay-1,bPatchOpticalLeftInternal=True,bPatchOpticalRightInternal=not right)
    assert v['bDriveRunRequestInternal'] and not v['bVerticalDownRequestInternal']
    scan(v,120+delay)
    assert v['usiStepInternal']==22 and not v['bDriveRunRequestInternal']
   scan(v,121+delay)
   assert v['usiStepInternal']==22 and not v['bVerticalDownRequestInternal']
   scan(v,130+delay,bDriveMovingInternal=False,bDriveStandstillInternal=True,bDriveBusyInternal=False)
   assert v['usiStepInternal']==(0 if feed_only else 40)
   if feed_only:assert not v['stResultInternal.bValid'] and not v['bAirBlowRequestInternal']
print('PASS 0/1/100/2000/5000 ms, full/feed-only, right ignored, TRUE holds no timer, FALSE starts exact timer, bounce/new patch cannot extend, standstill before descent')
v=new(2000)
scan(v,0,bPatchOpticalLeftInternal=True,bPatchOpticalRightInternal=False)
scan(v,100,bPatchOpticalLeftInternal=False)
scan(v,2100)
scan(v,2110,bDriveMovingInternal=False,bDriveStandstillInternal=True,bDriveBusyInternal=False)
scan(v,2120,bVerticalUpInternal=False,bVerticalDownInternal=False)
scan(v,2999);assert not v['bAirBlowRequestInternal']
scan(v,3000);assert v['bAirBlowRequestInternal']
scan(v,10120,bVerticalDownInternal=True)
assert v['usiStepInternal']==50 and not v['bAirBlowRequestInternal']
print('PASS independent 3 s air delay remains continuous through run-on/standstill/descent and cuts at DOWN')
for cause,value in [('bStopRequestInternal',True),('bSafetyOkInternal',False),('bEnableInternal',False),('bCommissionedInternal',False),('bDriveFaultInternal',True),('bSimulatedFault',True),('bVerticalUpInternal',False),('bSupportExtendedInternal',False),('tonFeed.Q',True)]:
 v=new(2000)
 scan(v,0,bPatchOpticalLeftInternal=True,bPatchOpticalRightInternal=False)
 scan(v,100,bPatchOpticalLeftInternal=False)
 assert v['usiStepInternal']==23
 scan(v,200,**{cause:value})
 assert not v['bDriveRunRequestInternal'] and not v['bVerticalDownRequestInternal'],cause
 scan(v,210)
 assert not v['tonDriveStopDelay.Q'] and '_tonDriveStopDelay' not in v,cause
print('PASS run-on interrupted by stop/safety/disable/commissioning withdrawal/drive fault/feedback loss/feed watchdog; timer resets')
for stuck in [False,True]:
 v=new(2000)
 for now in [0,100,3000]:scan(v,now,bPatchOpticalLeftInternal=stuck,bPatchOpticalRightInternal=not stuck)
 assert v['usiStepInternal'] in [20,21] and v['bDriveRunRequestInternal']
 scan(v,30000,**{'tonFeed.Q':True})
 assert v['bFaultInternal'] and not v['bDriveRunRequestInternal']
v=new(2000);v['bDriveMovingInternal']=False
scan(v,0,bPatchOpticalLeftInternal=True,bPatchOpticalRightInternal=False)
scan(v,10,bPatchOpticalLeftInternal=False)
assert v['usiStepInternal']==21 and '_tonDriveStopDelay' not in v
print('PASS missing/stuck left sensor still times out; observed movement remains mandatory')

hmi=root/'TwinCAT Patch Press/PatchPress_HMI'
page=(hmi/'Contents/Screens/Settings/settings_PatchDispense.content').read_text(encoding='utf-8-sig')
d=json.loads((hmi/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
before=json.loads((base/'TcHmiSrv.Config.default.json.before').read_text(encoding='utf-8-sig'))
expected=copy.deepcopy(before)
for kind in ['Edit','Applied']:
 old=f'ADS.PLC1.GVL_HMI.stPatchProcess{kind}.udiAirBlowDelayMs';key=old.replace('udiAirBlowDelayMs',field)
 expected['SYMBOLS'][key]=copy.deepcopy(before['SYMBOLS'][old])
 expected['SYMBOLS'][key]['MAPPING']=expected['SYMBOLS'][key]['MAPPING'].replace('udiAirBlowDelayMs',field)
 for group in expected['USERGROUPS'].values():group['SYMBOLS'][key]=group['SYMBOLS'][old]
for key,schema in expected['DEFINITIONS']['ADS'].items():
 if key.endswith('.ST_PatchProcessSettings'):
  schema['properties'][field]=copy.deepcopy(schema['properties']['udiAirBlowDelayMs']);schema['required'].append(field)
assert expected==d,'Unrelated server configuration change'
for kind in ['Edit','Applied']:
 tag=re.search(r'<div id="Patch'+kind+field+r'"[^>]*>',page).group()
 assert 'data-tchmi-max-value="5000"' in tag and 'data-tchmi-min-value="0"' in tag and 'data-tchmi-decimal-digits="0"' in tag
assert f'stPatchProcessEdit.{field}|BindingMode=TwoWay' in page
assert f'PatchEdit{field}::Value' in page
print('PASS new native Edit/Applied controls, 0–5000 ms, Apply ordering, mappings/schema and exact inherited role permissions; server config otherwise unchanged')
changes=json.loads((base/'changes.json').read_text())
for name,c in changes.items():
 parts=c['path'].split('PatchPress Project^')[1].split('^')
 if name=='cyclic':node=E.parse(root.joinpath('TwinCAT Patch Press/PatchPress',*parts[:-1]).with_suffix('.TcPOU')).find(".//Method[@Name='Cyclic']")
 else:node=E.parse(root.joinpath('TwinCAT Patch Press/PatchPress',*parts).with_suffix('.TcDUT' if name=='process' else '.TcPOU')).getroot()[0]
 assert node.findtext('Declaration').strip()==c['newDeclaration'].strip(),name
 assert (node.findtext('Implementation/ST') or '').strip()==c['newImplementation'].strip(),name
print('PASS all four saved PLC sections match reviewed replacements')
