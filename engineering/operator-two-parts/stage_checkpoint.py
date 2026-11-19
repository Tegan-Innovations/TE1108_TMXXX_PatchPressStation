"""Stage only the reviewed two-component loading checkpoint."""
from pathlib import Path
import json, subprocess
def git(*args):return subprocess.check_output(['git',*args])
assert git('branch','--show-current').decode().strip()=='Patch_Feeding_Commissioning'
assert not git('diff','--cached','--name-only').strip(),'Preserve existing staged work'
base=Path('TwinCAT Patch Press/PatchPress')
files=[]
for s in json.loads(Path('engineering/operator-two-parts/verified-sections.json').read_text()):
 parts=s['path'].split('^')[3:]
 for end in range(len(parts),0,-1):
  matches=[base.joinpath(*parts[:end]).with_suffix(ext) for ext in ['.TcPOU','.TcDUT']]
  found=next((p for p in matches if p.exists()),None)
  if found:break
 assert found,s['path']
 if found.as_posix() not in files:files.append(found.as_posix())
files += ['TwinCAT Patch Press/PatchPress_HMI/Contents/Screens/Main.content',
 'TwinCAT Patch Press/PatchPress_HMI/Server/TcHmiSrv/TcHmiSrv.Config.default.json']
files += ['engineering/operator-two-parts/'+p for p in ['HANDOVER.md','check_two_parts.py','verify_saved.py','verified-sections.json','stage_checkpoint.py']]
subprocess.run(['git','add','--',*files],check=True)
assert set(git('diff','--cached','--name-only').decode().splitlines())==set(files)
subprocess.run(['git','diff','--cached','--check'],check=True)
subprocess.run(['git','diff','--cached','--stat'],check=True)
