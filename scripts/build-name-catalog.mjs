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
    } else if(row.method==='namuwiki-team-roster-v1') {
      assert.ok(row.sources.length===1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='namu.moe' && url.pathname.startsWith('/w/') && s.domain==='namu.moe' && s.teamMatched && s.englishNameMatched && s.rowMatched && s.contentHash;
      }),'NamuWiki roster needs exact team and bilingual player row');
    } else if(row.method==='google-search-result-v1') {
      assert.ok(row.sources.length>=1 && row.sources.every(s=>{
        const url=new URL(s.url);
        return url.protocol==='https:' && url.hostname==='www.google.com' && url.pathname==='/search' && s.domain==='google.com' && s.teamMatched && (s.bilingualNameMatched || s.knowledgePanelMatched) && s.contentHash;
      }),'Google result needs player identity evidence');
    } else {
      assert.equal(row.method,'independent-bilingual-sources-v1');
      assert.ok(row.sources.length>=2 && new Set(row.sources.map(s=>s.domain)).size>=2 && row.sources.some(s=>s.teamMatched),'Automatic name needs independent identity evidence');
      assert.ok(row.sources.every(s=>s.bilingualNameMatched && /^https:\/\//.test(s.url)),'Automatic name lacks source evidence');
    }
    automatic[row.name]=row.korean;
  }
  // Human-reviewed spellings always take precedence over automated additions.
  vm.runInContext(fs.readFileSync(new URL('dist/football-ko.js',root),'utf8'),context);
  const manual={...vm.runInContext('footballKo',context),...vm.runInContext('playerKo',context),...read('scripts/player-name-review.json').userOverrides};
  const normalized=name=>name.normalize('NFD').replace(/[\u0300-\u036f]/g,'').normalize('NFC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const manualKeys=new Set(Object.keys(manual).map(normalized));
  const players = {...Object.fromEntries(Object.entries(automatic).filter(([name])=>!manualKeys.has(normalized(name)))),...manual};
  for (const dictionary of [teams,players]) {
    for (const [name,korean] of Object.entries(dictionary)) {
      assert.ok(name && typeof korean==='string' && korean.length<=160 && /\p{Script=Hangul}/u.test(korean),`Invalid approved name: ${name}`);
    }
  }
  const teamEnglish=Object.fromEntries(review.entries.filter(row=>row.english).map(row=>[row.name,row.english]));
  const previous = fs.existsSync(new URL('dist/name-catalog.json',root)) ? read('dist/name-catalog.json') : {};
  const unchanged = ['teams','teamEnglish','players'].every(key=>JSON.stringify(previous[key])===JSON.stringify({teams,teamEnglish,players}[key]));
  const catalog = {schemaVersion:1,generatedAt:unchanged && previous.generatedAt ? previous.generatedAt : new Date().toISOString(),teams,teamEnglish,players};
  write('dist/team-ko.json',teams);
  write('dist/name-catalog.json',catalog);
  console.log(`Approved name catalog: ${Object.keys(teams).length} team aliases, ${Object.keys(players).length} player aliases.`);
}
