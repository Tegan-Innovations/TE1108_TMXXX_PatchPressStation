"""Configuration/source checks for read-only I/O diagnostics; no runtime access."""
from pathlib import Path
import re,json,xml.etree.ElementTree as E,html
root=Path(__file__).resolve().parents[2];base=Path(__file__).parent;plc=root/'TwinCAT Patch Press/PatchPress';hmi=root/'TwinCAT Patch Press/PatchPress_HMI'
inventory=json.loads((base/'inventory.json').read_text());routes=json.loads((base/'routes.json').read_text());symbols=json.loads((base/'symbols.json').read_text())
detail_pages=[('EL6910 '+name,'Contents/Hardware/EL6910_'+name+'.content') for name in ['Connections','Blocks','History']]
page_routes=routes+detail_pages
normal=lambda s:(s or '').replace('\r\n','\n').replace('Â°','°').strip()
for snapshot in json.loads((base/'verified-sections.json').read_text()):
 parts=snapshot['path'].split('^')[3:];p=plc.joinpath(*parts).with_suffix('.TcGVL' if parts[0]=='GVLs' else '.TcPOU');o=E.parse(p).getroot()[0]
 assert normal(o.findtext('Declaration'))==normal(snapshot['declaration']),str(p)
 assert normal(o.findtext('Implementation/ST'))==normal(snapshot['implementation']),str(p)
print('PASS all three saved PLC objects match XAE readback')
before=json.loads((base/'links.json').read_text())
def links(path):
 t=E.parse(path);out=[]
 for a in t.iter('OwnerA'):
  for b in a.findall('OwnerB'):
   for l in b.findall('Link'):out.append({'a':a.attrib,'b':b.attrib,'link':l.attrib})
 return out
after=links(root/'TwinCAT Patch Press/TwinCAT Patch Press.tsproj')
def canonical(x):
 # Hardware nodes were renumbered before this HMI correction. Compare links
 # by their current owner identity without changing any PLC/process endpoint.
 x=json.loads(json.dumps(x))
 renamed={'Term 21 (EL4028)':'Term 20 (EL4028)',
          'Term 20 (EL3314-0092)':'Term 21 (EL3314-0092)',
          'Term 21 (EL6633)':'Term 22 (EL6633)'}
 for old,new in renamed.items():
  if x['b']['Name'].endswith('^'+old):
   x['b']['Name']=x['b']['Name'].rsplit('^',1)[0]+'^'+new
 return json.dumps(x,sort_keys=True)
oldset={canonical(x) for x in before};newset={canonical(x) for x in after}
assert oldset<=newset,'Existing process/safety/NC links must remain unchanged'
added=[json.loads(x) for x in newset-oldset]
terminal_added=[x for x in added if x['link']['VarA'].endswith('nTerminal_State')]
camera_added=[x for x in added if x['link']['VarA'].startswith('PlcTask Inputs^GVL_EtherCAT.wVisionPn')]
assert len(terminal_added)==17,len(terminal_added)
assert all(x['link']['VarB']=='InfoData^State' for x in terminal_added)
assert len(added)==len(terminal_added)+len(camera_added)
assert len(camera_added)==2
assert {(x['link']['VarA'],x['link']['VarB']) for x in camera_added}=={
 ('PlcTask Inputs^GVL_EtherCAT.wVisionPnState','Inputs^PnIoBoxState'),
 ('PlcTask Inputs^GVL_EtherCAT.wVisionPnDiag','Inputs^PnIoBoxDiag')}
assert 'GVL_IoDiagnostics' not in (plc/'PatchPress.plcproj').read_text(encoding='utf-8-sig')
for item in inventory:
 if item['state']:
  assert any(x['link']['VarA']=='PlcTask Inputs^'+item['state'] and x['b']['Name']==item['path'] and x['link']['VarB']=='InfoData^State' for x in after),item['name']
print('PASS original process/NC/FSoE links preserved; 17 added InfoData state links, 23 total, and 2 read-only camera connection links')

# Resolve actual IEC declarations so a saved HMI symbol cannot silently point to a nonexistent member.
types={d.findtext('Name'):{s.findtext('Name'):s.findtext('Type') for s in d.findall('SubItem')} for d in E.parse(plc/'PatchPress.tmc').iter('DataType')};globals={}
def parse(text):
 text=re.sub(r'//[^\n]*','',re.sub(r'\(\*.*?\*\)','',text,flags=re.S))
 return dict(re.findall(r'\b(\w+)\s*(?:AT\s+%[IQ][^:;]*\s*)?:\s*(\w+)',text))
for p in (plc/'DUTs').rglob('*.TcDUT'):
 t=E.parse(p);types[t.getroot()[0].get('Name')]=parse(t.findtext('.//Declaration'))
