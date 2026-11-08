"""Actual saved Vision ST, scripted feedback and 10 ms task/timer model."""
from pathlib import Path
import runpy,xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[2]
h=runpy.run_path(str(root/'engineering/vision-hardware-retirement/test_station.py'))
state,scan=h['state'],h['scan']
reset=E.parse(root/'TwinCAT Patch Press/PatchPress/POUs/03_Stations/Vision/FB_VisionStation.TcPOU').find(".//Method[@Name='RequestReset']/Implementation/ST").text
reset=reset.replace('tonCameraTriggerDelay[1]','tonCameraTriggerDelay1').replace('tonCameraTriggerDelay[2]','tonCameraTriggerDelay2')
def mounting(manual=False):
 e=state(70)
 e.v.update(bManualModeInternal=manual,bHorizontalBackInternal=False,bHorizontalFrontInternal=True,
 bVerticalUpInternal=False,bVerticalDownInternal=True,bGripOpenedInternal=False,bGripClosedInternal=True,tStepDelay=100)
 return e
def wait_before_up(e,frames):
 for _ in range(frames):
  v=scan(e)
  assert v['usiStepInternal']==70 and not v['bVerticalUpRequestInternal']
  assert not v['bRotate180RequestInternal']
 return v
for manual in [False,True]:
 e=mounting(manual)
 e.v['bVerticalDownInternal']=False
 wait_before_up(e,200)
 assert e.v['tonStepDelay'].elapsed==0
 e.v['bVerticalDownInternal']=True
 wait_before_up(e,99)
 v=scan(e);assert v['usiStepInternal']==80
 v=scan(e);assert v['bVerticalUpRequestInternal'] and not v['bVerticalDownRequestInternal']
for interruption in ['down_loss','up_conflict']:
 e=mounting();wait_before_up(e,65)
 if interruption=='down_loss':e.v['bVerticalDownInternal']=False
 else:e.v['bVerticalUpInternal']=True
 wait_before_up(e,1)
 assert e.v['tonStepDelay'].elapsed==0
 e.v.update(bVerticalDownInternal=True,bVerticalUpInternal=False)
 wait_before_up(e,99)
 assert scan(e)['usiStepInternal']==80
for key,value in [('bSafetyOkInternal',False),('bEnableInternal',False),('bStopRequestInternal',True)]:
 e=mounting();wait_before_up(e,60);e.v[key]=value;scan(e)
 assert e.v['eStateInternal']!=30 or e.v['usiStepInternal']!=70
 # Run the actual Reset method before a later explicit new sequence entry.
 # A direct jump back into step 70 without Reset/HOME is not a supported restart.
 e.v.update(bSafetyOkInternal=True,bEnableInternal=True,bStopRequestInternal=False,
 bVerticalDownInternal=True,bVerticalUpInternal=False)
 e.v['stEmptyVisionResults']={}
 e.execute(h['Parser'](reset).block())
 assert e.v['tonStepDelay'].elapsed==0
 e.v.update(eStateInternal=30,usiStepInternal=70)
 wait_before_up(e,99);assert scan(e)['usiStepInternal']==80
# Pick/replacement descents retain the existing 100 ms common qualification.
for step in [30,140]:
 e=mounting();e.v['usiStepInternal']=step
 for _ in range(9):assert scan(e)['usiStepInternal']==step
 assert scan(e)['usiStepInternal']==step+10
print('PASS 1 s only after physical DOWN, Manual/Auto, no early UP/flip, DOWN loss/conflict restart, stop/disable/safety cancellation, unchanged other descents')
