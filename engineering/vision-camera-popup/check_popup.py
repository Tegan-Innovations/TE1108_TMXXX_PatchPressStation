from pathlib import Path
import json,re,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2];base=Path(__file__).parent
hmi=root/'TwinCAT Patch Press/PatchPress_HMI'
p=hmi/'Contents/Screens/ManualTabs/VisionTab.content'
s=p.read_text(encoding='utf-8');before=(base/'VisionTab.before.content').read_text(encoding='utf-8')
def control(name,text=s):return re.search(r'<div id="'+name+r'"[^>]*>.*?</div>',text,re.S)[0]
button=control('TcHmiButton_CameraOpenInterface');popup=control('TcHmiPopup_VisionCamera')
def data(block,name):return json.loads(re.search(r'<script data-tchmi-target-attribute="'+name+r'"[^>]*>(.*?)</script>',block,re.S)[1])
actions=data(button,'data-tchmi-trigger')
assert len(actions)==1 and actions[0]['event'].endswith('.onPressed')
assert actions[0]['actions']==[{'objectType':'ControlApiFunction','active':True,'control':'TcHmiPopup_VisionCamera','fn':'open','asyncWait':True}]
attrs=dict(re.findall(r'([\w-]+)="([^"]*)"',popup))
assert attrs['data-tchmi-type']=='TcHmi.Controls.System.TcHmiPopup'
assert attrs['data-tchmi-target-file-host-preload']=='False'
assert attrs['data-tchmi-target-file-host-keep-alive']=='False'
assert attrs['data-tchmi-modal']=='True' and attrs['data-tchmi-close-on-background']=='False'
target=data(popup,'data-tchmi-target-file')['path']
assert target=='Contents/Screens/popups/Content_Popup_VisionCamera.content'
assert data(popup,'data-tchmi-buttons')[0]['keepPopupOpen'] is False
content=(hmi/target).read_text(encoding='utf-8')
frame=control('TcHmiIFrame_VisionCameraWeb',content)
assert 'data-tchmi-src="http://192.168.0.30/"' in frame
assert 'data-tchmi-width="100" data-tchmi-width-unit="%"' in frame
assert 'data-tchmi-height="100" data-tchmi-height-unit="%"' in frame
assert '192.168.0.30' not in s and 'TcHmiIFrame_CameraImageTriggerSelection' not in s
old=re.search(r'<div id="TcHmiIFrame_CameraImageTriggerSelection"[^>]*></div>',before)[0]
assert s.replace(button+'\n'+popup,old)==before,'Other VisionTab layout/bindings changed'
tree=E.parse(hmi/'PatchPress_HMI.hmiproj');ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
assert sum(x.get('Include','').replace('\\','/')==target for x in tree.findall('.//m:Content',ns))==1
for text in [s,content]:
 ids=re.findall(r'<div\b[^>]*\bid="([^"]+)"',text);assert len(ids)==len(set(ids))
 for script in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',text,re.S):json.loads(script)
framework=root/'Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi'
description=json.loads((framework/'Controls/System/TcHmiPopup/Description.json').read_text(encoding='utf-8-sig'))
names={a['name'] for a in description['attributes']}
assert {'data-tchmi-target-file','data-tchmi-target-file-host-preload','data-tchmi-target-file-host-keep-alive','data-tchmi-buttons'}<=names
native=(framework/'dist/Controls/System/TcHmiPopup/TcHmiPopup.esm.js').read_text(encoding='utf-8')
assert 'this.__targetFileHostPreload&&this.__buildFileHost()' in native
assert 'this.__fileHost.destroy(),this.__fileHost=void 0),EventProvider.raise(this.__id+".onClosed"' in native
assert '__detach(){super.__detach(),this.__popup?.abort({result:null})' in native
print('PASS native click-only popup, no preload/keep-alive, close/detach disposal, registered iframe content, modal Close button, and exact preservation of other bindings/layout')
