"""Execute the saved Vision Cyclic ST with scripted endpoint/timer feedback."""
from pathlib import Path
import sys, re, json, xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'engineering/el6910'))
from st_function_test import Engine,Parser,Timer
path=ROOT/'TwinCAT Patch Press/PatchPress/POUs/03_Stations/Vision/FB_VisionStation.TcPOU'
t=E.parse(path)
raw=next(m.findtext('Implementation/ST') for m in t.findall('.//Method') if m.get('Name')=='Cyclic')
raw=re.sub(r'\(\*.*?\*\)','',raw,flags=re.S)
# Two independent timers retain their own IN/Q; only syntax is normalized.
raw=raw.replace('tonCameraTriggerDelay[1]','tonCameraTriggerDelay1').replace('tonCameraTriggerDelay[2]','tonCameraTriggerDelay2')
for key,value in {'Disabled':0,'Homing':10,'Ready':20,'Processing':30,'Complete':40,'Fault':100}.items():
 raw=raw.replace('E_PatchStationState.'+key,str(value))
for key,value in {'None':0,'Pass':1,'Fail':2}.items():raw=raw.replace('E_ProcessResultCode.'+key,str(value))
code=Parser(raw).block()
class Ton(Timer):
 def __init__(self):
  super().__init__();self.update(IN=False,PT=0);self.last_frame=-1
 def call(self,a):
  self.update(a)
  if not self['IN']:self.elapsed=0
  elif self.last_frame!=frame[0]:self.elapsed+=10
  self.last_frame=frame[0];self['Q']=bool(self['IN'] and self.elapsed>=self['PT'])
class Edge(Timer):
 def __init__(self):super().__init__();self.old=False
 def call(self,a):self['Q']=bool(a['CLK'] and not self.old);self.old=bool(a['CLK'])
frame=[0]
Engine.cache['VISION_TEST']=({},code)
def state(step=70,mode=30):
 e=Engine('VISION_TEST',{})
 names=set(re.findall(r'\b[A-Za-z_]\w*\b',raw))
 e.v.update({n:0 for n in names})
 e.v.update({
  'E_PatchStationState':{'Disabled':0,'Homing':10,'Ready':20,'Processing':30,'Complete':40,'Fault':100},
  'E_ProcessResultCode':{'None':0,'Pass':1,'Fail':2},
  'eStateInternal':mode,'usiStepInternal':step,
  'bEnableInternal':True,'bCommissionedInternal':True,'bSafetyOkInternal':True,'bSupervisionEnableInternal':True,
  'bHorizontalBackInternal':True,'bVerticalUpInternal':True,'bGripOpenedInternal':True,
  'bRotate0Internal':True,'bRotate0RawInternal':True,
  'nCurrentProgramNumberInternal':0,'tMoveTimeout':5000,'tStepDelay':0,'tToolingSensorConflict':300,
  'stProcessSettingsInternal':{'udiMovingTriggerDelayMs':100},
  'stResultInternal':{'bValid':False,'bPassed':False,'eCode':0,'udiFaultCode':0,'udiAlertCode':0,'sDetail':'','CameraResults':{}},
  'nVisionResultsInternal':{'aInspectionCompleted':[False]+[True]*4,'aInspectionPassed':[False]+[True]*4},
 })
 for name in names:
  if name.startswith('ton'):e.v[name]=Ton()
 e.v['rtRotate0Raw']=Edge()
 return e
def scan(e):frame[0]+=1;e.execute(code);return e.v
def output(v):return {k:x for k,x in v.items() if k.endswith('RequestInternal')}

# Retired inputs cannot alter HOME, with neither input, either input or both high.
import itertools
for bits in itertools.product([False,True],repeat=4):
 e=state(70,10)
 e.v.update(zip(['bSupportRetractedInternal','bSupportExtendedInternal','bLimitOffInternal','bLimitOnInternal'],bits))
 v=scan(e);assert v['bHomeInternal'] and v['bReadyInternal'] and v['eStateInternal']==20

