import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Execute the production dictionaries and rendering functions without network requests.
const elements = new Map();
const storage = new Map();
const element = () => ({addEventListener() {},setAttribute() {},innerHTML:'',textContent:''});
const context = vm.createContext({
  localStorage: {getItem(key) { return storage.get(key)||null; },setItem(key,value) {storage.set(key,value);}},
  document: {documentElement: {dataset: {}}, getElementById(id) {if(!elements.has(id))elements.set(id,element());return elements.get(id);}, querySelector() {return element();}, addEventListener() {}},
  window: {setInterval() {}},
  atob,TextDecoder,Uint8Array
});
for (const file of ['football-ko.js', 'player-ko.js', 'win-probability.js', 'app.js']) {
  let source = fs.readFileSync(new URL(`../dist/${file}`, import.meta.url), 'utf8');
  if (file === 'app.js') source = source.replace(/loadGames\(\);\s*$/, '');
  vm.runInContext(source, context, {filename: file});
}
const run = code => vm.runInContext(code, context);
const approvedCatalog = JSON.parse(fs.readFileSync(new URL('../dist/name-catalog.json',import.meta.url),'utf8'));
context.approvedPlayers = approvedCatalog.players;
run('Object.assign(naverKo,approvedPlayers);Object.assign(naverKoNormalized,Object.fromEntries(Object.entries(approvedPlayers).map(([name,korean])=>[normalizePlayerName(name),korean])))');
for (const [name,korean] of Object.entries({
  'Jabari Smith':'자바리 스미스 주니어','Dennis Seimen':'데니스 자이멘',
  'Atakan Karazor':'아타칸 카라조르','Lorenz Assignon':'로랑 아시뇽',
  'Robin Le Normand':'로뱅 르노르망','Oleg Ocheretko':'올레 오쉐레트코',
  'Valerii Bondar':'발레리 본다르','Meleek Thomas':'밀릭 토마스',
  'Pedro Lima':'페드로 리마','Pedro Henrique':'페드루 엔히키',
  'Gleiker Mendoza':'글라이커 멘도사','Isaque':'이자키'
})) assert.equal(approvedCatalog.players[name],korean,name);
assert.equal(run("availability('QUES')"),'출전 불투명');
context.checkedTeamDictionary=JSON.parse(fs.readFileSync(new URL('../dist/team-ko.json',import.meta.url),'utf8'));
run('applyTeamNames(checkedTeamDictionary)');
assert.throws(()=>run('applyTeamNames({bad:123})'),/Invalid team name dictionary/);
assert.equal(run("teamKo['Manchester United']"),'맨체스터 유나이티드 FC');
assert.equal(run("teamDisplayName({displayName:'Mito HollyHock'})"),'미토 홀리호크');
assert.equal(run("teamDisplayName({displayName:'Como'})"),'코모 1907');
assert.equal(run("teamDisplayName({displayName:'Lille'})"),'LOSC 릴');
assert.equal(run("teamDisplayName({displayName:'SC Freiburg'})"),'SC 프라이부르크');
assert.equal(run("teamDisplayName({displayName:'Unreviewed United'})"),'Unreviewed United');
for (const [name, expected] of [
  ['Abdulkerim Bardakci', '압둘케림 바르닥치'],
  ['Alisson Becker', '알리송 베커'], ['Alisson', '알리송 베커'],
  ['Onyeka Okongwu', '오니에카 오콩우'],
  ['Nickeil Alexander-Walker', '니킬 알렉산더워커'],
  ['Jayson Tatum', '제이슨 테이텀'],
  ['Donovan Mitchell', '도노반 미첼'],
  ['Antonín Kinsky', '안토닌 킨스키'], ['Noah Atubolu', '노아 아투볼루'],
  ['Mateus Fernandes', '마테우스 페르난데스'],
  ['牧　秀悟', '마키 슈고'], ['周東　佑京', '슈토 우쿄'],
  ['Kentavious Caldwell‑Pope', '켄타비우스 콜드웰-폽'],
  ['Joshua Kimmich', '요주아 키미히'],
  ['Sidney Crosby', '시드니 크로스비'],
  ['Shohei Ohtani', '오타니 쇼헤이'],
  ['Alexey Batrakov', '알렉세이 바트라코프'],
  ['Baris Alper Yilmaz', '바리스 알페르 일마즈'],
  ['Eduardo Felicíssimo', '에두아르도 펠리시시모'],
  ['Silas Andersen', '실라스 안데르센'],
  ['Fotis Ioannidis', '포티스 이오아니디스'],
  ['Yehor Nazaryna', '예호르 나자리나'],
  ['Brayden Burries', '브레이든 버리스'],
  ['Baylor Scheierman', '베일러 샤이어맨'],
  ['Unknown Player', 'Unknown Player'], ['Alisson Santos', 'Alisson Santos'],
  ['Becker', 'Becker']
]) assert.equal(run(`translated(${JSON.stringify(name)})`), expected, name);
run("sport='football'");
assert.match(run("teamLogo({team:{displayName:'Manchester United',logo:'https://a.espncdn.com/i/teamlogos/soccer/500/132.png'}})"),/soccer\/500\/360\.png/);
assert.match(run("teamLogo({team:{displayName:'Roma'}})"),/soccer\/500\/104\.png/);
context.logoEvent = {date:'2026-11-03T20:00:00Z',competitions:[{competitors:[
  {homeAway:'home',team:{displayName:'Manchester United',abbreviation:'MAN'}},
  {homeAway:'away',team:{displayName:'Roma',abbreviation:'ROMA'}}
]}]};
context.logoItems = [
  {league:'ucl',kickoff:context.logoEvent.date,teams:{home:'MUN',away:'ROM'},names:{home:'Bayern Munich',away:'Roma'}},
  {league:'ucl',kickoff:context.logoEvent.date,teams:{home:'MUN',away:'ROM'},names:{home:'Manchester United',away:'Roma'}}
];
assert.equal(run('predictionFor(logoEvent,logoItems,"ucl").names.home'),'Manchester United');
assert.equal(run(`translated('João Neves')`), run(`translated('Joao Neves')`));
assert.equal(run(`normalizePlayerName('Łukasz Skorupski')`),run(`normalizePlayerName('Lukasz Skorupski')`));
for (const [name, korean] of run('Object.entries(playerKo)')) {
  context.checkedPlayer = {name};
  assert.equal(run('translated(checkedPlayer.name)'), korean, name);
  assert.ok(run(`teamCard({team:{displayName:'Team'},homeAway:'home'},[checkedPlayer]).includes(safe(translated(checkedPlayer.name)))`), `Lineup: ${name}`);
  assert.ok(run(`injuryPanel({injuryDetails:{home:[checkedPlayer]}},{}).includes(safe(translated(checkedPlayer.name)))`), `Injury: ${name}`);
}
assert.match(run(`teamCard({team:{displayName:'Liverpool'},homeAway:'home'},[{name:'Alisson Becker'}])`), /알리송 베커/);
assert.match(run(`injuryPanel({injuryDetails:{home:[{name:'Alisson Becker',status:'out'}]}},{})`), /알리송 베커/);
run(`language='en'`);
assert.equal(run(`translated('Alisson Becker')`), 'Alisson Becker');
assert.match(run(`teamCard({team:{displayName:'Liverpool'},homeAway:'home'},[{name:'Alisson Becker'}])`), /Alisson Becker/);
run(`language='ko'`);
const collisions = run(`Object.entries(naverKo).filter(([name,korean])=>naverKoNormalized[normalizePlayerName(name)]!==korean)`);
assert.equal(collisions.length, 0, `Conflicting normalized names: ${JSON.stringify(collisions)}`);
const reviewed = JSON.parse(fs.readFileSync(new URL('./player-name-source-review.json', import.meta.url), 'utf8')).entries;
assert.equal(new Set(reviewed.map(row=>row.name)).size, reviewed.length, 'Duplicate source review names');
for (const row of reviewed) {
  assert.ok(row.source.startsWith('https://'), `Missing source: ${row.name}`);
  assert.equal(run(`translated(${JSON.stringify(row.name)})`), row.korean, `Source review: ${row.name}`);
}
console.log(`Player names and both rendering paths passed. Reviewed dictionary: ${run('Object.keys(playerKo).length')} names/aliases.`);

