"""Correct HMI physical terminal identities using saved mappings; no PLC writes."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).parent
HMI = ROOT / 'TwinCAT Patch Press/PatchPress_HMI'

def write(path, text):
    with path.open('w', encoding='utf-8', newline='\r\n') as stream:
        stream.write(text)

routes = json.loads((BASE / 'routes.json').read_text())
changes = {
    'T21_EL4028': ('T20_EL4028', 'Term 20 (EL4028)'),
    'T20_EL3314': ('T21_EL3314', 'Term 21 (EL3314-0092)'),
    'T21_EL6633': ('T22_EL6633', 'Term 22 (EL6633)'),
}
navpath = HMI / 'Contents/IOs/Main_IOs.content'
nav = navpath.read_text(encoding='utf-8-sig')
for route in routes:
    old = Path(route[1]).stem
    if old not in changes:
        continue
    new, title = changes[old]
    source = (HMI / route[1]).read_text(encoding='utf-8-sig')
    # Page/control IDs follow physical numbering; PLC symbol names remain exact.
    source = source.replace(old, new)
    if old == 'T21_EL6633':
        source = re.sub(r'<div\b[^>]*data-tchmi-type="TcHmi.Controls.Beckhoff.TcHmiImage"[^>]*>\s*</div>', '', source)
    write(HMI / 'Contents/Hardware' / (new + '.content'), source)
    newpath = 'Contents/Hardware/' + new + '.content'
    nav = nav.replace(route[0], title).replace(route[1], newpath)
    route[:] = [title, newpath]
write(navpath, nav)

# Exclude unused Silicone hardware pages and superseded duplicate terminal pages.
# Keep their files as historical source; they are not shipped in the HMI project.
project = HMI / 'PatchPress_HMI.hmiproj'
text = project.read_text(encoding='utf-8-sig')
allowed = {path.replace('/', '\\') for _, path in routes}
def content(match):
    return match[0] if match[1] in allowed else ''
text = re.sub(r'<Content Include="(Contents\\Hardware\\[^"\n]+)">.*?</Content>', content, text, flags=re.S)
included = {x.get('Include') for x in ET.fromstring(text).iter()}
extra = ''.join('<ItemGroup><Content Include="' + path + '"><SubType>Designer</SubType></Content></ItemGroup>\n' for path in sorted(allowed - included))
text = text.replace('</Project>', extra + '</Project>')
text = re.sub(r'^ +\n', '', text, flags=re.M)
text = re.sub(r'^ *<ItemGroup></ItemGroup>\n', '', text, flags=re.M)
write(project, text)
(BASE / 'routes.json').write_text(json.dumps(routes, indent=2) + '\n')

inventory = json.loads((BASE / 'inventory.json').read_text())
tree = ET.parse(ROOT / 'TwinCAT Patch Press/TwinCAT Patch Press.tsproj')
for item in inventory:
    if item['key'] not in changes:
        continue
    item['key'], item['name'] = changes[item['key']]
    item['path'] = item['path'].rsplit('^', 1)[0] + '^' + item['name']
    assert any(b.findtext('Name') == item['name'] for b in tree.iter('Box'))
(BASE / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
print('Corrected physical terminal pages/navigation; excluded obsolete hardware content references.')
