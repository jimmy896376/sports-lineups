import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const root = new URL('../', import.meta.url);
const read = path => JSON.parse(fs.readFileSync(new URL(path, root), 'utf8'));
const write = (path,value) => fs.writeFileSync(new URL(path,root),JSON.stringify(value,null,2)+'\n');
if (process.argv.includes('--queue')) {
  const entries = [];
  for (const [kind,path] of [['player','scripts/player-name-live-audit.json'],['team','scripts/team-name-live-audit.json']]) {
    if (!fs.existsSync(new URL(path,root))) continue;
    for (const row of read(path).pending || []) {
      const query = [row.name,row.team,row.league].filter(Boolean).join(' ');
      entries.push({...row,kind,google:`https://www.google.com/search?q=${encodeURIComponent(query)}`});
    }
  }
  write('scripts/name-review-queue.json',{policy:'Confirm club/player identity and established Korean full name before approving. Do not publish search snippets automatically.',entries});
  console.log(`Name review queue: ${entries.length} unreviewed names.`);
} else {
  const teams = read('dist/team-ko.json');
  const review = read('scripts/team-name-review.json');
  for (const row of review.entries) teams[row.name]=row.korean;
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(new URL('dist/player-ko.js',root),'utf8'),context);
  const autoPath = new URL('scripts/player-name-auto-review.json',root);
  const previous = fs.existsSync(new URL('dist/name-catalog.json',root)) ? read('dist/name-catalog.json') : {};
  const automatic = {};
  if(fs.existsSync(autoPath)) for(const row of read('scripts/player-name-auto-review.json').entries) {
    if(row.method==='korean-wikipedia-search-v1') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='ko.wikipedia.org' && url.pathname.startsWith('/wiki/') && s.languageLinkMatched && s.englishNameMatched && s.sportMatched && s.teamMatched && s.contentHash;
      }),'Korean Wikipedia search needs exact English identity, sport and club');
    } else if(row.method==='wikipedia-language-link-v1' || row.method==='wikipedia-language-link-v2') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && (row.method==='wikipedia-language-link-v2' ? ['ja.wikipedia.org','zh.wikipedia.org'].includes(url.hostname) : url.hostname==='en.wikipedia.org') && url.pathname.startsWith('/wiki/') && s.languageLinkMatched && s.englishNameMatched && (s.teamMatched || (s.exactEnglishTitleMatched && s.sportMatched)) && s.contentHash;
      }),'Wikipedia language link needs exact player and team identity');
    } else if(row.method==='wikidata-label-v1') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url), item=new URL(s.wikidataUrl);
        return url.protocol==='https:' && ['en.wikipedia.org','ja.wikipedia.org','zh.wikipedia.org'].includes(url.hostname) && url.pathname.startsWith('/wiki/') && item.protocol==='https:' && item.hostname==='www.wikidata.org' && item.pathname===`/wiki/${s.wikidataItem}` && /^Q[1-9][0-9]*$/.test(s.wikidataItem) && s.koreanLabelMatched && s.englishLabelMatched && s.englishNameMatched && s.sportMatched && (s.exactEnglishTitleMatched || s.teamMatched) && s.contentHash;
      }),'Wikidata label needs exact player and sports biography evidence');
    } else if(row.method==='namuwiki-team-roster-v1' || row.method==='namuwiki-team-roster-v2') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        const hosts=row.method==='namuwiki-team-roster-v2' ? ['namu.moe','d.namu.moe','m.namu.moe','www.namu.moe'] : ['namu.moe'];
        return url.protocol==='https:' && hosts.includes(url.hostname) && url.pathname.startsWith('/w/') && s.domain==='namu.moe' && s.teamMatched && s.englishNameMatched && s.rowMatched && s.contentHash;
      }),'NamuWiki roster needs exact team and bilingual player row');
    } else if(row.method==='kleague-official-roster-v1') {
      assert.ok(['kleague1','kleague2'].includes(row.league) && row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='www.kleague.com' && url.pathname==='/club/club.do'
          && url.searchParams.get('teamId')===s.clubCode && /^K[0-9]{2}$/.test(s.clubCode)
          && s.domain==='kleague.com' && s.teamMatched && s.jerseyMatched && s.contentHash;
      }),'K League roster needs official club and unique jersey evidence');
    } else if(['scorebase-nhl-roster-v1','scorebase-nba-roster-v1','scorebase-khl-roster-v1'].includes(row.method)) {
      assert.ok(row.method===`scorebase-${row.league}-roster-v1` && row.sources.length===1 && row.sources.every(s=>{
        const team=new URL(s.url),player=new URL(s.playerUrl);
        return team.protocol==='https:' && team.hostname==='www.scorebase.kr' && /^\/teams\/[0-9]+$/.test(team.pathname)
          && player.protocol==='https:' && player.hostname==='www.scorebase.kr' && /^\/players\/[0-9]+$/.test(player.pathname)
          && player.searchParams.get('league')===row.league.toUpperCase() && s.englishNameMatched && s.koreanNameMatched && s.contentHash;
      }),'Scorebase roster needs bilingual player link and team identity');
    } else if(row.method==='scorebase-khl-profile-v1' || row.method==='scorebase-khl-roster-variant-v1') {
      assert.ok(row.league==='khl' && row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='www.scorebase.kr'
          && /^\/players\/[a-z0-9]+$/.test(url.pathname) && url.searchParams.get('league')==='KHL'
          && s.domain==='scorebase.kr' && s.englishNameMatched && s.koreanNameMatched
          && s.leagueMatched && s.contentHash && (row.method==='scorebase-khl-profile-v1' || (()=>{
            const team=new URL(s.teamUrl);
            return team.protocol==='https:' && team.hostname==='www.scorebase.kr'
              && /^\/teams\/[0-9]+$/.test(team.pathname) && s.teamMatched && s.providerNameVariantMatched;
          })());
      }),'Scorebase KHL profile needs paired full names and league identity');
    } else if(row.method==='scorebase-namu-profile-v1') {
      assert.ok(row.sources.length===2 && row.sources.every(s=>s.contentHash), 'Scorebase player needs two source hashes');
      const scorebase=new URL(row.sources[0].url),namu=new URL(row.sources[1].url);
      assert.ok(scorebase.protocol==='https:' && scorebase.hostname==='www.scorebase.kr' && /^\/transfers\/[a-z0-9]+$/.test(scorebase.pathname)
        && row.sources[0].domain==='scorebase.kr' && row.sources[0].koreanNameMatched && row.sources[0].teamMatched
        && namu.protocol==='https:' && ['namu.moe','d.namu.moe','m.namu.moe','www.namu.moe'].includes(namu.hostname)
        && namu.pathname.startsWith('/w/') && row.sources[1].domain==='namu.moe' && row.sources[1].englishNameMatched
        && row.sources[1].koreanNameMatched && row.sources[1].teamMatched,
      'Scorebase football profile needs independent exact player and team identity');
    } else if(row.method==='google-search-result-v1') {
      assert.ok(row.sources.length>=1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='www.google.com' && url.pathname==='/search' && s.domain==='google.com' && s.teamMatched && (s.bilingualNameMatched || s.knowledgePanelMatched) && s.contentHash;
      }),'Google result needs player identity evidence');
    } else if(row.method==='daum-sports-profile-v1') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='search.daum.net' && url.pathname==='/search' && s.domain==='daum.net' && s.teamMatched && s.originalNameMatched && s.sportsProfileMatched && s.contentHash;
      }),'Daum profile needs exact player, sport and club identity');
    } else {
      assert.equal(row.method,'independent-bilingual-sources-v1');
      assert.ok(row.sources.length>=2 && new Set(row.sources.map(s=>s.domain)).size>=2 && row.sources.some(s=>s.teamMatched),'Automatic name needs independent identity evidence');
      assert.ok(row.sources.every(s=>s.bilingualNameMatched && /^https:\/\//.test(s.url)),'Automatic name lacks source evidence');
    }
    automatic[row.name]=row.korean;
  }
  for (const row of read('scripts/scorebase-name-candidates.json').entries) {
    if (row.method!=='scorebase-bilingual-candidate-v1') continue;
    assert.ok(row.name && row.team && /\p{Script=Hangul}/u.test(row.korean) && row.sources.length===2,
      `Invalid Scorebase bilingual name: ${row.name}`);
    const [ko,en]=row.sources.map(source=>new URL(source.url));
    assert.ok(ko.protocol==='https:' && en.protocol==='https:'
      && ko.hostname==='www.scorebase.kr' && en.hostname==='www.scorebase.kr'
      && /^\/transfers\/[a-z0-9]+$/.test(ko.pathname) && en.pathname===`/en${ko.pathname}`
      && row.sources[0].koreanNameMatched && row.sources[0].teamMatched
      && row.sources[1].englishNameMatched && row.sources[1].teamMatched
      && row.sources.every(source=>source.contentHash),
    `Scorebase bilingual name needs matching player ID and both club identities: ${row.name}`);
    if (!(row.name in automatic)) automatic[row.name]=row.korean;
  }
  // Human-reviewed spellings always take precedence over automated additions.
  vm.runInContext(fs.readFileSync(new URL('dist/football-ko.js',root),'utf8'),context);
  const element=()=>({innerHTML:'',textContent:'',dataset:{},addEventListener(){},setAttribute(){}});
  context.document={documentElement:{dataset:{}},getElementById:element,querySelector:element,addEventListener(){}};
  context.localStorage={getItem(){return null}};
  context.window={setInterval(){}};
  Object.assign(context,{fetch(){},atob,TextDecoder,Uint8Array});
  vm.runInContext(fs.readFileSync(new URL('dist/win-probability.js',root),'utf8'),context);
  vm.runInContext(fs.readFileSync(new URL('dist/app.js',root),'utf8').replace(/loadGames\(\);\s*$/,''),context);
  const appNames={...vm.runInContext('extraKo',context),...vm.runInContext('nhlPlayerKo',context)};
  for(const name of Object.keys(appNames)) if(previous.players?.[name]) appNames[name]=previous.players[name];
  const manual={...vm.runInContext('footballKo',context),...appNames,...vm.runInContext('playerKo',context),...read('scripts/player-name-review.json').userOverrides};
  const normalized=name=>name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const manualKeys=new Set(Object.keys(manual).map(normalized));
  // shortcut: published aliases persist; add explicit revocation when a spelling must be withdrawn.
  const players = {...previous.players,...Object.fromEntries(Object.entries(automatic).filter(([name])=>!manualKeys.has(normalized(name)))),...manual};
  const playerTeamNames={};
  for(const row of read('scripts/player-name-team-review.json').entries){
    const source=new URL(row.source);
    const kleague=['kleague1','kleague2'].includes(row.league) && /^\d+$/.test(row.number)
      && source.hostname==='www.kleague.com' && source.pathname==='/club/club.do'
      && /^K\d{2}$/.test(source.searchParams.get('teamId')||'');
    const football=row.league==='laliga' && ['Deportivo Alaves','Málaga'].includes(row.team)
      && ['Jonny','Calero'].includes(row.name) && source.hostname==='www.scorebase.kr'
      && /^\/transfers\/[a-z0-9]+$/.test(source.pathname);
    assert.ok(row.team && row.name && source.protocol==='https:' && (kleague||football) && /\p{Script=Hangul}/u.test(row.korean),
      `Invalid team-scoped player name: ${row.name}`);
    playerTeamNames[JSON.stringify([row.league,row.team,row.name])]=row.korean;
  }
  for (const dictionary of [teams,players,playerTeamNames]) {
    const aliases=new Map();
    for (const [name,korean] of Object.entries(dictionary)) {
      const plain=name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').normalize('NFC');
      if (plain!==name && !(plain in dictionary)) aliases.set(plain,aliases.has(plain) && aliases.get(plain)!==korean ? null : korean);
    }
    for (const [name,korean] of aliases) if (korean) dictionary[name]=korean;
    for (const [name,korean] of Object.entries(dictionary)) {
      assert.ok(name && typeof korean==='string' && korean.length<=160 && /\p{Script=Hangul}/u.test(korean),`Invalid approved name: ${name}`);
    }
  }
  const fixture=read('scripts/fixtures/player-name-inventory.json');
  const observed=fixture.records;
  const observedTeams=fixture.teams || [];
  const inventoryPath = new URL('scripts/player-name-live-inventory.json',root);
  if (fs.existsSync(inventoryPath)) {
    const inventory=read('scripts/player-name-live-inventory.json');
    if (Date.now()-Date.parse(inventory.at)<2*60*60*1000) {
      observed.push(...(inventory.records || []));
      observedTeams.push(...(inventory.teams || []));
    }
  }
  const addObservedAliases=(dictionary,rows)=>{
    const known=new Map();
    for (const [name,korean] of Object.entries(dictionary)) {
      const key=normalized(name);
      if (!known.has(key)) known.set(key,korean);
      else if (known.get(key)!==korean) known.set(key,null);
    }
    for (const {name} of rows) {
      if (typeof name!=='string' || name in dictionary) continue;
      const korean=known.get(normalized(name));
      if (korean) dictionary[name]=korean;
    }
  };
  addObservedAliases(players,observed);
  addObservedAliases(teams,observedTeams);
  const teamEnglish=Object.fromEntries(review.entries.filter(row=>row.english).map(row=>[row.name,row.english]));
  const unchanged = ['teams','teamEnglish','players','playerTeamNames'].every(key=>JSON.stringify(previous[key])===JSON.stringify({teams,teamEnglish,players,playerTeamNames}[key]));
  const catalog = {schemaVersion:1,generatedAt:unchanged && previous.generatedAt ? previous.generatedAt : new Date().toISOString(),teams,teamEnglish,players,playerTeamNames};
  write('dist/team-ko.json',teams);
  write('dist/name-catalog.json',catalog);
  console.log(`Approved name catalog: ${Object.keys(teams).length} team aliases, ${Object.keys(players).length} player aliases.`);
}
