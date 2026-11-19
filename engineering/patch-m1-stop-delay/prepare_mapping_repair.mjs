// Default: read-only preview. --apply requires separate user authorization.
// Writes only local engineering HMI configuration; no PLC values or published server.
import fs from 'node:fs';
import crypto from 'node:crypto';
const base=new URL('./',import.meta.url);
const source=new URL('../../TwinCAT Patch Press/PatchPress_HMI/Server/TcHmiSrv/TcHmiSrv.Config.default.json',import.meta.url);
const disk=JSON.parse(fs.readFileSync(source,'utf8').replace(/^\uFEFF/,''));
const ws=new WebSocket('ws://127.0.0.1:3000/');
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
let id=0;
const pending=new Map();
ws.onmessage=({data})=>{const r=JSON.parse(data);const p=pending.get(r.id);if(p){clearTimeout(p.timer);pending.delete(r.id);p.resolve(r);}};
async function request(commands){
 const current=++id;
 return await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>{pending.delete(current);reject(new Error('HMI read/config request timed out'));},7000);
  pending.set(current,{resolve,timer});
  ws.send(JSON.stringify({requestType:'ReadWrite',id:current,commands}));
 });
}
const symbolNames=['TcHmiSrv.Config::SYMBOLS','TcHmiSrv.Config::USERGROUPS','TcHmiSrv.Config::DEFINITIONS'];
const result=await request(symbolNames.map(symbol=>({symbol,commandOptions:['SendErrorMessage']})));
if(result.error||result.commands?.some(c=>c.error||c.readValue===undefined))throw new Error('Cannot read engineering configuration; no writes permitted');
const before=Object.fromEntries(result.commands.map(c=>[c.symbol,c.readValue]));
if(process.argv.includes('--inspect')){
 const plan=JSON.parse(fs.readFileSync(new URL('mapping-repair-plan.json',base),'utf8'));
 const differences=[];
 function compare(a,b,path=''){
  if(a&&b&&typeof a==='object'&&typeof b==='object'){
   for(const key of new Set([...Object.keys(a),...Object.keys(b)]))compare(a[key],b[key],path+'/'+key);
  }else if(a!==b)differences.push(path);
 }
 compare(plan.after,before);
 fs.writeFileSync(new URL('mapping-repair-readback.json',base),JSON.stringify(before,null,2));
 console.log(JSON.stringify({semanticMatch:differences.length===0,differences}));
 ws.close();process.exit(0);
}
const after=structuredClone(before);
const field='udiDriveStopDelayMs';
for(const kind of ['Edit','Applied']){
 const key=`ADS.PLC1.GVL_HMI.stPatchProcess${kind}.${field}`;
 const existing=key.replace(field,'udiAirBlowDelayMs');
 if(!disk.SYMBOLS[key])throw new Error('Missing source mapping');
 const live=after[symbolNames[0]][key];
 if(live&&JSON.stringify(live)!==JSON.stringify(disk.SYMBOLS[key]))throw new Error('Conflicting existing engineering mapping');
 after[symbolNames[0]][key]=disk.SYMBOLS[key];
 for(const [groupName,group] of Object.entries(after[symbolNames[1]])){
  if(group.SYMBOLS?.[existing]===undefined)throw new Error('Missing reference permission: '+groupName);
  group.SYMBOLS[key]=group.SYMBOLS[existing];
 }
}
const schemaName='ADS-PLC1.ST_PatchProcessSettings';
const schema=after[symbolNames[2]].ADS[schemaName];
if(!schema?.properties?.udiAirBlowDelayMs)throw new Error('Missing live reference schema');
schema.properties[field]=disk.DEFINITIONS.ADS[schemaName].properties[field];
if(!schema.required.includes(field))schema.required.push(field);
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const hash=v=>crypto.createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
const plan={endpoint:'ws://127.0.0.1:3000/',beforeHash:hash(before),afterHash:hash(after),before,after};
if(!process.argv.includes('--apply')){
 fs.writeFileSync(new URL('mapping-repair-plan.json',base),JSON.stringify(plan,null,2));
 console.log(JSON.stringify({mode:'read-only preview',endpoint:plan.endpoint,changed:plan.beforeHash!==plan.afterHash,mappings:2,permissions:'copy existing corresponding air-delay access for each group',schema:'append UDINT field; preserve other properties',writesExecuted:0}));
}else{
 const reviewed=JSON.parse(fs.readFileSync(new URL('mapping-repair-plan.json',base),'utf8'));
 if(hash(before)!==hash(reviewed.before)||hash(after)!==hash(reviewed.after))throw new Error('Configuration/source changed since preview; no writes applied');
 const writes=symbolNames.filter(symbol=>hash(before[symbol])!==hash(after[symbol])).map(symbol=>({symbol,writeValue:after[symbol],commandOptions:['SendErrorMessage']}));
 const written=await request(writes);
 if(written.error||written.commands?.some(c=>c.error))throw new Error('Engineering configuration write failed; inspect before retry');
 const verified=await request(symbolNames.map(symbol=>({symbol,commandOptions:['SendErrorMessage']})));
 const readback=Object.fromEntries(verified.commands.map(c=>[c.symbol,c.readValue]));
 if(hash(readback)!==hash(after))throw new Error('Engineering configuration readback mismatch');
 const symbols=['Edit','Applied'].map(k=>`ADS.PLC1.GVL_HMI.stPatchProcess${k}.${field}`);
 const values=await request(symbols.map(symbol=>({symbol,commandOptions:['SendErrorMessage']})));
 console.log(JSON.stringify({mode:'local engineering configuration applied',readbackVerified:true,commands:values.commands?.map(c=>({symbol:c.symbol,value:c.readValue,error:c.error}))}));
}
ws.close();
