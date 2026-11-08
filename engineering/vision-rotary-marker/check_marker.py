"""Execute saved ST marker and endpoint branches with a 10 ms virtual scan clock."""
from pathlib import Path
import re,runpy
import xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
h=runpy.run_path(str(root/'engineering/patch-feeding/implementation/st_branch_runner.py'))
plc=root/'TwinCAT Patch Press/PatchPress'
def method(path,name):
 t=E.parse(plc/path)
 return next(x.findtext('Implementation/ST') for x in t.findall('.//Method') if x.get('Name')==name)
vision=method('POUs/03_Stations/Vision/FB_VisionStation.TcPOU','Cyclic')
machine=method('POUs/01_Core/Machine/FB_IndexedPatchPressMachine.TcPOU','Cyclic')
prefix=vision[:vision.index('// Rearm inspection 2')]
request=vision[vision.index('bTriggerRequestInternal :='):vision.index('bGetResultsRequestInternal :=')]
endpoint=machine[machine.index('tonVisionRotate0Confirm('):machine.index('bVisionRotate180Confirmed := tonVisionRotate180Confirm.Q;')+len('bVisionRotate180Confirmed := tonVisionRotate180Confirm.Q;')]
def strip(s):
 # UDINT milliseconds and TIME milliseconds have the same numeric test representation.
 return re.sub(r'UDINT_TO_TIME\(([^()]+)\)',r'\1',re.sub(r'//[^\n]*','',s))
prefix,request,endpoint=map(strip,[prefix,request,endpoint])
calls=re.compile(r'\b((?:ton|rt)\w+)\((.*?)\);',re.S)
class Runner:
 def __init__(self,code):
  self.v={k:0 for k in re.findall(h['var'],code)};self.t=0;self.timers={};self.edges={}
  self.v.update({'E_PatchStationState.Processing':30,'E_PatchStationState.Ready':20,
    'tTakingPictureWHileRotating':100,'tFlipDepartureFilter':20,'tVisionRotaryConfirm':1000,
    'stProcessSettingsInternal.udiMovingTriggerDelayMs':100})
 def execute(self,code):
  pos=0
  for m in calls.finditer(code):
   h['execute'](code[pos:m.start()],self.v);name,args=m.groups()
   if name.startswith('rt'):
    value=bool(h['expression'](args.split(':=',1)[1],self.v))
    self.v[name+'.Q']=value and not self.edges.get(name,False);self.edges[name]=value
   else:
    m2=re.fullmatch(r'\s*IN\s*:=\s*(.*?)\s*,\s*PT\s*:=\s*(.*?)\s*',args,re.S);assert m2,args
    value=bool(h['expression'](m2[1],self.v));pt=h['expression'](m2[2],self.v)
    if not value:self.timers.pop(name,None)
    elif name not in self.timers:self.timers[name]=self.t
    self.v[name+'.Q']=value and self.t-self.timers[name]>=pt
   pos=m.end()
  h['execute'](code[pos:],self.v)
 def scan(self,code,**kw):self.v.update(kw);self.execute(code);self.t+=10

r=Runner(endpoint)
r.v.update({'bVisionCommissioned':True,'stInputs.stSafety.bSafetyOk':True,'GVL_Safety.bAirSupplySafe':True})
for _ in range(101):r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':True})
assert not r.v['bVisionRotate0Confirmed'],'unreferenced high signal alone cannot establish HOME before commanding 0'
for _ in range(100):r.scan(endpoint,**{'bVisionRotate0CommandPrevious':True})
assert not r.v['bVisionRotate0Confirmed']
r.scan(endpoint);assert r.v['bVisionRotate0Confirmed']
r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':False});assert not r.v['bVisionRotate0Confirmed']
for _ in range(30):r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':True})
r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':False});assert not r.v['bVisionRotate0Confirmed'],'90 pulse cannot qualify endpoint'
for _ in range(101):r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':True,'bVisionRotate180CommandPrevious':True})
assert not r.v['bVisionRotate0Confirmed'],'outbound command excludes false 0'
for _ in range(101):r.scan(endpoint,**{'stInputs.bRotaryGripperPick0':False,'stInputs.bRotaryGripperPlace180':True,'bVisionRotate180CommandPrevious':False,'bVisionRotate0CommandPrevious':False})
assert r.v['bVisionRotate180Confirmed']
r.scan(endpoint,**{'bVisionRotate0CommandPrevious':True});assert not r.v['bVisionRotate180Confirmed']
for _ in range(101):r.scan(endpoint,**{'stInputs.bRotaryGripperPlace180':False,'stInputs.bRotaryGripperPick0':True})
assert r.v['bVisionRotate0Confirmed'],'return qualifies final sustained 0'
r.scan(endpoint,**{'stInputs.bRotaryGripperPlace180':True});assert not r.v['bVisionRotate0Confirmed'] and not r.v['bVisionRotate180Confirmed']
print('PASS 1 s endpoints, transient 90 pulse, direction exclusion, final return and opposing raw sensors')

code=prefix+request
def setup():
 r=Runner(code);r.v.update({'bEnableInternal':True,'bCommissionedInternal':True,'bSafetyOkInternal':True,
 'eStateInternal':20,'usiStepInternal':0,'bRotate0RawInternal':True,'bRotate0Internal':True,'nCurrentProgramNumberInternal':1})
 r.scan(code);r.scan(code,eStateInternal=30,usiStepInternal=100)
 return r
def depart(r):
 for _ in range(3):r.scan(code,bRotate0RawInternal=False,bRotate0Internal=False)
 assert r.v['bFlipLeft0']
