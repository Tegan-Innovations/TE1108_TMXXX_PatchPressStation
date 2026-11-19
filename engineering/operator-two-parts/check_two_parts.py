"""Execute saved operator/process/nest ST with scripted inputs; no equipment access."""
from pathlib import Path
import re,json,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2];plc=root/'TwinCAT Patch Press/PatchPress'
helper=(root/'engineering/patch-feeding/implementation/st_branch_runner.py').read_text()
casts=['INT_TO_UINT','TO_UINT','UINT_TO_E_TablePosition','UDINT_TO_LREAL']
helper=helper.replace("'UDINT_TO_UINT': 'int',", "'UDINT_TO_UINT': 'int',"+','.join(repr(x)+": 'int'" for x in casts)+',')
h={};exec(helper,h)
enums={}
for f in (plc/'DUTs').rglob('E_*.TcDUT'):
 t=E.parse(f);name=t.getroot()[0].get('Name');decl=t.findtext('.//Declaration') or ''
 decl=re.sub(r'//[^\n]*','',decl)
 for k,v in re.findall(r'(\w+)\s*:=\s*(-?\d+)',decl):enums[name+'.'+k]=int(v)
def source(path,method=None):
 t=E.parse(plc/path);o=t.getroot()[0] if method is None else next(m for m in t.findall('.//Method') if m.get('Name')==method)
 return o.findtext('Implementation/ST') or ''
def clean(s):return re.sub(r'//[^\n]*','',re.sub(r'\(\*.*?\*\)','',s,flags=re.S))
def cases(s):
 stack=[];out=[]
 for line in s.splitlines():
  m=re.match(r'\s*CASE (\w+) OF\s*$',line)
  if m:stack.append([m[1],True]);continue
  if re.match(r'\s*END_CASE\s*;?$',line):out.append('END_IF');stack.pop();continue
  m=re.match(r'\s*([\w.]+):\s*(.*)',line)
  if m and stack:
   name,first=stack[-1];out.append(('IF ' if first else 'ELSIF ')+name+' = '+m[1]+' THEN '+m[2]);stack[-1][1]=False
  else:out.append(line)
 assert not stack
 return '\n'.join(out)
def initial(s):
 v={k:0 for k in re.findall(h['var'],s)};v.update(enums);return v
def execute(s,v):h['execute'](s,v)
def remove_calls(s):return re.sub(r'\b(?:rt\w+|ton\w+)\([^;]*\);','',s,flags=re.S)
operator=cases(remove_calls(clean(source('POUs/03_Stations/Operator/FB_OperatorStation.TcPOU','Cyclic'))))
process=cases(remove_calls(clean(source('POUs/01_Core/Process/FB_ProcessCycle.TcPOU','Cyclic'))))
class Operator:
 def __init__(self,product=False,pbup=False,empty=True):
  self.v=initial(operator);self.prev=False
  self.v.update({'bAutomaticActive':True,'bIndexStable':True,'bPartPresent':product,'bPbupPresent':pbup,'bAllowEmptyNestIndex':empty,'bRequireRejectConfirm':True})
 def scan(self,**kw):
  self.v.update(kw);cur=bool(self.v['bTwoHandsSafe']);self.v['rtIndexAttempt.Q']=cur and not self.prev;self.prev=cur;execute(operator,self.v);return self.v
for product in [False,True]:
 for pbup in [False,True]:
  o=Operator(product,pbup)
  for _ in range(4):o.scan()
  assert bool(o.v['stStatusInternal.bIndexPermissive'])==(product==pbup),(product,pbup)
  assert o.v['stStatusInternal.bPartPresent']==product and o.v['stStatusInternal.bPbupPresent']==pbup
  o.scan(bTwoHandsSafe=True)
  assert bool(o.v['stStatusInternal.bMissingPbupAlert'])==(product and not pbup)
  assert bool(o.v['stStatusInternal.bMissingProductAlert'])==(pbup and not product)
  if product!=pbup:assert ('PBUP missing' if product else 'Product missing') in o.v['sMessage']
