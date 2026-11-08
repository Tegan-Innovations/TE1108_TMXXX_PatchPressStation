"""Small bounded interpreter for the saved diagnostic functions, not a PLC runtime.

Used solely to exercise protocol fixtures against executable ST, including
memory bounds and signed parameters. Does not load ADS or operate equipment.
"""
import re, struct, copy, xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'TwinCAT Patch Press/PatchPress/POUs/06_Utilities'
TOKEN=re.compile(r"\s+|//[^\n]*|'(?:\$.|[^'$])*'|T#\d+(?:MS|S)|16#[0-9A-Fa-f]+|\d+|[A-Za-z_]\w*|:=|<>|<=|>=|[.,:;()\[\]+*/=<>-]")
class Parser:
 def __init__(self,s):
  self.t=[];end=0
  for m in TOKEN.finditer(s):
   assert not s[end:m.start()].strip(),s[end:m.start()]
   end=m.end()
   if m[0].strip() and not m[0].startswith('//'):self.t.append(m[0])
  assert not s[end:].strip()
  self.i=0
 def peek(self):return self.t[self.i] if self.i<len(self.t) else ''
 def take(self,x=None):
  v=self.peek();assert v and (x is None or v==x),(x,v,self.t[self.i:self.i+12]);self.i+=1;return v
 def expr(self,minimum=0):
  t=self.take()
  if t in ['NOT','-']:left=('unary',t,self.expr(7))
  elif t=='(':left=self.expr();self.take(')')
  elif t.startswith("'"):left=('literal',t[1:-1].replace("$'","'").replace('$$','$'))
  elif t.startswith('16#'):left=('literal',int(t[3:],16))
  elif t.startswith('T#'):left=('literal',int(re.search(r'\d+',t)[0])*(1 if t.endswith('MS') else 1000))
  elif t.isdigit():left=('literal',int(t))
  elif t in ['TRUE','FALSE']:left=('literal',t=='TRUE')
  else:
   left=('var',t)
   if self.peek()=='(':
    self.take();args=[]
    while self.peek()!=')':
     if self.i+1<len(self.t) and self.t[self.i+1]==':=':
      key=self.take();self.take(':=');args.append(('named',key,self.expr()))
     else:args.append(self.expr())
     if self.peek()!=',':break
     self.take(',')
    self.take(')');left=('call',t,args)
  while self.peek() in ['.','[']:
   op=self.take()
   if op=='.':left=('member',left,self.take())
   else:left=('index',left,self.expr());self.take(']')
  priority={'OR':1,'AND':2,'=':3,'<>':3,'<':3,'>':3,'<=':3,'>=':3,'+':4,'-':4,'*':5,'/':5}
  while self.peek() in priority and priority[self.peek()]>=minimum:
   op=self.take();left=('binary',op,left,self.expr(priority[op]+1))
  return left
 def block(self,stops=(),case=False):
  out=[]
  while self.peek() and self.peek() not in stops:
   if case and (self.peek().isdigit() or self.peek().startswith('16#')):break
   t=self.peek()
   if t==';':self.take();continue
   if t=='IF':
    self.take();cond=self.expr();self.take('THEN');parts=[(cond,self.block(['ELSIF','ELSE','END_IF']))]
    while self.peek()=='ELSIF':
     self.take();cond=self.expr();self.take('THEN');parts.append((cond,self.block(['ELSIF','ELSE','END_IF'])))
    otherwise=[]
    if self.peek()=='ELSE':self.take();otherwise=self.block(['END_IF'])
    self.take('END_IF');out.append(('if',parts,otherwise))
   elif t=='CASE':
    self.take();value=self.expr();self.take('OF');parts=[]
    while self.peek() not in ['ELSE','END_CASE']:
     labels=[self.expr()]
     while self.peek()==',':self.take();labels.append(self.expr())
     self.take(':');parts.append((labels,self.block(['ELSE','END_CASE'],True)))
    otherwise=[]
    if self.peek()=='ELSE':self.take();otherwise=self.block(['END_CASE'])
    self.take('END_CASE');out.append(('case',value,parts,otherwise))
   elif t=='FOR':
    self.take();name=self.take();self.take(':=');start=self.expr();self.take('TO');end=self.expr();step=('literal',1)
    if self.peek()=='BY':self.take();step=self.expr()
    self.take('DO');body=self.block(['END_FOR']);self.take('END_FOR');out.append(('for',name,start,end,step,body))
   elif t in ['EXIT','RETURN']:self.take();out.append((t,))
   else:
    left=self.expr()
    if self.peek()==':=':self.take();out.append(('assign',left,self.expr()))
    else:out.append(('call',left))
   if self.peek()==';':self.take()
  return out