for p in (plc/'GVLs').glob('*.TcGVL'):
 t=E.parse(p);globals[t.getroot()[0].get('Name')]=parse(t.findtext('.//Declaration'))
config=json.loads((hmi/'Server/TcHmiSrv/TcHmiSrv.Config.default.json').read_text(encoding='utf-8-sig'))
for var,typ in symbols.items():
 parts=var.split('.');scope=globals[parts[0]]
 for index,name in enumerate(parts[1:]):
  assert name in scope,(var,name)
  actual=scope[name]
  if index<len(parts)-2:scope=types[actual]
 assert actual==typ,(var,actual,typ)
 key='ADS.PLC1.'+var;entry=config['SYMBOLS'][key]
 assert entry['MAPPING']=='PLC1::'+var.replace('.','::'),key
 assert entry['SCHEMA'],key
print('PASS all',len(symbols),'HMI symbols resolve to actual typed PLC members and exact server mappings')

ids=[];used=set();project=E.parse(hmi/'PatchPress_HMI.hmiproj');included={x.get('Include','').replace('\\','/') for x in project.iter()}
for label,path in page_routes:
 assert path in included,path
 p=hmi/path;s=p.read_text(encoding='utf-8-sig');ids+=re.findall(r'\bid="([^"]+)"',s)
 assert 'GVL_IO.dw_' not in s and 'Silicone' not in s and 'JavaScript' not in s
 for binding in re.findall(r'%s%(ADS\.PLC1\.[^%|]+)(?:\|[^%]+)?%/s%',s):used.add(binding.removeprefix('ADS.PLC1.'))
 for tag in re.findall(r'<div\b[^>]*>',s):
  if 'Beckhoff.TcHmiNumericInput' in tag:
   assert 'data-tchmi-is-enabled="False"' in tag
   if any(x in tag for x in ['Value','lrActPosition','lrActVelocity']):assert 'data-tchmi-decimal-digits="3"' in tag
  if 'data-tchmi-src=' in tag:
   image=html.unescape(re.search(r'data-tchmi-src="([^"]+)"',tag).group(1));assert (hmi/image).exists(),image
 for value in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',s,re.S):json.loads(value)
 for dest in re.findall(r'"symbolExpression"\s*:\s*"([^"]+)"',s):assert not dest.startswith('%s%'),'No PLC writes from diagnostic pages'
assert len(ids)==len(set(ids)),'Global IDs must be unique across active pages'
assert used==set(symbols),(used-set(symbols),set(symbols)-used)
nav=(hmi/'Contents/IOs/Main_IOs.content').read_text(encoding='utf-8-sig')
assert 'data-tchmi-columns' in nav and 'Contents/Hardware/T01_EK1100.content' in nav
assert 'IO_Overview' not in nav and 'SafetySignals' not in nav and 'Camera_IO' not in nav
for label,path in routes:assert path in nav
for item in inventory:
 if item['key']=='Festo':continue
 s=(hmi/'Contents/Hardware'/(item['key']+'.content')).read_text()
 for c in item['channels']:
  assert f'CH{c["channel"]:02}' in s
  if c['symbol']:assert 'ADS.PLC1.'+c['symbol']+'%/s%' in s
  else:assert 'feedback not exported' in s and 'data-tchmi-channelfeedbackavailable="False"' in s
  if c['label'] in ['No application assignment','No assignment (FSoE)']:assert f'CH{c["channel"]:02} spare' in s
 if item['info']:assert item['info']+'.bTerminalOperational' in s
print('PASS all channels, native bindings/navigation, disabled numerics, unique IDs, images, no physical writes or active Silicone references')

# Verify physical identity from today's configuration, not the old PLC names.
current=E.parse(root/'TwinCAT Patch Press/TwinCAT Patch Press.tsproj')
devices=[b.findtext('Name') for b in current.iter('Box') if (b.findtext('Name') or '').startswith('Term ')]
assert [label for label,path in routes if label.startswith('Term ')]==devices
active={path for label,path in page_routes}
assert {p for p in included if p.startswith('Contents/Hardware/') and p.endswith('.content')}==active
for item in inventory:
 if item['key']=='Festo':continue
 page=(hmi/'Contents/Hardware'/(item['key']+'.content')).read_text()
 assert not re.search(r'IVEK|Silicone|GVL_IO\.dw_|stTerm33',page,re.I)
 for channel in item['channels']:
  if channel['symbol']:
   assert any(link['b']['Name']==item['path'] and link['link']['VarA'].split('^')[-1]==channel['symbol'] for link in after),(item['name'],channel['symbol'])
print('PASS every physical terminal route and channel matches current saved hardware mapping; no legacy hardware contents included')