o=Operator(empty=False)
for _ in range(4):o.scan()
assert not o.v['stStatusInternal.bIndexPermissive'],'preserve configured no-empty policy'
o=Operator(True,True)
for _ in range(4):o.scan()
o.scan(bPbupPresent=False);assert not o.v['stStatusInternal.bIndexPermissive'],'same-scan load loss clears latched exchange'
o.scan(bTwoHandsSafe=True);assert o.v['bMissingPbupAlert']
o.scan(bPbupPresent=True);assert not o.v['bMissingPbupAlert']
o.scan(bAutomaticActive=False);assert not o.v['stStatusInternal.bIndexPermissive']
print('PASS four presence combinations, messages/attempt warnings, same-scan revalidation, correction and existing empty-load setting')

class Process:
 def __init__(self):
  self.v=initial(process);self.prev=False
  self.v.update({k:True for k in ['bEnable','bSafetyOk','bIndexReady','bIndexLocked','bStationsIndexPermissive','bOperatorIndexPermissive','bTemperatureIndexPermissive','bNestEnableIndexPermissive','bAllStationsReady']})
  self.v['eStateInternal']=enums['E_CycleState.WaitingForProcessCycleTrigger']
 def scan(self,**kw):
  self.v.update(kw);cur=bool(self.v['bTwoHandsSafe']);self.v['rtCycleTrigger.Q']=cur and not self.prev;self.prev=cur;execute(process,self.v);return self.v
p=Process();p.scan(bOperatorIndexPermissive=False,bTwoHandsSafe=True)
for _ in range(5):p.scan(bOperatorIndexPermissive=True);assert not p.v['bRequestIndex']
p.scan(bTwoHandsSafe=False);p.scan(bTwoHandsSafe=True);p.scan();p.scan()
assert p.v['bRequestIndex']
for state in ['ValidatingIndexPermissives','RequestingIndexMove']:
 p=Process();p.v['eStateInternal']=enums['E_CycleState.'+state];p.prev=True
 p.scan(bTwoHandsSafe=True,bOperatorIndexPermissive=False)
 assert p.v['eStateInternal']==enums['E_CycleState.WaitingForProcessCycleTrigger'] and not p.v['bRequestIndex']
 for _ in range(3):p.scan(bOperatorIndexPermissive=True);assert not p.v['bRequestIndex']
p=Process();p.v['eStateInternal']=enums['E_CycleState.WaitingForIndexStart']
p.scan(bOperatorIndexPermissive=False,bIndexBusy=True)
assert p.v['eStateInternal']==enums['E_CycleState.WaitingForIndexComplete'] and not p.v['bFault']
print('PASS stale held hands cannot start after correction; validation/request gaps abort; live sensor loss does not abort an index already committed')

# Keep product-removal and reject proof semantics independent of PBUP cleanup.
o=Operator(True,False);o.v['stOperatorNest.stResult.bValid']=True;o.v['stOperatorNest.stResult.bPassed']=False
o.scan();o.scan();assert o.v['eState']==enums['E_OperatorExchangeState.WaitingForPartRemoval']
o.scan(bPartPresent=False,bPbupPresent=True)
assert o.v['bPartRemovedConfirmed'] and o.v['eState']==enums['E_OperatorExchangeState.WaitingForRejectConfirmation']
o.scan(bRejectChutePartPresent=False);o.scan(bRejectChutePartPresent=True)
assert o.v['bRejectConfirmed'] and not o.v['stStatusInternal.bIndexPermissive']
o.scan();assert not o.v['stStatusInternal.bIndexPermissive'],'PBUP only is not a valid next load'
o.scan(bPbupPresent=False);assert o.v['stStatusInternal.bIndexPermissive']
print('PASS assembled return with PBUP pocket empty; product removal/chute edge preserved; remaining PBUP still prevents next index')

nest=clean(source('POUs/02_Components/Index/FB_NestTableManager.TcPOU','Cyclic'))
all_text=nest+clean(source('POUs/02_Components/Index/FB_NestTableManager.TcPOU','ClearOperatorNest'))+clean(source('POUs/02_Components/Index/FB_NestTableManager.TcPOU','FinaliseResultAtPosition'))
def loops(s):
 pattern=r'FOR i := 1 TO 4 DO(.*?)END_FOR'
 while re.search(pattern,s,re.S):
  s=re.sub(pattern,lambda m:'\n'.join(re.sub(r'\bi\b',str(n),m[1]) for n in range(1,5)),s,flags=re.S)
 return s
