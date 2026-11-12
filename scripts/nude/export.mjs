import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import './source-adapter.cjs';
import './contract.cjs';

export function buildFeed(snapshot,catalog,teams,config,revision,scorebase={matches:[]}){
 for(const rows of Object.values(snapshot.domestic||{}))if(Array.isArray(rows))for(const row of rows){
  const event=Date.parse(row.event?.date),prediction=Date.parse(row.prediction?.kickoff);
  if(Number.isFinite(event)&&Number.isFinite(prediction)&&Math.abs(event-prediction)>60000)
   throw Error(`Schedule/lineup kickoff mismatch: ${row.prediction?.league||'domestic'} ${row.event?.id||''}`);
 }
 const model=globalThis.NudeLineupData.normalize(snapshot,catalog,teams);
 if(model.rejected)throw Error(`${model.rejected} source rows rejected; update scripts/nude/source-adapter.cjs before publishing.`);
 if(!model.matches.length&&!config.allowEmptyFeed)throw Error('Empty feed blocked. Review collection or deliberately set allowEmptyFeed.');
 const key=name=>String(name||'').normalize('NFKD').toLowerCase().replace(/\b(?:fc|cf|sc|afc)\b/g,'').replace(/[^\p{L}\p{N}]/gu,'');
 const alike=(a,b)=>{const left=key(a),right=key(b);return left.length>=3&&right.length>=3&&(left===right||left.includes(right)||right.includes(left));};
 const sharedName=(a,b)=>String(a).split(/[^\p{L}\p{N}]+/u).some(word=>word.length>=3&&String(b).split(/[^\p{L}\p{N}]+/u).includes(word));
 const days=new Set(Array.from({length:5},(_,offset)=>new Date(Date.parse(snapshot.asOf)+9*3600000+offset*86400000).toISOString().slice(0,10)));
 const starters={축구:[11],야구:[9],농구:[5],배구:[6,7],하키:[19]};
 for(const extra of scorebase.matches||[]){
  const date=new Date(extra.kickoff+9*3600000).toISOString().slice(0,10);
  if(!days.has(date)||!starters[extra.sport]||extra.teams?.length!==2||
     extra.teams.some(team=>!starters[extra.sport].includes(team.players?.length))||
     (extra.sport==='축구'&&!['home','away'].every(side=>extra.recentForm?.[side]?.length===5&&extra.records?.[side]?.record&&extra.records?.[side]?.sideRecord)))continue;
  const duplicate=model.matches.find(match=>match.sport===extra.sport&&Math.abs(match.kickoff-extra.kickoff)<=10*60000&&
    (alike(match.teams[0].name,extra.teams[0].name)&&alike(match.teams[1].name,extra.teams[1].name)||
     key(match.teams[0].name)===key(extra.teams[0].name)&&sharedName(match.teams[1].name,extra.teams[1].name)||
     key(match.teams[1].name)===key(extra.teams[1].name)&&sharedName(match.teams[0].name,extra.teams[0].name)));
  const translate=player=>({...player,name:catalog.players?.[player.name]||player.name});
  if(duplicate){
   duplicate.league=extra.league;duplicate.leagueName=extra.leagueName;
   duplicate.teams.forEach((team,index)=>{team.players=extra.teams[index].players.map(translate);team.status=extra.teams[index].status;team.logo=extra.teams[index].logo||team.logo;});
   if(Object.keys(extra.recentForm||{}).length)duplicate.recentForm=extra.recentForm;
   if(Object.keys(extra.records||{}).length)duplicate.records=extra.records;
  }else model.matches.push({...extra,teams:extra.teams.map(team=>({...team,players:team.players.map(translate)}))});
 }
 model.matches.sort((a,b)=>a.kickoff-b.kickoff||a.id.localeCompare(b.id));
 const feed={schemaVersion:1,asOf:model.asOf,pollSeconds:config.pollSeconds,revision,
  leagues:scorebase.leagues||{},matches:model.matches};
 globalThis.NudeLineupContract.validate(feed);
 return feed;
}

export function exportFeed(root=process.cwd()){
 const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
 const snapshot=read('dist/projections.json'),catalog=read('dist/name-catalog.json'),teams=read('dist/team-ko.json'),config=read('scripts/nude/config.json');
 catalog.teamCodes=read('scripts/nude/team-codes.json');
 let revision='local';try{revision=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();}catch{}
 const scorebasePath=path.join(root,'dist/scorebase-lineups.json');
 const scorebase=fs.existsSync(scorebasePath)?read('dist/scorebase-lineups.json'):{matches:[]};
 const feed=buildFeed(snapshot,catalog,teams,config,revision,scorebase);
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