const teamReview = JSON.parse(fs.readFileSync(new URL('./team-name-review.json', import.meta.url),'utf8'));
const reviewedTeamHosts = new Set(['cdn.kovo.co.kr','iffhs.com','news.coupang.com','readonly.wiki',
  'sports.daum.net','toricori.com','www.ford.co.kr','www.hankyung.com','www.ktwiz.co.kr',
  'www.liveman.co.kr','www.newyorkredbulls.com']);
for (const row of teamReview.entries) {
  context.teamToReview = {displayName:row.name};
  assert.equal(run('teamDisplayName(teamToReview)'),row.korean,row.name);
  const source = new URL(row.source);
  assert.ok(row.source.startsWith('https://www.google.com/search?') ||
    (source.hostname==='www.yagoonara.com' && row.identitySource?.startsWith('https://npb.jp/')) ||
    (source.protocol==='https:' && (['namu.moe','d.namu.moe','m.namu.moe','www.namu.moe'].includes(source.hostname) || reviewedTeamHosts.has(source.hostname))),row.name);
}
run(`nameReview={request:requestId,names:new Map()};teamDisplayName({displayName:'Manchester United'});playerDisplayName('Alisson Becker');playerDisplayName('Unreviewed Athlete');finishNameReview(requestId);`);
let refreshReport = JSON.parse(storage.get('sports-lineups-name-review'));
assert.deepEqual(refreshReport.pending.map(row=>row.name),['Unreviewed Athlete']);
assert.equal(refreshReport.names.length,3);
run(`nameReview={request:requestId,names:new Map()};teamDisplayName({displayName:'Manchester United'});finishNameReview(requestId-1);`);
assert.ok(run('nameReview !== null'),'An older response must not finish the latest review');
run('finishNameReview(requestId)');
refreshReport = JSON.parse(storage.get('sports-lineups-name-review'));
assert.equal(refreshReport.names.length,1,'Previous refresh names must be cleared');
assert.equal(refreshReport.pending.length,0);
run(`nameReview={request:requestId,names:new Map(),failed:true};finishNameReview(requestId);`);
assert.equal(JSON.parse(storage.get('sports-lineups-name-review')).status,'data-unavailable');
context.fetch = async () => {throw new Error('Offline');};
await run(`majorView=false;sport='khl';loadGames()`);
assert.equal(JSON.parse(storage.get('sports-lineups-name-review')).status,'data-unavailable');
const refreshRequests = [];
context.fetch = async (url,options) => {
  refreshRequests.push({url,options});
  const snapshot = {items:[],domestic:{khl:[]}};
  return {ok:true,json:async()=>String(url).includes('name-catalog.json') ? {schemaVersion:1,generatedAt:String(url).startsWith('https://raw.')?'2026-10-23T00:00:00Z':'2026-10-24T00:00:00Z',teams:context.checkedTeamDictionary,players:{'Abdulkerim Bardakci':'압둘케림 바르닥치','Source Verified Player':String(url).startsWith('https://raw.')?'이전 표기':'검증된 선수'},teamEnglish:{'Como':'Como 1907'}} : String(url).includes('/contents/') ? {content:Buffer.from(JSON.stringify(snapshot)).toString('base64')} : snapshot};
};
await run('loadGames()');
await run('loadGames()');
refreshReport = JSON.parse(storage.get('sports-lineups-name-review'));
assert.equal(refreshReport.status,'checked');
assert.equal(refreshReport.dictionaryStatus,'fresh');
assert.equal(refreshReport.names.length,0,'Failed/previous loads must not leak names');
const dictionaryRequests = refreshRequests.filter(row=>String(row.url).includes('name-catalog.json'));
assert.equal(dictionaryRequests.length,4,'Each refresh must check both live and bundled dictionaries');
assert.ok(dictionaryRequests.every(row=>row.options.cache==='no-store'));
assert.equal(run("playerDisplayName('Source Verified Player')"),'검증된 선수','Newer bundled spellings win while GitHub CDN serves an older snapshot');
run("language='en'");
assert.equal(run("teamDisplayName({displayName:'Como',shortDisplayName:'COM'})"),'Como 1907');
run("language='ko'");
assert.equal(run("teamDisplayName({displayName:'Unreviewed Full Club',shortDisplayName:'UFC'})"),'Unreviewed Full Club');
const fallbackRequests=[];
context.fetch=async url=>{
  fallbackRequests.push(String(url));
  if(String(url).startsWith('https://raw.')) throw new Error('GitHub unavailable');
  return {ok:true,json:async()=>({schemaVersion:1,teams:context.checkedTeamDictionary,players:{'Catalog Test Player':'검수 선수'}})};
};
run('nameReview={request:requestId,names:new Map()};');
await run('refreshTeamNames(requestId)');
assert.equal(fallbackRequests.length,2,'Try bundled catalog after GitHub failure');
assert.equal(run("translated('Catalog Test Player')"),'검수 선수','Apply approved player updates during refresh');
assert.equal(run('nameReview.dictionaryStatus'),'fresh');
run('finishNameReview(requestId)');
console.log(`Team source review and refresh audit passed: ${teamReview.entries.length} reviewed team names.`);