prefix=loops(nest[:nest.index('IF bIndexStable AND')])
case=nest[nest.index('CASE eIndexPosition OF'):nest.index('END_CASE')+len('END_CASE')]
map_for=nest[nest.index('END_CASE')+len('END_CASE'):nest.index('    uiNest :=')]
presence=nest[nest.index('    uiNest :='):nest.rfind('END_IF')]
class Nests:
 def __init__(self):
  self.v=initial(all_text)
  for prefix_name,field in re.findall(r'(aNestInternal|aNestStatisticsInternal)\[\w+\]\.(\w+(?:\.\w+)*)',all_text):
   for n in range(1,5):self.v[prefix_name+f'[{n}].'+field]=0
  for n in range(1,5):self.v[f'aNestEnabled[{n}]']=True
  self.v.update({'bIndexStable':True,'eIndexPosition':1,'eOperatorPosition':1,'operatorPos':1})
 def scan(self,**kw):
  self.v.update(kw);execute(prefix,self.v)
  if self.v['bIndexStable'] and self.v['eIndexPosition']!=enums['E_TablePosition.Unknown']:
   execute(cases(case),self.v)
   mapping=loops(map_for)
   for n in range(1,5):mapping=mapping.replace(f'aNestInternal[aPositionToNest[{n}]]',f'aNestInternal[{self.v[f"aPositionToNest[{n}]"]}]')
   execute(mapping,self.v)
   execute(presence.replace('aPositionToNest[TO_UINT(eOperatorPosition)]','aPositionToNest[operatorPos]'),self.v)
  return self.v
 def record(self,n,field):return self.v[f'aNestInternal[{n}].'+field]
n=Nests();n.scan(bPartPresent=True,bPbupPresent=False)
assert n.record(1,'bPartLoadedPulse') and not n.record(1,'bLoadSetComplete')
n.scan(bPbupPresent=True)
assert not n.record(1,'bPartLoadedPulse') and n.record(1,'bLoadSetComplete')
n.scan(bIndexStable=False,bPbupPresent=False,bPartPresent=False)
assert n.record(1,'bPartPresent') and n.record(1,'bPbupPresent') and n.record(1,'bLoadSetComplete')
assert not n.record(1,'bPartLoadedPulse')
n.scan(bIndexStable=True,eIndexPosition=2)
assert n.v['uiNest']==2 and not n.record(2,'bPartPresent') and n.record(1,'bLoadSetComplete')
n.scan(eIndexPosition=3,bPbupPresent=True)
assert n.v['uiNest']==3 and n.record(3,'bPbupPresent') and not n.record(3,'bLoadSetComplete')
n.scan(eIndexPosition=4,bPartPresent=True,bPbupPresent=True)
assert n.v['uiNest']==4 and n.record(4,'bLoadSetComplete')
print('PASS either loading order, PBUP-only memory, one-scan product edges, index freeze and physical nest identity across four positions')

# Completed product retains paired-load history after PBUP was assembled away from its pocket.
n=Nests();n.scan(bPartPresent=True,bPbupPresent=True)
for field,value in [('stResult.bValid',True),('stResult.bPassed',False),('bStatisticsCounted',True),('eDisposition',enums['E_PartDisposition.Reject'])]:n.v['aNestInternal[1].'+field]=value
n.scan(bPbupPresent=False,bOperatorReloadPermitted=False)
assert n.record(1,'bLoadSetComplete') and n.record(1,'bStatisticsCounted') and n.record(1,'stResult.bValid')
n.scan(bPartPresent=False);n.scan(bPartPresent=True)
assert n.record(1,'stResult.bValid') and n.record(1,'bStatisticsCounted') and not n.record(1,'bPartLoadedPulse')
n.scan(bOperatorReloadPermitted=True,bPbupPresent=True)
assert n.record(1,'bPartLoadedPulse') and not n.record(1,'stResult.bValid') and not n.record(1,'bStatisticsCounted')
n.scan();assert not n.record(1,'bPartLoadedPulse')
print('PASS returned result/count history survives empty PBUP pocket and early reload; reject exchange must allow a new product identity')

