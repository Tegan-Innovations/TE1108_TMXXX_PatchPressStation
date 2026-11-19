"""Verify real saved native actions, initial appearance and bounded preservation."""
from pathlib import Path
import json,re,copy
B=Path(__file__).parent;R=B.resolve().parents[1];H=R/'TwinCAT Patch Press/PatchPress_HMI'
p=H/'Contents/Screens/Main.content';new=p.read_text(encoding='utf-8-sig');old=(B/'Main.before.content').read_text(encoding='utf-8-sig')
pattern=r'<div id="(TcHmiHtmlHost_(?:Patch|Heat|Vision)(?:Ready|Busy|Fault))"[^>]*>.*?</div>'
def blocks(text):return {m[1]:m[0] for m in re.finditer(pattern,text,re.S)}
before=blocks(old);after=blocks(new);assert len(after)==9 and before.keys()==after.keys()
def prop(block,name):return json.loads(re.search(r'<script data-tchmi-target-attribute="'+name+r'"[^>]*>(.*?)</script>',block,re.S)[1])
config=json.loads((H/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
def evaluate(actions,value):
 assert len(actions)==1
 condition=actions[0];assert condition['objectType']=='Condition' and condition['active']
 parts=condition['parts'];test=parts[0]['if'][0]
 assert test['compareOperator']=='==' and test['compare2']['value'] is True
 selected=parts[0]['then'] if value else parts[1]['else']
 assert len(selected)==1
 write=selected[0];assert write['objectType']=='WriteToSymbol' and write['active']
 assert write['symbolExpression']=='%ctx%owner::BackgroundColor%/ctx%'
 return write['value']['value']
for name,block in after.items():
 assert block.split('>')[0]==before[name].split('>')[0],name
 assert prop(block,'data-tchmi-background-color')=={'color':'rgba(137, 137, 137, 1)'}
 events=prop(block,'data-tchmi-trigger');original=prop(before[name],'data-tchmi-trigger')
 assert len(events)==2 and events[0]==original[0]
 assert events[1]['event']=='%ctx%owner::Id|EventRegistrationMode=Resolve%/ctx%.onAttached'
 assert events[1]['actions']==events[0]['actions']
 symbol=events[0]['event'];assert symbol.startswith('%s%ADS.PLC1.GVL_HMI.stStatus.')
 assert symbol[3:-4] in config['SYMBOLS']
 assert events[0]['actions'][0]['parts'][0]['if'][0]['compare1']['symbolExpression']==symbol
 for state in [False,True,False,True]:
  initial=evaluate(events[1]['actions'],state);changed=evaluate(events[0]['actions'],state)
  assert initial==changed==evaluate(original[0]['actions'],state)
  if not state:assert initial=={'color':'rgba(137, 137, 137, 1)'}
  else:assert 'stopPoints' in initial and initial['stopPoints']
 # Before any ADS callback, a newly created control already has a visible neutral fill.
 assert prop(block,'data-tchmi-background-color')['color']!='rgba(0, 0, 0, 0)'
assert re.sub(pattern,'<station-led/>',new,flags=re.S)==re.sub(pattern,'<station-led/>',old,flags=re.S)
ids=re.findall(r'<div\b[^>]*\bid="([^"]+)"',new);assert len(ids)==len(set(ids))
for script in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',new,re.S):json.loads(script)
print('PASS nine visible initial LED fills, matching native attach/change actions, true/false/reattach colors, exact symbol maps and unchanged surrounding Main content')
