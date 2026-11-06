"""Stage only the IO/HMI milestone; preserve unrelated working-tree changes."""
from pathlib import Path
import subprocess as S
import difflib, json, re, xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).parent
HMI='TwinCAT Patch Press/PatchPress_HMI/'
def git(*args,**kw):return S.check_output(['git',*args],cwd=ROOT,**kw)
def head(p):return git('show','HEAD:'+p).decode('utf-8-sig')
def stage(p,s):
 blob=git('hash-object','-w','--stdin',input=s.encode()).decode().strip()
 git('update-index','--add','--cacheinfo','100644',blob,p)
existing=git('diff','--cached','--name-only','-z').decode().strip('\0').split('\0')
routes=json.loads((BASE/'routes.json').read_text())
files=[HMI+p for _,p in routes]
files.append(HMI+'Contents/IOs/Main_IOs.content')
for name in ['08CH_Dig_IO_CARD','4CH_Dig_IO_CARD','8CH_Analog_Input_CARD','1CH_Motion_Interface_CARD']:
 files += [HMI+'Contents/UserControl/'+name+suffix for suffix in ['.usercontrol','.usercontrol.json']]
files += ['TwinCAT Patch Press/PatchPress/GVLs/GVL_EtherCAT.TcGVL',
 'TwinCAT Patch Press/PatchPress/POUs/00_Application/PRG_HmiStatus.TcPOU',
 'TwinCAT Patch Press/PatchPress/POUs/06_Utilities/FB_TerminalInfo.TcPOU']
# Add only task-used hardware images that were supplied after the source correction.
for _,p in routes:
 text=(ROOT/HMI/p).read_text(encoding='utf-8-sig')
 for image in re.findall(r'data-tchmi-(?:image|src)="(Images/[^"%]+)"',text):
  if (ROOT/HMI/image).exists():files.append(HMI+image)
for name in ['check_io.py','inventory.json','routes.json','symbols.json','links.json','verified-sections.json',
 'HANDOVER.md','CURRENT-MAPPING-CORRECTION.md','MOTION-CARD.md','corrected-hmi-build-result.json',
 'hmi-build-result.json','plc-build-result.json','create_motion_card.py','correct_current_pages.py',
 'build_corrected_hmi.ps1','stage_milestone.py']:
 files.append('engineering/hmi-io/'+name)
assert set(filter(None,existing)) <= set(files+['TwinCAT Patch Press/TwinCAT Patch Press.tsproj',HMI+'PatchPress_HMI.hmiproj',HMI+'Server/TcHmiSrv/TcHmiSrv.Config.default.json']), 'Preserve unrelated staged work'
git('add','--',*sorted(set(files)))

# Project file: only hardware contents, card interfaces and hardware images.
p=HMI+'PatchPress_HMI.hmiproj';text=head(p)
allowed={path.replace('/','\\') for _,path in routes}
text=re.sub(r' *<Content Include="(Contents\\Hardware\\[^"\n]+\.content)">.*?</Content>\n',lambda m:m[0] if m[1] in allowed else '',text,flags=re.S)
current=E.parse(ROOT/p)
needed=set(allowed)
for x in current.iter():
 inc=x.get('Include','')
 if '1CH_Motion_Interface_CARD.' in inc or inc in ['Images\\IO\\EL4028.png','Images\\IO\\EL3314-0092.png']:
  needed.add(inc)
included={x.get('Include') for x in E.fromstring(text).iter()}
for path in sorted(needed-included):
 text=text.replace('</Project>','  <ItemGroup><Content Include="'+path+'"><SubType>Designer</SubType></Content></ItemGroup>\n</Project>')
stage(p,text)

# Server: add exact read-only task symbol mappings without settings/schema churn.
p=HMI+'Server/TcHmiSrv/TcHmiSrv.Config.default.json'
old=json.loads(head(p));current=json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
for var in json.loads((BASE/'symbols.json').read_text()):
 key='ADS.PLC1.'+var
 old['SYMBOLS'][key]=current['SYMBOLS'][key]
 for name,g in old['USERGROUPS'].items():
  g.setdefault('SYMBOLS',{})[key]=current['USERGROUPS'][name].get('SYMBOLS',{}).get(key,0 if name=='__SystemGuests' else 1)
stage(p,json.dumps(old,indent=4,ensure_ascii=False)+'\n')

# Apply only changes since the initial IO snapshot, excluding earlier NC and
# safety serialization changes already present when the IO work began.
p='TwinCAT Patch Press/TwinCAT Patch Press.tsproj'
current=(ROOT/p).read_text(encoding='utf-8-sig')
text=head(p)
for old,new in {'Term 21 (EL4028)':'Term 20 (EL4028)','Term 20 (EL3314-0092)':'Term 21 (EL3314-0092)','Term 21 (EL6633)':'Term 22 (EL6633)'}.items():
 text=text.replace(old+'</Name>',new+'</Name>').replace(old+'</EtherCATDeviceName>',new+'</EtherCATDeviceName>').replace(old+'"',new+'"')
tree=E.fromstring(current)
inputs=re.compile(r'<Vars VarGrpType="1">.*?</Vars>',re.S).search(text,text.index('<Plc>'))
assert inputs
addition=''
for v in tree.findall('.//Plc/Project/Instance/Vars/Var'):
 name=v.findtext('Name') or ''
 if name.endswith('nTerminal_State') and '<Name>'+name+'</Name>' not in text:
  addition+='\t\t\t\t\t\t<Var>\n\t\t\t\t\t\t\t<Name>'+name+'</Name>\n\t\t\t\t\t\t\t<Type>UINT</Type>\n\t\t\t\t\t\t</Var>\n'
insert=text.rfind('\n',0,inputs.end()-7)+1
text=text[:insert]+addition+text[insert:]
for a in tree.iter('OwnerA'):
 if not a.get('Name','').startswith('TIPC'):continue
 owner=re.search(r'<OwnerA Name="'+re.escape(a.get('Name'))+r'"[^>]*>.*?</OwnerA>',text,re.S)
 assert owner
 section=owner[0]
 for b in a.findall('OwnerB'):
  for link in b.findall('Link'):
   if not link.get('VarA','').endswith('nTerminal_State'):continue
   if link.get('VarA') in section:continue
   line='\t\t\t\t<Link VarA="'+link.get('VarA')+'" VarB="InfoData^State"/>\n'
   target=re.search(r'<OwnerB Name="'+re.escape(b.get('Name'))+r'"[^>]*>.*?</OwnerB>',section,re.S)
   if target:
    insert=section.rfind('\n',0,target.end()-9)+1
    section=section[:insert]+line+section[insert:]
   else:section=section.replace('</OwnerA>','\t\t\t<OwnerB Name="'+b.get('Name')+'">\n'+line+'\t\t\t</OwnerB>\n\t\t</OwnerA>')
 text=text[:owner.start()]+section+text[owner.end():]
E.fromstring(text)
stage(p,text)
git('diff','--cached','--check')
print(git('diff','--cached','--stat').decode())