finalise=clean(source('POUs/02_Components/Index/FB_NestTableManager.TcPOU','FinaliseResultAtPosition'))
finalise=re.sub(r'uiId := GetNestIdAtPosition\(ePosition\);','uiId := testNestId;',finalise)
for s in ['ePatchDispenseStage','eHeatStakeStage','eVisionStage']:n.v['aNestInternal[1].'+s]=enums['E_NestStageStatus.Complete']
for token in re.findall(h['var'],finalise):n.v.setdefault(token,0)
n.v.update(enums);n.v['testNestId']=1
execute(finalise,n.v);execute(finalise,n.v)
assert n.v['aNestStatisticsInternal[1].udiTotalTests']==1 and n.v['aNestStatisticsInternal[1].udiGoodParts']==1
n.scan(bPbupPresent=False,bOperatorReloadPermitted=False)
execute(finalise,n.v)
assert n.v['aNestStatisticsInternal[1].udiTotalTests']==1,'PBUP changes cannot count a second product'
print('PASS actual existing finalisation/statistics still counts one complete product exactly once')

machine=source('POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU','Cyclic')
assert 'AND bOperatorLoadValid' in machine
move=machine[machine.index('stPermissives.bIndexMoveAllowed :='):machine.index('fbCommissioningGuard.Cyclic(')]
assert 'bOperatorLoadValid' not in move and 'bOperatorIndexPermissive' not in move
for name in ['stPatchDispenseNest','stHeatStakeNest','stVisionNest']:assert name+'.bLoadSetComplete' in machine
assert 'OR aNestSnapshot[iNestCheck].bPbupPresent' in machine
assert 'AND NOT stInputs.bLoadingStationPbupPresent\nTHEN' in machine
assert 'bIndexStable := stInputs.bIndexReady AND stInputs.bIndexLocked AND NOT stIndexStatus.bBusy' in machine
assert 'bOperatorReloadPermitted :=' in machine
content=(root/'TwinCAT Patch Press/PatchPress_HMI/Contents/Screens/Main.content').read_text(encoding='utf-8-sig')
config=json.loads((root/'TwinCAT Patch Press/PatchPress_HMI/Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
for suffix,field in [('1','bLoadingStationPbupPresent'),('2','bLoadingStationEaglePresent')]:
 block=re.search(r'<div\b[^>]*\bid="TcHmiHtmlHost_OperatorNestPartPresent'+suffix+r'"[^>]*>.*?</div>',content,re.S).group()
 sym='ADS.PLC1.GVL_HMI.stStatus.'+field
 assert sym in block and config['SYMBOLS'][sym]['MAPPING'].endswith('::'+field)
assert 'id="TcHmiHtmlHost_OperatorNestPartsPresent"' not in content
for data in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',content,re.S):json.loads(data)
for key in ['ADS-PLC1.ST_HmiStatus','ADS-PLC1.ST_Nest','ADS-PLC1.ST_OperatorStationStatus']:
 schema=config['DEFINITIONS']['ADS'][key];assert set(schema['required'])==set(schema['properties'])
print('PASS start-only integration, downstream validity gates, disabled PBUP nest, empty clearing, native LED bindings and typed ADS definitions')

events=source('POUs/05_AlarmsAndEvents/PRG_Events.TcPOU')
manager='\n'.join(E.parse(plc/'POUs/05_AlarmsAndEvents/FB_EventsManager.TcPOU').getroot().itertext())
for slot in [2,3]:
 assert f'aWarningEvents[1, {slot}] := TRUE;' in events
 assert f'GVL_MASTER.stStationEvents[1].aEvents[{slot}].bMessage := TRUE;' in events
 assert f'GVL_MASTER.stStationEvents[1].aEvents[{slot}].bActive := FALSE;' in events
assert manager.index('ELSIF aWarningEvents[k[0], k[1]] THEN') < manager.index('ELSIF stStationEvents[k[0]].aEvents[k[1]].bMessage THEN')
mapping=source('POUs/04_IO_Mapping/PRG_TerminalMapping.TcPOU','ReadInputs')
assert 'bLoadingStationPbupPresent := GVL_EtherCAT.stTerm19_EL1809.iEL1809_Ch1;' in mapping
print('PASS warning text classification/auto-clear and provisional Term19 Input1 mapping')