context.searchDate=new Date(Date.now()+3600000).toISOString();
context.oldSearchDate=new Date(Date.now()-3*86400000).toISOString();
run(`indexTeamSearch({items:[{league:'ucl',kickoff:searchDate,names:{home:'Como',away:'Manchester United'},teams:{home:'COM',away:'MUN'}},{league:'ucl',kickoff:oldSearchDate,names:{home:'Lille',away:'Arsenal'},teams:{}}],domestic:{kovo:[{event:{date:searchDate,competitions:[{competitors:[{homeAway:'home',team:{displayName:'우리카드'}},{homeAway:'away',team:{displayName:'한국전력'}}]}]}}]}})`);
run(`indexTeamSearch({items:[{league:'ucl',kickoff:searchDate.replace('Z','+00:00'),names:{home:'Como',away:'Manchester United'},teams:{home:'COM',away:'MUN'}}]},true)`);
assert.equal(run("findTeamGames('코모 1907').length"),1);
assert.equal(run("findTeamGames('코모')[0].home"),'Como');
assert.equal(run("findTeamGames('Como').length"),1);
assert.equal(run("findTeamGames('MUN').length"),1);
assert.equal(run("findTeamGames('우리WON').length"),1);
assert.equal(run("findTeamGames('Arsenal').length"),0,'Exclude games outside today/tomorrow');
assert.equal(run("findTeamGames('').length"),0);
assert.equal(run("findTeamGames('<script>').length"),0);
console.log('Team search: full Korean/English names, abbreviation, domestic nicknames and date range passed.');

