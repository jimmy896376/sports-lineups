import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import './source-adapter.cjs';
import './contract.cjs';

export function buildFeed(snapshot,catalog,teams,config,revision){
 for(const rows of Object.values(snapshot.domestic||{}))if(Array.isArray(rows))for(const row of rows){
  const event=Date.parse(row.event?.date),prediction=Date.parse(row.prediction?.kickoff);
  if(Number.isFinite(event)&&Number.isFinite(prediction)&&Math.abs(event-prediction)>60000)
   throw Error(`Schedule/lineup kickoff mismatch: ${row.prediction?.league||'domestic'} ${row.event?.id||''}`);
 }
 const model=globalThis.NudeLineupData.normalize(snapshot,catalog,teams);
 if(model.rejected)throw Error(`${model.rejected} source rows rejected; update scripts/nude/source-adapter.cjs before publishing.`);
 if(!model.matches.length&&!config.allowEmptyFeed)throw Error('Empty feed blocked. Review collection or deliberately set allowEmptyFeed.');
 const feed={schemaVersion:1,asOf:model.asOf,pollSeconds:config.pollSeconds,revision,matches:model.matches};
 globalThis.NudeLineupContract.validate(feed);
 return feed;
}

export function exportFeed(root=process.cwd()){
 const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
 const snapshot=read('dist/projections.json'),catalog=read('dist/name-catalog.json'),teams=read('dist/team-ko.json'),config=read('scripts/nude/config.json');
 catalog.teamCodes=read('scripts/nude/team-codes.json');
 let revision='local';try{revision=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',stdio:['ignore','pipe','ignore']}).trim();}catch{}
 const feed=buildFeed(snapshot,catalog,teams,config,revision);
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
