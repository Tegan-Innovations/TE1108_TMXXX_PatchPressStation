from pathlib import Path
import json,hashlib,xml.etree.ElementTree as E,difflib
base=Path(__file__).parent;root=base.parents[1]
args=json.loads((base/'change.json').read_text(encoding='utf-8'))
before=json.loads((base/'before.json').read_text(encoding='utf-8'))
readback=json.loads((base/'readback.json').read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def canonical(text,digest):
 for _ in range(3):
  if sha(text)==digest:return text
  text=text.encode('cp1252').decode('utf-8')
 raise AssertionError('Snapshot transport/hash mismatch')
p=root/'TwinCAT Patch Press/PatchPress/POUs/03_Stations/Vision/FB_VisionStation.TcPOU'
node=E.parse(p).find(".//Method[@Name='Cyclic']")
saved=node.findtext('Implementation/ST')
assert saved==canonical(args['newImplementation'],readback['implementationHash'])
assert sha(saved)==readback['implementationHash']
assert node.findtext('Declaration')==before['declaration']
old=canonical(before['implementation'],before['implementationHash'])
delta=list(difflib.unified_diff(old.splitlines(),saved.splitlines()))
assert sum(x.startswith('@@') for x in delta)==2
assert 'IF usiStepInternal = 70 THEN' in saved and 'PT := T#1S' in saved
print('PASS exact saved/XAE readback, unchanged method declaration, exactly two intended source hunks')
