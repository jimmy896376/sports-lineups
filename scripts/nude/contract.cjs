/* Stable data contract. This file reads data only; no remote code is executed. */
(function(root){
 'use strict';
 function validate(feed){
  const fail=message=>{throw Error('NUDE feed: '+message);};
  const str=(x,max=240)=>typeof x==='string'&&x.length>0&&x.length<=max;
  if(!feed||feed.schemaVersion!==1||!Number.isFinite(Date.parse(feed.asOf))||!Array.isArray(feed.matches))fail('invalid version, time or matches');
  if(feed.matches.length>10000)fail('too many matches');
  if(!Number.isInteger(feed.pollSeconds)||feed.pollSeconds<10||feed.pollSeconds>300)fail('pollSeconds must be 10–300');
  const ids=new Set();
  for(const m of feed.matches){
   if(!str(m.id,500)||ids.has(m.id))fail('missing or duplicate match id');ids.add(m.id);
   if(!str(m.league)||!str(m.leagueName)||!['축구','야구','농구','배구','하키'].includes(m.sport)||!Number.isFinite(m.kickoff)||!Number.isFinite(Date.parse(m.checkedAt)))fail('invalid match metadata');
   if(!Array.isArray(m.teams)||m.teams.length!==2||m.teams[0].side!=='home'||m.teams[1].side!=='away')fail('invalid teams');
   for(const t of m.teams){
    if(!str(t.id)||!str(t.name)||!['pending','predicted','confirmed'].includes(t.status)||!Array.isArray(t.players)||!Array.isArray(t.injuries))fail('invalid team');
    if(t.players.length>100||t.injuries.length>100)fail('too many players');
    if(!t.players.length&&t.status!=='pending')fail('empty roster must be pending');
    for(const p of t.players)if(!str(p.name)||typeof p.position!=='string'||typeof p.number!=='string'||typeof p.flag!=='string'||[p.position,p.number,p.flag].some(v=>v.length>240))fail('invalid player');
    for(const p of t.injuries)if(!str(p.name)||typeof p.status!=='string'||typeof p.detail!=='string'||p.detail.length>1000)fail('invalid injury');
    if(t.pitcher!=null&&typeof t.pitcher!=='string'&&!(typeof t.pitcher==='object'&&str(t.pitcher.name)))fail('invalid pitcher');
   }
  }
  return {asOf:feed.asOf,matches:feed.matches.slice().sort((a,b)=>a.kickoff-b.kickoff||a.id.localeCompare(b.id)),rejected:0,pollSeconds:feed.pollSeconds,revision:typeof feed.revision==='string'?feed.revision:''};
 }
 root.NudeLineupContract={validate};
})(typeof window!=='undefined'?window:globalThis);
