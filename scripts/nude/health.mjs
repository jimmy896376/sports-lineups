import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import './contract.cjs';

export function inspect(feed,snapshot,now=Date.now()){
 const issues=[];
 const checked=globalThis.NudeLineupContract.validate(feed);
 const age=(now-Date.parse(feed.asOf))/60000;
 if(age>45||age< -5)issues.push(`feed age ${Math.round(age)} minutes`);
 if(!Number.isFinite(Date.parse(snapshot.asOf))||Math.abs(Date.parse(snapshot.asOf)-Date.parse(feed.asOf))>20*60000)issues.push('feed/source snapshot mismatch');
 for(const [league,status] of Object.entries(snapshot.sourceStatus||{}))
  if(status?.fresh!==true||!Number.isFinite(Date.parse(status.checkedAt))||now-Date.parse(status.checkedAt)>60*60000)
   issues.push(`source unavailable or stale: ${league}`);
 if(!checked.matches.length)issues.push('empty feed');
 const day=ms=>new Date(ms+9*3600000).toISOString().slice(0,10);
 const allowed=new Set([0,1,2].map(offset=>day(now+offset*86400000)));
 let missingLogos=0,emptyLineups=0,latinPlayers=0,missingKboForms=0,missingKboRecords=0;
 for(const match of checked.matches){
  if(!allowed.has(day(match.kickoff)))issues.push(`outside three-day window: ${match.id}`);
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
 return {asOf:feed.asOf,ageMinutes:Math.round(age),matches:checked.matches.length,missingLogos,emptyLineups,latinPlayers,missingKboForms,missingKboRecords,issues};
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])){
 const feed=JSON.parse(fs.readFileSync('dist/nude-feed.json','utf8'));
 const snapshot=JSON.parse(fs.readFileSync('dist/projections.json','utf8'));
 const report=inspect(feed,snapshot);
 console.log(JSON.stringify(report));
 if(report.latinPlayers)console.log(`::warning::${report.latinPlayers} lineup names still contain Latin letters`);
 for(const issue of report.issues)console.error(`::error::${issue}`);
 if(report.issues.length)process.exitCode=1;
}
