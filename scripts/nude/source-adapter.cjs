/* Read-only adapter for the existing sports-lineups repository. No credentials. */
(function(root){
 'use strict';
 const leagues={ucl:['축구','UEFA 챔피언스리그'],uel:['축구','UEFA 유로파리그'],epl:['축구','프리미어리그'],championship:['축구','챔피언십'],laliga:['축구','라리가'],bundesliga:['축구','분데스리가'],seriea:['축구','세리에 A'],ligue1:['축구','리그 1'],mls:['축구','MLS'],ligamx:['축구','리가 MX'],j1:['축구','J1'],kleague1:['축구','K리그 1'],kleague2:['축구','K리그 2'],eredivisie:['축구','에레디비시'],jupiler:['축구','주필러리그'],primeira:['축구','프리메이라리가'],scottish:['축구','스코틀랜드 프리미어십'],mlb:['야구','MLB'],kbo:['야구','KBO'],npb:['야구','NPB'],cpbl:['야구','CPBL'],nba:['농구','NBA'],wnba:['농구','WNBA'],kbl:['농구','KBL'],wkbl:['농구','WKBL'],ncaam:['농구','NCAA'],kovo:['배구','V리그'],nhl:['하키','NHL'],khl:['하키','KHL']};
 const text=v=>typeof v==='string'?v.trim().slice(0,240):'';
 const day=ms=>new Date(Number(ms)+32400000).toISOString().slice(0,10);
 const valid=x=>!!x&&Array.isArray(x.items)&&x.domestic&&typeof x.domestic==='object'&&!Array.isArray(x.domestic)&&Number.isFinite(Date.parse(x.asOf));
 function normalize(snapshot,catalog={},teamNames={}){
  if(!valid(snapshot))throw Error('라인업 데이터 형식이 올바르지 않습니다.');
  const translated=(v,dict)=>text(dict?.[v])||text(v),seen=new Set(),matches=[];
  const rows=snapshot.items.map(p=>({prediction:p}));
  for(const [league,entries] of Object.entries(snapshot.domestic))if(Array.isArray(entries))for(const row of entries)rows.push({...row,prediction:{...row.prediction,league}});
  let rejected=0;
  for(const row of rows){
   const p=row.prediction||{},league=text(p.league),kind=leagues[league],kickoff=Date.parse(p.kickoff||row.event?.date);
   if(!kind||!Number.isFinite(kickoff)){rejected++;continue;}
   const teams=['home','away'].map(side=>{
    const eventTeam=row.event?.competitions?.[0]?.competitors?.find(t=>t.homeAway===side)?.team;
    const code=text(String(p.teams?.[side]||''));
    const aliases={UTA:'UTAH',GSW:'GS',NOP:'NO',NYK:'NY',SAS:'SA',SJS:'SJ',NJD:'NJ',LAK:'LA',TBL:'TB',WAS:'WSH'};
    const teamFull=v=>catalog.teamCodes?.[league]?.[aliases[v]||v]||v;
    const name=text(p.names?.[side]||eventTeam?.displayName||teamFull(code));
    const playerName=value=>text(catalog.playerTeamNames?.[JSON.stringify([league,name,value])])||translated(value,catalog.players);
    const players=(Array.isArray(p.lineups?.[side])?p.lineups[side]:[]).filter(x=>text(x?.name)).map(x=>({name:playerName(x.name),originalName:text(x.name),position:text(x.position),number:text(String(x.number??x.jersey??'')),flag:text(x.flag)}));
    const detailed=Array.isArray(p.injuryDetails?.[side])?p.injuryDetails[side]:[];
    const injuries=detailed.length?detailed:(Array.isArray(p.injuries?.[side])?p.injuries[side].map(name=>({name})):[]);
    const pitcher=p.startingPitchers?.[side];
    return {side,id:text(String(p.teams?.[side]||eventTeam?.id||name)),name:translated(teamFull(name),{...catalog.teams,...teamNames}),logo:text(p.logos?.[side]||eventTeam?.logo),players,status:players.length?(p.statuses?.[side]==='confirmed'?'confirmed':'predicted'):'pending',injuries:injuries.filter(x=>text(x?.name)).map(x=>({name:playerName(x.name),status:text(x.status),detail:text(x.detail||x.description||x.injury)})),pitcher:typeof pitcher==='string'?playerName(pitcher):pitcher?.name?{...pitcher,name:playerName(pitcher.name)}:null};
   });
   if(teams.some(t=>!t.name)){rejected++;continue;}
   // Names/translation changes do not change the identity; home and away remain ordered.
   const identity=JSON.stringify([league,new Date(kickoff).toISOString(),teams[0].id,teams[1].id]);
   if(seen.has(identity))continue;seen.add(identity);
   const source=snapshot.sourceStatus?.[league]||{};
   const competitorRecords=Object.fromEntries(['home','away'].map(side=>{
    const records=row.event?.competitions?.[0]?.competitors?.find(t=>t.homeAway===side)?.records||[];
    return [side,records.find(r=>r.name==='overall')?.summary];
   }).filter(([,value])=>value).map(([side,record])=>[side,{record}]));
   matches.push({id:identity,eventId:text(String(row.event?.id||'')),league,sport:kind[0],leagueName:kind[1],kickoff,teams,logos:p.logos||{},recentForm:Object.keys(p.recentForm||{}).length?p.recentForm:row.event?.recentForm||{},records:{...competitorRecords,...p.records},checkedAt:text(source.checkedAt||snapshot.asOf),sourceFailed:source.fresh===false,note:text(p.note)});
  }
  const days=new Set(Array.from({length:5},(_,offset)=>day(Date.parse(snapshot.asOf)+offset*86400000)));
  return {asOf:snapshot.asOf,matches:matches.filter(m=>days.has(day(m.kickoff))).sort((a,b)=>a.kickoff-b.kickoff||a.id.localeCompare(b.id)),rejected};
 }
 function select(matches,{sport='전체',league='',date='today',now=Date.now()}={}){
  const target=day(now+(date==='tomorrow'?86400000:0));
  return matches.filter(m=>(sport==='전체'||m.sport===sport)&&(!league||m.league===league)&&(date==='all'?m.kickoff>=Date.parse(day(now)+'T00:00:00+09:00'):day(m.kickoff)===target));
 }
 function positions(sport,players){
  const map=sport==='축구'?{GK:[8,50],DL:[28,16],LB:[28,16],DC:[28,50],CB:[28,50],DR:[28,84],RB:[28,84],DML:[44,20],DMC:[44,50],DM:[44,50],DMR:[44,80],ML:[58,16],LM:[58,16],MC:[58,50],CM:[58,50],MR:[58,84],RM:[58,84],AMC:[74,50],AM:[74,50],AML:[74,18],AMR:[74,82],FWL:[86,18],LW:[86,18],FWR:[86,82],RW:[86,82],FW:[88,50],ST:[88,50],CF:[88,50]}:sport==='농구'?{PG:[38,50],SG:[57,20],SF:[57,80],PF:[77,25],C:[83,65]}:null;
  if(!map||!players.length||players.some(p=>!map[p.position.toUpperCase()]))return [];
  const groups={};players.forEach((p,i)=>{const xy=map[p.position.toUpperCase()],key=xy.join(',');(groups[key]??=[]).push(i);});
  return players.map((p,i)=>{const xy=map[p.position.toUpperCase()],group=groups[xy.join(',')],n=group.indexOf(i);return {...p,x:xy[0],y:Math.max(10,Math.min(90,xy[1]+(n-(group.length-1)/2)*22))};});
 }
 root.NudeLineupData={normalize,select,positions,valid,day,leagues};
})(typeof window!=='undefined'?window:globalThis);
