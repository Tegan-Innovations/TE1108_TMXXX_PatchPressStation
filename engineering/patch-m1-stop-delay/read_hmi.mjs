// Strictly read-only requests; no Login, writeValue, subscription or PLC commands.
import https from 'node:https';
const local=process.argv.includes('--local');
const host=local?'127.0.0.1':'192.168.0.10', port=local?3000:1020;
if(!local){
await new Promise(resolve=>{
 const r=https.get({hostname:host,port,path:'/',rejectUnauthorized:false,timeout:5000},res=>{
  let body='';res.on('data',c=>body+=c);res.on('end',()=>{console.log(JSON.stringify({httpStatus:res.statusCode,title:body.match(/<title>(.*?)<\/title>/is)?.[1],length:body.length}));resolve();});
 });r.on('error',e=>{console.log(JSON.stringify({httpError:e.message}));resolve();});r.on('timeout',()=>r.destroy());
});
}
process.env.NODE_TLS_REJECT_UNAUTHORIZED='0';
const ws=new WebSocket(`${local?'ws':'wss'}://${host}:${port}/`);
const timer=setTimeout(()=>{console.log('Read-only websocket timeout');ws.close();},7000);
ws.onopen=()=>{
 const symbols=process.argv.includes('--config')?[
  'TcHmiSrv.Config::SYMBOLS::ADS.PLC1.GVL_HMI.stPatchProcessEdit.udiDriveStopDelayMs',
  'TcHmiSrv.Config::SYMBOLS::ADS.PLC1.GVL_HMI.stPatchProcessApplied.udiDriveStopDelayMs',
  'TcHmiSrv.Config::SYMBOLS::ADS.PLC1.GVL_HMI.stPatchProcessApplied.udiAirBlowDelayMs'
 ]:['ADS.PLC1.GVL_HMI.stPatchProcessEdit.udiDriveStopDelayMs','ADS.PLC1.GVL_HMI.stPatchProcessApplied.udiDriveStopDelayMs','ADS.PLC1.GVL_HMI.stPatchProcessApplied.udiAirBlowDelayMs'];
 ws.send(JSON.stringify({requestType:'ReadWrite',id:1,commands:symbols.map(symbol=>({symbol,commandOptions:['SendErrorMessage']}))}));
};
ws.onmessage=({data})=>{try{const r=JSON.parse(data);console.log(JSON.stringify({id:r.id,commands:r.commands,error:r.error}));}catch{console.log('Non-JSON response');}clearTimeout(timer);ws.close();};
ws.onerror=e=>{console.log(JSON.stringify({websocketError:e.message}));clearTimeout(timer);};