# Both former intermediate steps wait for actual DOWN, never for both sensors OFF.
for step in [70,140]:
 e=state(step);e.v.update(bHorizontalBackInternal=False,bHorizontalFrontInternal=True,bVerticalUpInternal=False,bVerticalDownInternal=False,bGripOpenedInternal=False,bGripClosedInternal=True)
 v=scan(e);assert v['usiStepInternal']==step and not v['bStepTargetReached'] and v['bVerticalDownRequestInternal']
 e.v['bVerticalDownInternal']=True
 # PBUP mounting (70) now holds confirmed DOWN for 1 s; replacement is unchanged.
 for _ in range(110 if step==70 else 1):
  v=scan(e)
  if v['usiStepInternal']==step+10:break
 assert v['usiStepInternal']==step+10 and v['bStepTargetReached'] and not v['bVerticalDownRequestInternal']
 # A sustained contradictory UP/DOWN pair is still a fault.
 e=state(step);e.v.update(bVerticalDownInternal=True,tToolingSensorConflict=0)
 v=scan(e);assert v['eStateInternal']==100 and v['bFaultInternal']

# Release must not complete if DOWN is lost, even with the gripper open.
e=state(150);e.v.update(bVerticalUpInternal=False,bVerticalDownInternal=False,bGripOpenedInternal=False,bGripClosedInternal=True)
v=scan(e);assert v['usiStepInternal']==150 and not v['bStepTargetReached'] and not v['bGripOpenRequestInternal']
e.v['bVerticalDownInternal']=True
v=scan(e);assert v['bGripOpenRequestInternal'] and v['usiStepInternal']==150
e.v.update(bGripOpenedInternal=True,bGripClosedInternal=False)
v=scan(e);assert v['usiStepInternal']==160 and v['bStepTargetReached']

# Homing skips the two removed actuator-only steps, retaining feedback sequencing.
for start,target in [(10,30),(40,60)]:
 e=state(start,10);e.v.update(bHorizontalBackInternal=False,bHorizontalFrontInternal=True)
 v=scan(e);assert v['usiStepInternal']==target,(start,v['usiStepInternal'])

# Retained HOME feedback, timeouts, Stop recovery and safety loss remain effective.
e=state(70,10);e.v['bVerticalUpInternal']=False
v=scan(e);assert not v['bHomeInternal'] and not v['bReadyInternal']
e=state(70);e.v.update(bVerticalUpInternal=False,bStopRequestInternal=True)
v=scan(e);assert v['eStateInternal']==10 and v['usiStepInternal']==0
v=scan(e);assert v['eStateInternal']==10 and v['usiStepInternal']==10 and v['bVerticalUpRequestInternal']
e=state(140);e.v['bSafetyOkInternal']=False
v=scan(e);assert v['eStateInternal']==0 and not any(output(v).values())
e=state(70);e.v.update(bVerticalUpInternal=False,tMoveTimeout=0)
v=scan(e);assert v['eStateInternal']==100 and v['stResultInternal']['udiFaultCode']==10

# Motion interlocks still reject horizontal/rotation requests while vertical is DOWN.
e=state(120);e.v.update(bVerticalUpInternal=False,bVerticalDownInternal=True,bRotate0Internal=False)
v=scan(e);assert not v['bRotate0RequestInternal'] and not v['bHorizontalFrontRequestInternal']

# Reset uses HOME formed solely from retained feedback and invalidates camera results.
reset=next(m.findtext('Implementation/ST') for m in t.findall('.//Method') if m.get('Name')=='RequestReset')
reset=reset.replace('tonCameraTriggerDelay[1]','tonCameraTriggerDelay1').replace('tonCameraTriggerDelay[2]','tonCameraTriggerDelay2')
for key,value in {'Disabled':0,'Homing':10,'Ready':20,'Processing':30,'Complete':40,'Fault':100}.items():reset=reset.replace('E_PatchStationState.'+key,str(value))
reset=reset.replace('E_ProcessResultCode.None','0')
e=state(0,100);scan(e)
e.v['stEmptyVisionResults']={'aInspectionCompleted':[False]*5,'aInspectionPassed':[False]*5}
e.execute(Parser(reset).block())
assert e.v['eStateInternal']==20 and e.v['usiStepInternal']==0
assert not e.v['stResultInternal']['bValid'] and not any(e.v['nVisionResultsInternal']['aInspectionCompleted'])
print('PASS saved Vision ST: all retired input combinations, DOWN at steps 70/140/150, HOME routing, retained conflicts/timeouts, Stop, safety loss and UP motion interlocks')