// Unlike snapshot-only audits, this inventory also covers ESPN live starters,
// recent-game fallback starters and injury names collected by the actual renderers.
if (process.argv.includes('--inventory')) {
  const input = process.argv[process.argv.indexOf('--inventory') + 1];
  assert.ok(input, '--inventory requires a collected inventory path');
  const inventory = JSON.parse(fs.readFileSync(input, 'utf8'));
  const exceptions = JSON.parse(fs.readFileSync(new URL('./player-name-exceptions.json', import.meta.url), 'utf8')).entries;
  const allowed = new Set(exceptions.map(row => row.name));
  const names = [...new Map(inventory.records.map(row => [row.name, row])).values()];
  const pending = [], english = [];
  for (const row of names) {
    context.checkedPlayer = row;
    run(`language='ko'`);
    const korean = run('translated(checkedPlayer.name,checkedPlayer.short)');
    if (/\p{Script=Latin}/u.test(row.name) && korean === row.name) {
      (allowed.has(row.name) ? english : pending).push(row);
    }
    run(`language='en'`);
    if (/\p{Script=Latin}/u.test(row.name)) {
      assert.equal(run('translated(checkedPlayer.name,checkedPlayer.short)'), row.name.normalize('NFD').replace(/\p{M}/gu,''), `English: ${row.name}`);
    }
  }
  run(`language='ko'`);
  const report = {collectedAt:inventory.at, totalNames:names.length, mapped:names.length-pending.length-english.length, reviewedEnglish:english, pending, fetchFailures:inventory.failures};
  fs.writeFileSync(new URL('./player-name-live-audit.json', import.meta.url), JSON.stringify(report,null,2)+'\n');
  const teams = [...new Map((inventory.teams||inventory.records.filter(row=>row.team).map(row=>({name:row.team,league:row.league}))).map(row=>[row.name,row])).values()];
  const pendingTeams = teams.filter(row=>!run(`teamKo[${JSON.stringify(row.name)}]||teamKoNormalized[normalizePlayerName(${JSON.stringify(row.name)})]`)).map(row=>({...row,google:`https://www.google.com/search?q=${encodeURIComponent(row.name)}`,status:'needs-source-review'}));
  fs.writeFileSync(new URL('./team-name-live-audit.json',import.meta.url),JSON.stringify({collectedAt:inventory.at,totalTeams:teams.length,reviewed:teams.length-pendingTeams.length,pending:pendingTeams},null,2)+'\n');
  console.log(`Team inventory: ${teams.length-pendingTeams.length}/${teams.length} source-reviewed; ${pendingTeams.length} queued.`);
  console.log(`Live inventory: ${report.totalNames} names; ${report.mapped} mapped, ${english.length} reviewed English exceptions, ${pending.length} unchecked.`);
  if (process.argv.includes('--require-reviewed')) {
    assert.equal(inventory.failures.length, 0, 'Inventory collection has fetch failures');
    assert.equal(pending.length, 0, `Unchecked live player names: ${pending.map(row=>row.name).join(', ')}`);
    assert.equal(pendingTeams.length,0,`Unchecked team names: ${pendingTeams.map(row=>row.name).join(', ')}`);
  }
}

