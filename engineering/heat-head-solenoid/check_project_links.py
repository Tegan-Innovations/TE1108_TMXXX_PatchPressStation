from pathlib import Path
import json,xml.etree.ElementTree as E
B=Path(__file__).parent;R=B.resolve().parents[1]
before=json.loads((R/'engineering/hmi-io/links.json').read_text(encoding='utf-8'))
t=E.parse(R/'TwinCAT Patch Press/TwinCAT Patch Press.tsproj')
after=[{'a':a.attrib,'b':b.attrib,'link':l.attrib} for a in t.iter('OwnerA') for b in a.findall('OwnerB') for l in b.findall('Link')]
def canonical(x):
 x=json.loads(json.dumps(x))
 for old,new in {'Term 21 (EL4028)':'Term 20 (EL4028)','Term 20 (EL3314-0092)':'Term 21 (EL3314-0092)','Term 21 (EL6633)':'Term 22 (EL6633)'}.items():
  if x['b']['Name'].endswith('^'+old):x['b']['Name']=x['b']['Name'].rsplit('^',1)[0]+'^'+new
 return json.dumps(x,sort_keys=True)
missing=[json.loads(x) for x in {canonical(x) for x in before}-{canonical(x) for x in after}]
(B/'missing-baseline-links.json').write_text(json.dumps(missing,indent=2),encoding='utf-8')
for x in missing:print(x['a']['Name'],x['b']['Name'],x['link'])
print('Missing exact historical link records:',len(missing),'; no project configuration was edited by this checker')
