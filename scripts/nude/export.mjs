import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import './source-adapter.cjs';
import './contract.cjs';
const createPlayerNameFallback=createRequire(import.meta.url)('../../dist/player-name-fallback.js');

export function matchState(match,now=Date.now()){
 const age=now-match.kickoff,checked=Date.parse(match.checkedAt);
 if(match.matchStatus==='finished')return 'finished';
 const hardLimit=({축구:4,야구:8,농구:5,배구:5,하키:5}[match.sport]||5)*3600000;
 if(age>hardLimit)return 'finished';
 if(match.matchStatus==='live'&&now-checked<3600000)return 'live';
 // When a provider omits both live and final status (e.g. bkvolley), cap fallback live duration tightly.
 const fallbackLimit=({축구:3,야구:6,농구:3.5,배구:3.5,하키:3.5}[match.sport]||4)*3600000;
 if(age>fallbackLimit)return 'finished';
 return age>=0?'live':'scheduled';
}

function isFinalResult(match,results){
 const items=Array.isArray(results?.items)?results.items:[];
 if(!items.length)return false;
 const norm=v=>String(v||'').trim().toLowerCase();
 const homeKeys=new Set([norm(match.teams?.[0]?.id),norm(match.teams?.[0]?.name)].filter(Boolean));
 const awayKeys=new Set([norm(match.teams?.[1]?.id),norm(match.teams?.[1]?.name)].filter(Boolean));
 for(const row of items){
  if(row?.status!=='final'||row.league!==match.league)continue;
  if(row.eventId&&match.eventId&&String(row.eventId)===String(match.eventId))return true;
  const rk=Date.parse(row.kickoff);
  if(!Number.isFinite(rk)||Math.abs(rk-match.kickoff)>30*60000)continue;
  const rHome=[norm(row.homeId),norm(row.homeName)].filter(Boolean);
  const rAway=[norm(row.awayId),norm(row.awayName)].filter(Boolean);
  if(rHome.some(k=>homeKeys.has(k))&&rAway.some(k=>awayKeys.has(k)))return true;
 }
 return false;
}

export function buildFeed(snapshot,catalog,teams,config,revision,scorebase={matches:[]},results={items:[]}){
 for(const rows of Object.values(snapshot.domestic||{}))if(Array.isArray(rows))for(const row of rows){
  const event=Date.parse(row.event?.date),prediction=Date.parse(row.prediction?.kickoff);
  if(Number.isFinite(event)&&Number.isFinite(prediction)&&Math.abs(event-prediction)>60000)
   throw Error(`Schedule/lineup kickoff mismatch: ${row.prediction?.league||'domestic'} ${row.event?.id||''}`);
 }
 const playerNames={...catalog.players};
 const nameKey=name=>String(name||'').normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
 const reviewed=new Map();
 for(const [name,korean] of Object.entries(playerNames)){
  const key=nameKey(name);
  if(reviewed.has(key)&&reviewed.get(key)!==korean)reviewed.set(key,null);
  else if(!reviewed.has(key))reviewed.set(key,korean);
 }
 const projections=[...(snapshot.items||[]),...Object.values(snapshot.domestic||{}).flat().map(row=>row.prediction||{})];
 const observed=projections.flatMap(row=>Object.values(row.lineups||{}).flat().map(player=>player?.name||player));
 for(const name of observed)if(typeof name==='string'&&!Object.hasOwn(playerNames,name)){
  const korean=reviewed.get(nameKey(name));
  if(korean)playerNames[name]=korean;
 }
 const reviewedCatalog={...catalog,players:playerNames};
 const model=globalThis.NudeLineupData.normalize(snapshot,reviewedCatalog,teams);
 if(model.rejected)throw Error(`${model.rejected} source rows rejected; update scripts/nude/source-adapter.cjs before publishing.`);
 const fallback=createPlayerNameFallback(playerNames);
 for(const match of model.matches)for(const team of match.teams){
  team.name=teams[team.name]||team.name;
  for(const player of team.players)player.name=fallback(player.name);
  for(const player of team.injuries||[])player.name=fallback(player.name);
  if(typeof team.pitcher==='string')team.pitcher=fallback(team.pitcher);
  else if(team.pitcher?.name)team.pitcher.name=fallback(team.pitcher.name);
 }
 model.matches.sort((a,b)=>a.kickoff-b.kickoff||a.id.localeCompare(b.id));
 for(const match of model.matches){
  if(isFinalResult(match,results))match.matchStatus='finished';
  match.matchStatus=matchState(match);
 }
 const published=model.matches.filter(match=>match.teams.some(team=>team.players.length));
 if(!published.length&&!config.allowEmptyFeed)throw Error('Empty feed blocked. Review collection or deliberately set allowEmptyFeed.');
 const feed={schemaVersion:1,asOf:model.asOf,pollSeconds:config.pollSeconds,revision,removalPolicy:'finished',
  leagues:scorebase.leagues||{},matches:published};
 globalThis.NudeLineupContract.validate(feed);
 return feed;
}

export function exportFeed(root=process.cwd()){
 const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
 const snapshot=read('dist/projections.json'),catalog=read('dist/name-catalog.json'),teams=read('dist/team-ko.json'),config=read('scripts/nude/config.json');
 catalog.teamCodes=read('scripts/nude/team-codes.json');
 let revision='local';try{revision=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();}catch{}
 const resultsPath=path.join(root,'dist/results.json');
 const results=fs.existsSync(resultsPath)?JSON.parse(fs.readFileSync(resultsPath,'utf8')):{items:[]};
 const feed=buildFeed(snapshot,catalog,teams,config,revision,{leagues:read('scripts/nude/league-catalog.json')},results);
 const target=path.join(root,'dist/nude-feed.json');
 if(fs.existsSync(target)){
  const old=read('dist/nude-feed.json');
  if(Date.parse(old.asOf)>Date.parse(feed.asOf))throw Error('Refusing to publish older source data');
  // A workflow-only commit should not produce an endless chain of new revisions.
  const comparable=x=>JSON.stringify({...x,revision:''});
  if(comparable(old)===comparable(feed)){console.log('NUDE feed unchanged');return old;}
 }
 const output=JSON.stringify(feed)+'\n',tmp=target+'.tmp';
 fs.writeFileSync(tmp,output);fs.renameSync(tmp,target);
 console.log(`NUDE feed ${feed.matches.length} matches, asOf=${feed.asOf}, sha256=${createHash('sha256').update(output).digest('hex')}`);
 return feed;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))exportFeed(process.argv[2]||process.cwd());