class Return(Exception):pass
class Exit(Exception):pass
class Pointer:
 def __init__(self,engine,node):self.engine=engine;self.node=node
 def read(self,count):
  if self.node[0]=='index':
   seq=self.engine.ev(self.node[1]);index=self.engine.ev(self.node[2]);assert 0<=index and index+count<=len(seq);return bytes(seq[index:index+count])
  v=self.engine.ev(self.node)
  if isinstance(v,list):assert count<=len(v);return bytes(v[:count])
  return int(v).to_bytes(count,'little',signed=v<0)
 def write(self,data):
  if self.node[0]=='var' and isinstance(self.engine.v[self.node[1]],list):
   assert len(data)<=len(self.engine.v[self.node[1]])
   self.engine.v[self.node[1]][:len(data)]=list(data);return
  typ=self.engine.types.get(self.node[1],'') if self.node[0]=='var' else ''
  self.engine.set(self.node,int.from_bytes(data,'little',signed=typ in ['SINT','INT','DINT']))
class Engine:
 cache={}
 def __init__(self,name,values):
  if name not in self.cache:
   t=E.parse(SOURCE/(name+'.TcPOU'));decl=t.findtext('.//Declaration')
   variables={}
   for names,typ in re.findall(r'(?m)^\s*([\w, ]+)\s*:\s*(\w+)',decl):
    for n in names.split(','):variables[n.strip()]=typ
   self.cache[name]=(variables,Parser(t.findtext('.//Implementation/ST')).block())
  self.types,self.code=self.cache[name];self.v={k:'' if t=='STRING' else 0 for k,t in self.types.items()}
  self.v[name]={k:'' for k in ['sSeverity','sTimestamp','sMessage','sDetail']} if name=='F_EL6910DecodeMessage' else ''
  self.v.update(values);self.name=name
 def ev(self,n):
  kind=n[0]
  if kind=='literal':return n[1]
  if kind=='var':return self.v[n[1]]
  if kind=='member':return self.ev(n[1])[n[2]]
  if kind=='index':
   seq=self.ev(n[1]);i=self.ev(n[2]);assert 0<=i<len(seq);return seq[i]
  if kind=='unary':return not self.ev(n[2]) if n[1]=='NOT' else -self.ev(n[2])
  if kind=='binary':
   a,b=self.ev(n[2]),self.ev(n[3]);op=n[1]
   return {'OR':lambda:a|b,'AND':lambda:a&b,'=':lambda:a==b,'<>':lambda:a!=b,'<':lambda:a<b,'>':lambda:a>b,'<=':lambda:a<=b,'>=':lambda:a>=b,'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[op]()
  name,args=n[1:]
  if name=='ADR':return Pointer(self,args[0])
  if name in self.v and isinstance(self.v[name],(Timer,Upload)):
   self.v[name].call({x[1]:self.ev(x[2]) for x in args});return 0
  a=[self.ev(x) for x in args]
  if name=='MEMCPY':a[0].write(a[1].read(a[2]));return a[2]
  if name=='MEMSET':a[0].write(bytes([a[1]])*a[2]);return a[2]
  if name=='SIZEOF':return len(a[0])
  if name.endswith('_TO_STRING'):return str(a[0])
  if '_TO_' in name:return int(a[0])
  if name=='CONCAT':return (a[0]+a[1])[:255]
  if name=='MID':return a[0][a[2]-1:a[2]-1+a[1]]
  if name=='FIND':return a[0].find(a[1])+1
  if name=='REPLACE':return (a[0][:a[3]-1]+a[1]+a[0][a[3]-1+a[2]:])[:255]
  if name=='SHR':return a[0]>>a[1]
  if name=='MIN':return min(a)
  if name=='F_EL6910Hex':return Engine(name,dict(zip(['uliValue','uiDigits'],a))).run()
  if name=='F_EL6910MessageTemplate':return Engine(name,{'wTextId':a[0]}).run()
  if name=='F_EL6910DecodeMessage':return Engine(name,dict(zip(['aData','cbData'],a))).run()
  raise AssertionError(name)
 def set(self,node,value):
  if isinstance(value,(dict,list)):value=copy.deepcopy(value)
  if node[0]=='var':self.v[node[1]]=value
  elif node[0]=='member':self.ev(node[1])[node[2]]=value
  elif node[0]=='index':self.ev(node[1])[self.ev(node[2])]=value
  else:raise AssertionError(node)
 def execute(self,code):
  for n in code:
   k=n[0]
   if k=='assign':self.set(n[1],self.ev(n[2]))
   elif k=='call':self.ev(n[1])
   elif k=='RETURN':raise Return()
   elif k=='EXIT':raise Exit()
   elif k=='if':
    for cond,body in n[1]:
     if self.ev(cond):self.execute(body);break
    else:self.execute(n[2])
   elif k=='case':
    value=self.ev(n[1])
    for labels,body in n[2]:
     if value in [self.ev(x) for x in labels]:self.execute(body);break
    else:self.execute(n[3])
   elif k=='for':
    start,end,step=[self.ev(x) for x in n[2:5]];assert abs(end-start)<10000
    for i in range(start,end+(1 if step>0 else -1),step):
     self.v[n[1]]=i
     try:self.execute(n[5])
     except Exit:break
 def run(self):
  try:self.execute(self.code)
  except Return:pass
  return self.v[self.name]
def decode(data,length=None):
 return Engine('F_EL6910DecodeMessage',{'aData':list(data)+[0]*(256-len(data)),'cbData':len(data) if length is None else length}).run()
class Timer(dict):
 def __init__(self):super().__init__(Q=False);self.elapsed=0
 def call(self,a):
  self.elapsed=self.elapsed+10 if a['IN'] else 0
  self['Q']=self.elapsed>=a['PT']
class Upload(dict):
 def __init__(self,reply):super().__init__(bBusy=False,bError=False,cbRead=0,nErrId=0);self.reply=reply;self.pending=None;self.requests=[]
 def call(self,a):
  if a['bExecute']:
   assert not self['bBusy'],'Overlapping upload'
   self.pending=a;self['bBusy']=True;self.requests.append((a['nIndex'],a['nSubIndex']))
  elif self.pending:
   data,error=self.reply(self.pending);self['bBusy']=False;self['bError']=bool(error);self['nErrId']=error;self['cbRead']=len(data)
   if not error:self.pending['pDstBuf'].write(data)
   self.pending=None
def reader(reply):
 row=lambda:{'sName':'','sState':'','sDiagnostic':'','sQuality':''}
 history=lambda:{'sSeverity':'','sTimestamp':'','sMessage':'','sDetail':''}
 status={'sReaderStatus':'','sLogicState':'','sCycleCounter':'','sGroupState':'','sGroupDiagnostic':'','sHistoryStatus':'','aConnections':[None]+[row() for _ in range(6)],'aBlocks':[None]+[row() for _ in range(24)],'aHistory':[None]+[history() for _ in range(8)]}
 return Engine('FB_EL6910Diagnostics',dict(bEnable=True,sMasterNetId='fixture',uiSlaveAddress=1003,stStatus=status,fbRead=Upload(reply),tonGap=Timer(),tonSweep=Timer(),tonHistoryAge=Timer(),aBuffer=[0]*256,aHistoryPending=[None]+[history() for _ in range(8)]))
if __name__=='__main__':
 header=lambda text,flags=2,stamp=123:struct.pack('<IHHQ',0x12345678,flags,text,stamp)
 assert Engine('F_EL6910Hex',{'uliValue':0xFEDCBA9876543210,'uiDigits':16}).run()=='FEDCBA9876543210'
 sample=header(0x3803,0x0202)+struct.pack('<HhHH',3,1,6,0x10)
 result=decode(sample)
 assert result['sSeverity']=='Error' and 'FB 1 (ESTOP)' in result['sMessage'] and '0x0010' in result['sMessage'],result
 assert result['sTimestamp']=='DC 0x000000000000007B'
 assert '12345678' in result['sDetail']
 result=decode(header(0x3803,0x0211)+struct.pack('<HbHH',2,-1,6,0xFF))
 assert 'FB -1' in result['sMessage'] and result['sSeverity']=='Warning' and result['sTimestamp'].startswith('Local ')
 assert decode(header(0xFFFF))['sMessage'].startswith('Unknown EL6910 Text ID')
 assert decode(bytes(32))['sMessage']==''
 for n in range(16):assert decode(sample[:n])['sMessage']=='Invalid diagnostic record length'
 for n in range(16,len(sample)):
  assert '[see raw parameters]' in decode(sample[:n])['sMessage']
 assert '[see raw parameters]' in decode(header(0x3803,0x0102)+struct.pack('<H',0x2005)+b'abc')['sMessage']
 assert decode(sample,257)['sMessage']=='Invalid diagnostic record length'
 # Random malformed payloads exercise bounded reads, parameter widths and header flags.
 import random
 rng=random.Random(6910)
 for i in range(1000):
  length=rng.randrange(257);decode(bytes(rng.randrange(256) for _ in range(length)))
 print('PASS executable saved ST decoder: signed/hex parameters, timestamps, unknown IDs, zero records, truncation and 1000 malformed frames')
