"""Validate the exact index contents in a temporary source snapshot."""
from pathlib import Path
import subprocess as S, tempfile, json, xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
def git(*a):return S.check_output(['git',*a],cwd=ROOT)
files=git('ls-files','-z').decode().strip('\0').split('\0')
with tempfile.TemporaryDirectory(prefix='patch-io-index-') as directory:
 dest=Path(directory)
 for p in files:
  if p.startswith('TwinCAT Patch Press/PatchPress/') and p.endswith(('.TcPOU','.TcDUT','.TcGVL','.plcproj')) or p.startswith('TwinCAT Patch Press/PatchPress_HMI/Contents/') and p.endswith(('.content','.usercontrol','.json')) or p.startswith('TwinCAT Patch Press/PatchPress_HMI/Images/') or p in ['TwinCAT Patch Press/TwinCAT Patch Press.tsproj','TwinCAT Patch Press/PatchPress_HMI/PatchPress_HMI.hmiproj','TwinCAT Patch Press/PatchPress_HMI/Server/TcHmiSrv/TcHmiSrv.Config.default.json'] or p.startswith('engineering/hmi-io/') or p=='engineering/patch-feeding/implementation/st_branch_runner.py':
   target=dest/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(git('show',':'+p))
 # Generated TMC is type evidence from the existing offline build, not source.
 p='TwinCAT Patch Press/PatchPress/PatchPress.tmc';(dest/p).write_bytes((ROOT/p).read_bytes())
 p='TwinCAT Patch Press/TwinCAT Patch Press.tsproj'
 old=E.fromstring(git('show','HEAD:'+p));new=E.parse(dest/p)
 baseline=[{'a':a.attrib,'b':b.attrib,'link':l.attrib} for a in old.iter('OwnerA') for b in a.findall('OwnerB') for l in b.findall('Link')]
 (dest/'engineering/hmi-io/links.json').write_text(json.dumps(baseline))
 S.run(['python',str(dest/'engineering/hmi-io/check_io.py')],check=True)
 def links(tree):
  return {(a.get('Name'),b.get('Name'),tuple(sorted(l.attrib.items()))) for a in tree.iter('OwnerA') for b in a.findall('OwnerB') for l in b.findall('Link')}
 def normalize(items):
  rename={'Term 21 (EL4028)':'Term 20 (EL4028)','Term 20 (EL3314-0092)':'Term 21 (EL3314-0092)','Term 21 (EL6633)':'Term 22 (EL6633)'}
  return {(a,next((b.rsplit('^',1)[0]+'^'+v for k,v in rename.items() if b.endswith('^'+k)),b),l) for a,b,l in items}
 before=normalize(links(old));after=links(new)
 assert before<=after,'Original NC/process/safety links changed'
 added=after-before
 assert len(added)==17
 assert all(dict(l)['VarB']=='InfoData^State' and dict(l)['VarA'].endswith('nTerminal_State') for a,b,l in added)
 print('PASS exact staged source snapshot and all original HEAD process/NC/safety links; only 17 diagnostic links added')
