"""Compare saved PLC sections with the final XAE readback; no runtime access."""
from pathlib import Path
import json, xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
plc=root/'TwinCAT Patch Press/PatchPress'
def normal(s):
    return (s or '').replace('\r\n','\n').replace('Â°','°').strip()
for s in json.loads((Path(__file__).parent/'verified-sections.json').read_text(encoding='utf-8')):
    parts=s['path'].split('^')[3:]
    found=None
    for end in range(len(parts),0,-1):
        for ext in ['.TcPOU','.TcDUT']:
            p=plc.joinpath(*parts[:end]).with_suffix(ext)
            if p.exists():found=(p,end);break
        if found:break
    assert found,s['path']
    p,end=found;t=E.parse(p);o=t.getroot()[0]
    for member in parts[end:]:o=next(m for m in o if m.get('Name')==member)
    assert normal(o.findtext('Declaration'))==normal(s['declaration']),str(p)+' declaration'
    assert normal(o.findtext('Implementation/ST'))==normal(s['implementation']),str(p)+' implementation'
print('PASS all 16 saved PLC sections match final XAE readback')