r=setup()
assert not r.v['bFlip90Seen'] and not r.v['bTriggerRequestInternal'],'initial 0 cannot be marker'
depart(r);r.scan(code,bRotate0RawInternal=True)
assert r.v['bFlip90Seen'];start=r.timers['tonTakingPictureWHileRotating']
for _ in range(5):r.scan(code,bRotate0RawInternal=not r.v['bRotate0RawInternal'])
assert r.timers['tonTakingPictureWHileRotating']==start and not r.v['bTriggerRequestInternal']
for _ in range(5):r.scan(code,bRotate0RawInternal=False)
assert r.v['bTriggerRequestInternal'] and r.v['bFlipTriggerLatched']
for _ in range(20):r.scan(code,bRotate0RawInternal=not r.v['bRotate0RawInternal'])
assert r.v['bTriggerRequestInternal'] and r.timers['tonTakingPictureWHileRotating']==start
r.scan(code,bCameraTriggerAcceptedInternal=True,bRotate180RawInternal=True)
assert r.v['bFlipCaptureAccepted'] and not r.v['bFlipCaptureWindowMissed'] and r.v['bTriggerRequestInternal']
r.scan(code,nCurrentProgramNumberInternal=2);assert not r.v['bTriggerRequestInternal']
r.scan(code,usiStepInternal=110);assert not r.v['bFlipTriggerLatched'] and not r.v['bFlip90Seen']
print('PASS first marker latches delay, duplicate pulses cannot restart/retrigger, ACK/result held, exit rearms')
for event in ['missing_marker','window_too_short','camera_not_ready','wrong_program']:
 r=setup();depart(r)
 if event!='missing_marker':r.scan(code,bRotate0RawInternal=True)
 if event in ['camera_not_ready','wrong_program']:
  if event=='wrong_program':r.v['nCurrentProgramNumberInternal']=2
  for _ in range(10):r.scan(code,bRotate0RawInternal=False)
 r.scan(code,bRotate180RawInternal=True)
 assert r.v['bFlipCaptureWindowMissed'] and not r.v['bTriggerRequestInternal'],event
for cancelled in ['bSafetyOkInternal','bEnableInternal','bCommissionedInternal']:
 r=setup();depart(r);r.scan(code,bRotate0RawInternal=True);r.scan(code,**{cancelled:False})
 assert not r.v['bTriggerRequestInternal'] and not r.v['bFlipTriggerLatched']
print('PASS missing marker, short window, unaccepted camera, wrong program and interruption cannot send a late photo')

# Execute actual pre-camera window guard with a stub substituted for the camera call.
guard=machine[machine.index('IF NOT bVisionTriggerRequest THEN bVisionRotatingCaptureAccepted'):machine.index('fbVSCamera.RequestChangeProgram(')]
g=strip(guard)
m=re.search(r'bVisionTriggerAccepted := fbVSCamera.RequestTrigger\(\s*bEnable := (.*?)\);',g,re.S);assert m
gate=m[1];g=g[:m.start()]+'bGate := '+gate+';\nbVisionTriggerAccepted := bStubAccepted;'+g[m.end():]
v={k:0 for k in re.findall(h['var'],g)}
v.update({'bVisionTriggerRequest':True,'GVL_EtherCAT.stVSKeyenceCamera.bCurrentProgramNumber':1,'stInputs.bRotaryGripperPlace180':True})
h['execute'](g,v);assert not v['bGate']
v['GVL_EtherCAT.stVSKeyenceCamera.bTriggerAcknowledge']=True;v['bStubAccepted']=True
h['execute'](g,v);assert v['bGate'] and v['bVisionRotatingCaptureAccepted']
v['GVL_EtherCAT.stVSKeyenceCamera.bTriggerAcknowledge']=False;v['bStubAccepted']=False
h['execute'](g,v);assert v['bGate'],'accepted error recovery may continue after raw 180'
v['bVisionTriggerRequest']=False;h['execute'](g,v);assert not v['bVisionRotatingCaptureAccepted']

camera=method('POUs/02_Components/VS Keyence Camera/FB_VSCamera.TcPOU','RequestTrigger')
recovery=strip(camera[camera.index('IF bRecoverInspection OR bRecoveryFailed OR (usiTriggerHandshake = 35) THEN'):camera.index('CASE usiTriggerHandshake OF')])
for step,captured,expected in [(35,False,True),(40,True,True),(0,False,False)]:
 v={k:0 for k in re.findall(h['var'],recovery)};v.update({'usiTriggerHandshake':step,'bResultCapturedForTrigger':captured,'bRecoverInspection':step==40,'bRecoveryFailed':step==0})
 h['execute'](recovery,v);assert bool(v['RequestTrigger'])==expected
 assert not v['stCameraIO.bTrigger']
print('PASS bridge closes unaccepted window, retains ACK/error recovery, and never turns acceptance into a second trigger')

step100=vision[vision.index('100: // Support'):vision.index('110:',vision.index('100: // Support'))]
assert 'AND bRotate180Internal AND NOT bRotate0Internal' in step100
assert 'OR (bRotate0RawInternal AND bRotate180RawInternal)' in vision
assert 'IF bVisionRotate0Confirmed THEN' in machine and 'IF bVisionRotate180Confirmed THEN' in machine
assert 'stStatus.bVisionRotate0 := bVisionRotate0Confirmed' in machine
assert 'stStatus.bVisionRotate180 := bVisionRotate180Confirmed' in machine
assert 'bRotate0 := bVisionRotate0Confirmed' in machine and 'bRotate0Raw := stInputs.bRotaryGripperPick0' in machine
print('PASS Step100 waits for qualified 180; raw conflict detection, Manual, HOME and HMI use intended signal roles')
