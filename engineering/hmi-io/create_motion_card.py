"""Generate native motion diagnostics from existing card conventions and NC symbols."""
from pathlib import Path
import json, re, html, xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).parent
HMI=ROOT/'TwinCAT Patch Press/PatchPress_HMI'
UC=HMI/'Contents/UserControl'
NAME='1CH_Motion_Interface_CARD'
def write(p,s):
 with p.open('w',encoding='utf-8',newline='\r\n') as f:f.write(s)
def pp(s):return '%pp%'+s+'%/pp%'
def tag(id,kind,x,y,w,h,**attrs):
 a={'id':id,'data-tchmi-type':'TcHmi.Controls.'+kind,'data-tchmi-left':x,'data-tchmi-top':y,'data-tchmi-width':w,'data-tchmi-height':h}
 a.update({'data-tchmi-'+k.replace('_','-'):v for k,v in attrs.items()})
 return '<div '+' '.join(k+'="'+html.escape(str(v),quote=True)+'"' for k,v in a.items())+'></div>\n'
fields=[
 ('ActualPosition','Actual position (axis units)','Axis.NcToPlc.ActPos','LREAL'),
 ('ActualVelocity','Actual velocity (axis units/s)','Axis.NcToPlc.ActVelo','LREAL'),
 ('ActualTorque','Actual torque (NC reported units)','Axis.NcToPlc.ActTorque','LREAL'),
 ('PositionDifference','Position difference (axis units)','Axis.NcToPlc.PosDiff','LREAL'),
 ('SetPosition','Set position (axis units)','Axis.NcToPlc.SetPos','LREAL'),
 ('SetVelocity','Set velocity (axis units/s)','Axis.NcToPlc.SetVelo','LREAL'),
 ('TargetPosition','Target position (axis units)','Axis.NcToPlc.TargetPos','LREAL'),
 ('AxisId','NC axis ID','Axis.NcToPlc.AxisId','UDINT'),
 ('Standstill','Application standstill','bStandstill','BOOL'),
 ('NcErrorCode','NC axis error code (decimal)','Axis.NcToPlc.ErrorCode','UDINT'),
 ('AxisState','NC movement state','Axis.NcToPlc.AxisState','UDINT'),
 ('HomingState','NC homing state','Axis.NcToPlc.HomingState','UDINT'),
 ('AxisError','Application axis error','bError','BOOL'),
 ('ApplicationErrorId','Application error ID (decimal)','udiErrorId','UDINT'),
 ('Enabled','Application enabled','bEnabled','BOOL'),
 ('Operational','Application operational','bOperational','BOOL'),
 ('Homed','Application homed','bHomed','BOOL'),
 ('Moving','Application moving','bMoving','BOOL'),
]
template=(UC/'8CH_Analog_Input_CARD.usercontrol').read_text()
header=re.search(r'<div id="TcHmiTextblock_867".*?</div>',template,re.S)[0]
led=re.search(r'<div id="TcHmiEllipse_26".*?</div>',template,re.S)[0]
image=re.search(r'<div id="TcHmiImage_11".*?</div>',template,re.S)[0]
body='<div id="MotionCard" data-tchmi-type="TcHmi.Controls.System.TcHmiUserControl" data-tchmi-width="1080" data-tchmi-height="480">\n'+header+led+image
body+=tag('MotionAxisName','Beckhoff.TcHmiTextblock',158,65,880,30,text=pp('AxisName'),text_font_size=20)
for i,(prop,label,field,typ) in enumerate(fields):
 x=158+(i//9)*460;y=102+(i%9)*37
 body+=tag('MotionLabel'+prop,'Beckhoff.TcHmiTextblock',x,y,285,30,text=label,text_font_size=15,text_vertical_alignment='Center')
 if typ=='BOOL':
  body+=tag('MotionValue'+prop,'Beckhoff.TcHmiTextblock',x+290,y,145,30,text="%f%"+pp(prop)+" ? 'TRUE' : 'FALSE'%/f%",text_font_size=15,text_vertical_alignment='Center')
 else:
  body+=tag('MotionValue'+prop,'Beckhoff.TcHmiNumericInput',x+290,y,145,30,value=pp(prop),is_enabled='False',decimal_digits=3 if typ=='LREAL' else 0,value_font_size=15)
body+=tag('MotionUnits','Beckhoff.TcHmiTextblock',158,442,895,30,text='NC units follow axis configuration; torque is not converted. Diagnostics only.',text_font_size=13)
write(UC/(NAME+'.usercontrol'),body+'</div>\n')
config=json.loads((UC/'8CH_Analog_Input_CARD.usercontrol.json').read_text())
params=[p for p in config['parameters'] if p['propertyName'] in ['Image','State_string','CardOperational']]
for prop,typ in [('AxisName','String')]+[(p,t) for p,l,f,t in fields]:
 params.append({'name':'data-tchmi-'+prop.lower(),'displayName':prop,'propertyName':prop,'propertySetterName':'set'+prop,'propertyGetterName':'get'+prop,'type':'tchmi:general#/definitions/'+typ,'bindable':True,'visible':True,'heritable':True,'readOnly':False,'requiredOnCompile':False,'allowSymbolExpressionsInObject':False,'description':'Read-only motion diagnostic input'})
config['parameters']=params;config['description']='Single-axis NC diagnostics; no motion commands.'
write(UC/(NAME+'.usercontrol.json'),json.dumps(config,indent=2)+'\n')
symbols=json.loads((BASE/'symbols.json').read_text())
for var in list(symbols):
 if var.startswith('GVL_Motion.') and var.rsplit('.',1)[-1] in ['lrActPosition','lrActVelocity','lrActTorque']:
  del symbols[var]
tmc=E.parse(ROOT/'TwinCAT Patch Press/PatchPress/PatchPress.tmc')
types={d.findtext('Name'):{s.findtext('Name'):s.findtext('Type') for s in d.findall('SubItem')} for d in tmc.iter('DataType')}
for n,axis,title in [(15,'AxisDriveMotor','Reel Payout'),(16,'AxisPatchFeedRollMotor','Material Index'),(17,'AxisWasteRollMotor','Slack')]:
 p=HMI/f'Contents/Hardware/T{n}_EL7201.content';old=p.read_text()
 attrs={k:v for k,v in re.findall(r'(data-tchmi-(?:image|state_string|cardoperational))="([^"]+)"',old)}
 attrs['data-tchmi-axisname']=f'Term {n} - EL7201 - {title}'
 for prop,label,field,typ in fields:
  actual='ST_Axis'
  for member in field.split('.'):actual=types[actual][member]
  assert actual==typ,(field,actual,typ)
  var='GVL_Motion.'+axis+'.'+field;symbols[var]=typ
  attrs['data-tchmi-'+prop.lower()]='%s%ADS.PLC1.'+var+'%/s%'
 host=tag(f'Card_T{n}_EL7201','System.TcHmiUserControlHost',0,0,1080,480,target_user_control='Contents/UserControl/'+NAME+'.usercontrol')
 host=host.replace('></div>',' '+' '.join(k+'="'+html.escape(v,quote=True)+'"' for k,v in attrs.items())+'></div>')
 write(p,f'<div id="IO_T{n}_EL7201" data-tchmi-type="TcHmi.Controls.System.TcHmiContent" data-tchmi-width="1080" data-tchmi-height="480">\n'+host+'</div>\n')
project=HMI/'PatchPress_HMI.hmiproj';s=project.read_text(encoding='utf-8-sig')
for ext in ['.usercontrol','.usercontrol.json']:
 path='Contents\\UserControl\\'+NAME+ext
 if 'Include="'+path+'"' not in s:s=s.replace('</Project>','<ItemGroup><Content Include="'+path+'"><SubType>Designer</SubType></Content></ItemGroup>\n</Project>')
write(project,s)
server=HMI/'Server/TcHmiSrv/TcHmiSrv.Config.default.json';d=json.loads(server.read_text(encoding='utf-8-sig'))
for var,typ in symbols.items():
 key='ADS.PLC1.'+var
 if key not in d['SYMBOLS']:
  d['SYMBOLS'][key]={'ACCESS':1,'DOMAIN':'ADS','DYNAMIC':True,'MAPPING':'PLC1::'+var.replace('.','::'),'SCHEMA':{'allOf':[{'$ref':'tchmi:general#/definitions/'+typ}]},'USEMAPPING':True}
  for name,g in d['USERGROUPS'].items():g.setdefault('SYMBOLS',{})[key]=0 if name=='__SystemGuests' else 1
write(server,json.dumps(d,indent=4,ensure_ascii=False)+'\n')
(BASE/'symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')
print('Created native motion card and bound 18 verified diagnostic fields on each of three EL7201 pages.')