// Audit every supplied league and date, including both injury data formats.
// A missing dictionary entry means "needs review", never "no Korean name exists".
if (process.argv.includes('--audit')) {
  const inputIndex = process.argv.indexOf('--input');
  const input = inputIndex < 0 ? new URL('../dist/projections.json', import.meta.url) : process.argv[inputIndex + 1];
  assert.ok(input, '--input requires a snapshot path');
  const snapshot = JSON.parse(fs.readFileSync(input, 'utf8'));
  const names = new Map();
  const predictions = [...(snapshot.items || []), ...Object.entries(snapshot.domestic || {}).flatMap(([league, games]) => games.map(game => ({...game.prediction, league})))];
  for (const prediction of predictions) {
    for (const side of ['home', 'away']) {
      for (const group of ['lineups', 'injuries', 'injuryDetails']) {
        for (const player of prediction[group]?.[side] || []) {
          const name = typeof player === 'string' ? player : player.name || player.player;
          if (!name || !/\p{Script=Latin}/u.test(name)) continue;
          if (!names.has(name)) names.set(name, new Set());
          names.get(name).add(prediction.league);
        }
      }
    }
  }
  const missing = [...names].filter(([name]) => run(`translated(${JSON.stringify(name)})`) === name).sort(([a], [b]) => a.localeCompare(b)).map(([name, leagues]) => ({
    name, leagues: [...leagues].sort(),
    google: `https://www.google.com/search?q=${encodeURIComponent(name)}`,
    status: 'needs-source-review'
  }));
  const report = {snapshotAsOf: snapshot.asOf, totalLatinNames: names.size, translated: names.size - missing.length, missing};
  const output = new URL('../scripts/player-name-audit.json', import.meta.url);
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  console.log(`All leagues: ${report.translated}/${names.size} names mapped; ${missing.length} queued for source review.`);
}
