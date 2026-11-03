import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const arg=(flag,fallback)=>{const i=process.argv.indexOf(flag);return i<0?fallback:process.argv[i+1]};
const output=arg('--output',root+'scripts/player-name-live-inventory.json');
const cacheDir=arg('--cache-dir',null);if(cacheDir)fs.mkdirSync(cacheDir,{recursive:true});
const elements=new Map();const element=()=>({innerHTML:'',textContent:'',dataset:{},addEventListener(){},setAttribute(){}});
const records=[];const teams=new Map();let currentLeague='';let currentEvent=null;const failures=[];
const cachedFetch=async url=>{
 if(String(url).includes('name-catalog.json'))return {ok:true,json:async()=>JSON.parse(fs.readFileSync(root+'/dist/name-catalog.json','utf8'))};
 const key=String(url).replace(/&v=\d+/,'');const file=cacheDir&&cacheDir+'/'+crypto.createHash('sha256').update(key).digest('hex')+'.json';
 if(file&&fs.existsSync(file)){const body=fs.readFileSync(file,'utf8');return {ok:true,json:async()=>JSON.parse(body)};}
 try{const response=await fetch(url,{signal:AbortSignal.timeout(20000)});if(!response.ok)throw Error(`HTTP ${response.status}`);const body=await response.text();JSON.parse(body);if(file)fs.writeFileSync(file,body);return {ok:true,json:async()=>JSON.parse(body)};}
 catch(error){failures.push({league:currentLeague,url:key,error:String(error)});return {ok:false,status:0,json:async()=>({})};}
};
const document={documentElement:{dataset:{}},getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id)},querySelector(){return element()},addEventListener(){}};
const ctx=vm.createContext({document,localStorage:{getItem(){return null}},window:{setInterval(){}},fetch:cachedFetch,atob,TextDecoder,Uint8Array,console});
for(const file of ['football-ko.js','player-ko.js','win-probability.js','app.js'])vm.runInContext(fs.readFileSync(root+'/dist/'+file,'utf8').replace(/loadGames\(\);\s*$/,''),ctx);
ctx.record=(player,kind,team)=>{const name=typeof player==='string'?player:player.name;if(name)records.push({name,eventDate:currentEvent?.date,eventId:currentEvent?.id,team:team?.team?.displayName,short:player.short,league:currentLeague,kind,korean:vm.runInContext(`translated(${JSON.stringify(name)},${JSON.stringify(player.short)})`,ctx)});};
ctx.setEvent=event=>{currentEvent=event};
ctx.recordTeam=team=>{const name=team.team.displayName;teams.set(currentLeague+':'+name,{name,short:team.team.shortDisplayName,league:currentLeague,korean:vm.runInContext(`teamDisplayName(${JSON.stringify(team.team)})`,ctx)});};
vm.runInContext(`const originalGameCard=gameCard;gameCard=function(event,...args){setEvent(event);return originalGameCard(event,...args)};const originalRange=kstDayRange;kstDayRange=function(){const [start]=originalRange();return [start,start+7*86400000]};const originalTeamCard=teamCard;teamCard=function(team,players,pitcher){recordTeam(team);for(const p of players||[])record(p,'lineup',team);if(pitcher?.name)record(pitcher,'starting-pitcher',team);return originalTeamCard(team,players,pitcher)};const originalInjuryPanel=injuryPanel;injuryPanel=function(prediction,event){for(const side of ['home','away']){const team=event?.competitions?.[0]?.competitors?.find(t=>t.homeAway===side);for(const p of [...(prediction?.injuryDetails?.[side]||[]),...(prediction?.injuries?.[side]||[])])record(typeof p==='string'?p:{...p,name:p.name||p.player},'injury',team);}return originalInjuryPanel(prediction,event)};`,ctx);
const leagues=vm.runInContext(`Object.entries(sources).filter(([id])=>leagueIds.includes(id)).map(([id])=>({sport:'football',league:id})).concat(sports.filter(x=>x.id!=='football').map(x=>({sport:x.id,league:x.id})))`,ctx);
for(const item of leagues){currentLeague=item.league;vm.runInContext(`majorView=false;sport=${JSON.stringify(item.sport)};league=${JSON.stringify(item.league)};`,ctx);await vm.runInContext('loadGames()',ctx);const rendered=elements.get('games').innerHTML;console.log(item.league,records.filter(r=>r.league===item.league).length,rendered.includes('class="empty"')?rendered.replace(/<[^>]+>/g,'').slice(0,100):'loaded');}
// The NudeTV feed can contain projected players that the original site does not render.
const projections=JSON.parse(fs.readFileSync(root+'/dist/projections.json','utf8'));
const projectionRows=[...(projections.items||[]),...Object.entries(projections.domestic||{}).flatMap(([league,rows])=>rows.map(row=>({...row.prediction,league})))];
const seen=new Set(records.map(row=>[row.league,row.team,row.kind,row.name].join('\0')));
for(const p of projectionRows)for(const side of ['home','away']){
 const team=p.names?.[side]||p.teams?.[side];
 if(!team)continue;
 const add=(player,kind)=>{
  const name=typeof player==='string'?player:player?.name||player?.player;
  if(!name)return;
  const key=[p.league,team,kind,name].join('\0');
  if(seen.has(key))return;
  seen.add(key);
  records.push({name,eventDate:p.kickoff,team,league:p.league,kind,korean:vm.runInContext(`translated(${JSON.stringify(name)})`,ctx)});
 };
 for(const player of p.lineups?.[side]||[])add(player,'lineup');
 for(const player of [...(p.injuryDetails?.[side]||[]),...(p.injuries?.[side]||[])])add(player,'injury');
 if(p.startingPitchers?.[side])add(p.startingPitchers[side],'starting-pitcher');
}
fs.writeFileSync(output,JSON.stringify({at:new Date().toISOString(),leagues,records,teams:[...teams.values()],failures},null,2));
const unique=[...new Map(records.map(r=>[r.name,r])).values()];console.log(JSON.stringify({total:unique.length,missing:unique.filter(r=>[...r.name].some(char=>/\p{L}/u.test(char)&&!/\p{Script=Hangul}/u.test(char))&&r.name===r.korean).length,failures:failures.length}));

if(!records.length || (failures.length && !process.argv.includes('--allow-partial')))process.exitCode=1;
