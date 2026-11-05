"""Exercise actual saved ST in both feedback modes with scripted timer completion."""
from pathlib import Path
import runpy
root=Path(__file__).resolve().parents[2]
h=runpy.run_path(str(root/'engineering/patch-dispense-m1/check_sequence.py'))
initial=h['initial'];scan=h['scan']
def timed(step=10):
    v=initial(step=step)
    v.update({'bUseVerticalFeedbackInternal':False,'bVerticalUpInternal':False,'bVerticalDownInternal':False})
    return v

v=timed();v.update({'bHomeRequestInternal':True,'bHomingAllowedInternal':True,'eStateInternal':0})
scan(v);scan(v,**{'tonHomeSupportRetract.Q':True});scan(v,**{'tonHomeSupportRetract.Q':False});scan(v)
assert v['bVerticalUpRequestInternal'] and not v['bHomeInternal']
scan(v,bVerticalUpCommandInternal=True)
assert not v['bHomeInternal'] and not v['bVerticalIndexReadyInternal']
scan(v,**{'tonVerticalTimedUp.Q':True})
assert v['bHomeInternal'] and v['bVerticalIndexReadyInternal']
assert not v['bVerticalUpInternal'] and not v['bVerticalDownInternal']
scan(v,bVerticalUpCommandInternal=False,**{'tonVerticalTimedUp.Q':False})
assert not v['bVerticalIndexReadyInternal'], 'old timed UP alone cannot permit index'
print('PASS disconnected sensors: HOME waits for timed UP, raw inputs unchanged, index requires ongoing hold-UP')

v=timed();scan(v)
assert v['bVerticalUpRequestInternal'] and not v['bSupportExtendRequestInternal']
scan(v,bVerticalUpCommandInternal=True)
assert not v['bSupportExtendRequestInternal']
scan(v,**{'tonVerticalTimedUp.Q':True})
assert v['bSupportExtendRequestInternal']
scan(v,bSupportExtendedInternal=True,bSupportRetractedInternal=False)
scan(v,bPatchOpticalLeftInternal=True)
scan(v,bDriveMovingInternal=True,bDriveStandstillInternal=False,bDriveBusyInternal=True)
scan(v,bPatchOpticalLeftInternal=False)
assert v['usiStepInternal']==22
scan(v,bDriveMovingInternal=False,bDriveStandstillInternal=True,bDriveBusyInternal=False)
scan(v)
assert v['bVerticalDownRequestInternal'] and v['bAirBlowRequestInternal']
scan(v,bVerticalUpCommandInternal=False,bVerticalDownCommandInternal=True,**{'tonVerticalTimedUp.Q':False})
assert not v['bVerticalDownReadyInternal'] and v['usiStepInternal']==40
scan(v,**{'tonVerticalTimedDown.Q':True})
assert v['usiStepInternal']==50 and not v['bAirBlowRequestInternal']
scan(v,bVerticalDownCommandInternal=False,**{'tonVerticalTimedDown.Q':False})
assert v['usiStepInternal']==50 and not v['bVerticalUpRequestInternal']
scan(v,**{'tonRelease.Q':True});scan(v,**{'tonRelease.Q':False})
assert v['bVerticalUpRequestInternal'] and not v['bSupportRetractRequestInternal']
scan(v,bVerticalUpCommandInternal=True)
assert v['usiStepInternal']==60 and not v['bSupportRetractRequestInternal']
scan(v,**{'tonVerticalTimedUp.Q':True});scan(v)
assert v['bSupportRetractRequestInternal']
scan(v,bSupportRetractedInternal=True,bSupportExtendedInternal=False)
assert v['bCompleteInternal'] and v['stResultInternal.bValid']
assert not v['bVerticalUpInternal'] and not v['bVerticalDownInternal']
print('PASS full timed dispense: no false DOWN/UP completion, real dwell, no nest return before timed UP')

scan(v,bSafetyOkInternal=False)
assert not v['usiVerticalEstimatedPosition'] and not v['bVerticalIndexReadyInternal']
v=timed();v['usiVerticalEstimatedPosition']=1
scan(v,bVerticalUpCommandInternal=True,bVerticalDownCommandInternal=True)
assert not v['usiVerticalEstimatedPosition'] and not v['bVerticalIndexReadyInternal']
v=timed();v.update({'usiVerticalEstimatedPosition':1,'bUseVerticalFeedbackInternal':True,'eStateInternal':0})
scan(v)
assert not v['bVerticalUpReadyInternal'] and not v['bVerticalIndexReadyInternal']
scan(v,bVerticalUpInternal=True)
assert v['bVerticalIndexReadyInternal']
scan(v,bVerticalDownInternal=True)
assert v['bFaultInternal']
print('PASS safety/conflicting commands discard estimate; real-feedback mode restores physical checks without timer bypass')
