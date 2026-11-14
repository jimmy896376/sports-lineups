import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import './contract.cjs';
import {matchState} from './export.mjs';

export function inspect(feed,snapshot,now=Date.now()){
 const issues=[];
 const checked=globalThis.NudeLineupContract.validate(feed);
 const age=(now-Date.parse(feed.asOf))/60000;
 // Scheduled jobs can arrive late; the workflow avoids retrying while a collector is already running.
 if(age>45||age< -5)issues.push(`feed age ${Math.round(age)} minutes`);
 if(!Number.isFinite(Date.parse(snapshot.asOf))||Math.abs(Date.parse(snapshot.asOf)-Date.parse(feed.asOf))>20*60000)issues.push('feed/source snapshot mismatch');
 for(const [league,status] of Object.entries(snapshot.sourceStatus||{}))
  if(status?.fresh!==true||!Number.isFinite(Date.parse(status.checkedAt))||now-Date.parse(status.checkedAt)>90*60000)
   issues.push(`source unavailable or stale: ${league}`);
 if(!checked.matches.length)issues.push('empty feed');
 const day=ms=>new Date(ms+9*3600000).toISOString().slice(0,10);
 const allowed=new Set(Array.from({length:5},(_,offset)=>day(now+offset*86400000)));
 let missingLogos=0,emptyLineups=0,latinPlayers=0,missingKboForms=0,missingKboRecords=0;
 const missingStatsByLeague={};
 for(const match of checked.matches){
  if(match.matchStatus!=='finished'&&!(match.matchStatus==='live'&&matchState(match,now)==='live')&&!allowed.has(day(match.kickoff)))issues.push(`outside five-day window: ${match.id}`);
  const coverage=missingStatsByLeague[match.league]??={recentForm:0,seasonRecord:0,venueRecord:0};
  for(const side of ['home','away']){
   if(!match.recentForm?.[side]?.length)coverage.recentForm++;
   if(!match.records?.[side]?.record)coverage.seasonRecord++;
   if(!match.records?.[side]?.sideRecord)coverage.venueRecord++;
  }
  for(const team of match.teams){
   if(!team.logo||!/^https:\/\/[^\s]+$/.test(team.logo)){missingLogos++;issues.push(`missing or invalid logo: ${match.id} ${team.side}`);}
   if(!team.players.length){emptyLineups++;issues.push(`empty lineup: ${match.id} ${team.side}`);}
   latinPlayers+=team.players.filter(player=>/[A-Za-z]/.test(player.name)).length;
  }
  if(match.league==='kbo'){
   for(const side of ['home','away']){
    if(!match.recentForm?.[side]?.length)missingKboForms++;
    if(!match.records?.[side]?.record||!match.records?.[side]?.sideRecord)missingKboRecords++;
   }
  }
 }
 if(missingKboForms)issues.push(`KBO recent form missing for ${missingKboForms} teams`);
 if(missingKboRecords)issues.push(`KBO season/venue records missing for ${missingKboRecords} teams`);
 return {asOf:feed.asOf,ageMinutes:Math.round(age),matches:checked.matches.length,missingLogos,emptyLineups,latinPlayers,missingKboForms,missingKboRecords,missingStatsByLeague,issues};
}

export function inspectPublication(source,live,now=Date.now()){
 const report=inspect(live,{asOf:live.asOf},now);
 const lag=Date.parse(source.asOf)-Date.parse(live.asOf);
 if(lag>10*60000)report.issues.push(`published feed lags source by ${Math.round(lag/60000)} minutes`);
 if(lag>=0){
  const published=new Map(live.matches.map(match=>[match.id,match]));
  let lostTeamNames=0,lostPlayerNames=0,lostLogos=0;
  for(const match of source.matches){
   const current=published.get(match.id);
   if(!current)continue;
   for(const team of match.teams){
    const shown=current.teams.find(value=>value.side===team.side);
    if(!shown)continue;
    if(/[가-힣]/.test(team.name)&&!/[가-힣]/.test(shown.name))lostTeamNames++;
    if(team.logo&&!shown.logo)lostLogos++;
    const players=new Map(shown.players.map(player=>[player.originalName||player.name,player.name]));
    for(const player of team.players)
     if(/[가-힣]/.test(player.name)&&!/[가-힣]/.test(players.get(player.originalName||player.name)||''))lostPlayerNames++;
   }
  }
  if(lostTeamNames||lostPlayerNames||lostLogos)report.issues.push(`published feed lost ${lostTeamNames} team names, ${lostPlayerNames} player names, ${lostLogos} logos`);
 }
 return report;
}

export async function inspectLogoUrls(feed,fetcher=fetch,slot=Math.floor(Date.now()/900000)){
 const urls=[...new Set(feed.matches.flatMap(match=>match.teams.map(team=>team.logo).filter(Boolean)))].sort();
 const selected=urls.filter((_,index)=>index%12===slot%12);
 const results=await Promise.all(selected.map(async url=>{
  try{
   const response=await fetcher(url,{headers:{'user-agent':'Mozilla/5.0',range:'bytes=0-63',accept:'image/*'},signal:AbortSignal.timeout(6000)});
   await response.body?.cancel();
   if([404,410].includes(response.status)||([200,206].includes(response.status)&&!response.headers.get('content-type')?.startsWith('image/')))
    return `broken logo: ${url} (HTTP ${response.status})`;
  }catch{}
  return null;
 }));
 return {checked:selected.length,issues:results.filter(Boolean)};
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])){
 const feed=JSON.parse(fs.readFileSync('dist/nude-feed.json','utf8'));
 const snapshot=JSON.parse(fs.readFileSync('dist/projections.json','utf8'));
 let report=inspect(feed,snapshot);
 if(process.argv.includes('--live')){
  try{
   const base=process.env.NUDE_LINEUP_LIVE_URL;
   if(!base)throw Error('NUDE_LINEUP_LIVE_URL is required');
   const url=new URL(base);url.searchParams.set('audit',String(Date.now()));
   const response=await fetch(url,{signal:AbortSignal.timeout(10000),cache:'no-store'});
   if(!response.ok)throw Error(`published feed HTTP ${response.status}`);
   const live=await response.json();
   const published=inspectPublication(feed,live);
   const logos=await inspectLogoUrls(live);
   published.issues.push(...logos.issues);
   report={...report,published:{asOf:published.asOf,matches:published.matches,logosChecked:logos.checked,issues:published.issues},issues:[...report.issues,...published.issues]};
  }catch(error){report.issues.push(`published feed unavailable: ${error.message}`);}
 }
 console.log(JSON.stringify(report));
 if(report.latinPlayers)console.log(`::warning::${report.latinPlayers} lineup names still contain Latin letters`);
 for(const [league,missing] of Object.entries(report.missingStatsByLeague))
  if(Object.values(missing).some(Boolean))console.log(`::warning::${league} records missing: ${JSON.stringify(missing)}`);
 for(const issue of report.issues)console.error(`::error::${issue}`);
 if(report.issues.length)process.exitCode=1;
}