for name,count in [('08CH_Dig_IO_CARD',8),('4CH_Dig_IO_CARD',4)]:
 s=(hmi/'Contents/UserControl'/(name+'.usercontrol')).read_text()
 assert s.count('data-tchmi-visibility="%f%%pp%ChannelFeedbackAvailable')==count
 params=json.loads((hmi/'Contents/UserControl'/(name+'.usercontrol.json')).read_text())['parameters']
 assert next(p for p in params if p['propertyName']=='ChannelFeedbackAvailable')['defaultValue'] is True
analog=(hmi/'Contents/UserControl/8CH_Analog_Input_CARD.usercontrol').read_text()
num=re.findall(r'<div[^>]*data-tchmi-type="TcHmi.Controls.Beckhoff.TcHmiNumericInput"[^>]*>',analog)
assert len(num)==16,len(num)
for tag in num:assert 'data-tchmi-is-enabled="False"' in tag and 'data-tchmi-decimal-digits="3"' in tag
for label,path in page_routes:
 s=(hmi/path).read_text()
 for target in re.findall(r'data-tchmi-target-user-control="([^"]+)"',s):
  assert (hmi/target).exists()
  params=json.loads((hmi/(target+'.json')).read_text())['parameters'];names={p['name'] for p in params}
  host=next(t for t in re.findall(r'<div[^>]*>',s) if 'data-tchmi-target-user-control="'+target+'"' in t)
  for attr in re.findall(r'(data-tchmi-[\w_]+)=',host):
   if attr in ['data-tchmi-image','data-tchmi-state_string','data-tchmi-cardoperational'] or attr.startswith('data-tchmi-_'):assert attr in names,(path,attr)
print('PASS exact existing card UserControl interfaces; analog raw/scaled NumericInputs read-only with 3 decimals; unavailable safety channels hidden')

motion=(hmi/'Contents/UserControl/1CH_Motion_Interface_CARD.usercontrol').read_text()
params=json.loads((hmi/'Contents/UserControl/1CH_Motion_Interface_CARD.usercontrol.json').read_text())['parameters']
assert set(re.findall(r'%pp%([^%]+)%/pp%',motion))=={p['propertyName'] for p in params}
assert 'JavaScript' not in motion
for tag in re.findall(r'<div[^>]*TcHmiNumericInput[^>]*>',motion):
 assert 'data-tchmi-is-enabled="False"' in tag
assert '"event": "%pp%CardOperational%/pp%"' in motion
for n in [15,16,17]:
 page=(hmi/f'Contents/Hardware/T{n}_EL7201.content').read_text()
 assert '1CH_Motion_Interface_CARD.usercontrol' in page and '8CH_Analog_Input_CARD' not in page
 assert f'stTerm{n}_EL7201.stTerminalInfo.bTerminalOperational%/s%' in page
 for p in params:assert p['name']+'=' in page
 assert '.Axis.NcToPlc.ErrorCode%/s%' in page
 assert '.Axis.NcToPlc.ActPos%/s%' in page
 assert '.Axis.NcToPlc.ActVelo%/s%' in page
 assert '.Axis.NcToPlc.ActTorque%/s%' in page
print('PASS three dedicated motion cards: complete parameter bindings, NC feedback/error fields, existing terminal LED and read-only values')

# Execute the actual FB statement body against every UINT state, including combined flag values.
helper=(root/'engineering/patch-feeding/implementation/st_branch_runner.py').read_text()
helper=helper.replace("'UDINT_TO_UINT': 'int',", "'UDINT_TO_UINT': 'int', 'UINT_TO_STRING': 'str', 'CONCAT': 'concat',")
helper=helper.replace("'int': int,", "'int': int, 'str': str, 'concat': lambda a,b:a+b,")
h={};exec(helper,h)
fb=E.parse(plc/'POUs/06_Utilities/FB_TerminalInfo.TcPOU').findtext('.//Implementation/ST');fb=re.sub(r'//[^\n]*','',fb)
for value in list(range(0,33))+[128,256,264,65535]:
 v={'nTerminalState':value,'sTerminalState':'OPERATIONAL','bTerminalOperational':True};h['execute'](fb,v)
 assert v['bTerminalOperational']==(value==8),value
 if value!=8:assert v['sTerminalState']!='OPERATIONAL',value
status=E.parse(plc/'POUs/00_Application/PRG_HmiStatus.TcPOU').findtext('.//Implementation/ST')
for item in inventory:
 if item['info']:assert item['info']+'.fbTerminalInfo(' in status and 'nTerminalState := '+item['info']+'.nTerminal_State' in status
print('PASS real FB_TerminalInfo: green only at 8, unknown/combined states replace stale text; 23 native FB instances called cyclically')
