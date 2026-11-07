import assert from 'node:assert/strict';
import {inspect} from './health.mjs';

const now=Date.parse('2026-11-05T00:00:00Z');
const team=side=>({side,id:side,name:side,logo:'https://example.com/logo.png',players:[{name:'선수',position:'',number:'',flag:''}],status:'predicted',injuries:[]});
const match={id:'kbo-1',league:'kbo',leagueName:'KBO',sport:'야구',kickoff:now+3600000,checkedAt:new Date(now).toISOString(),teams:[team('home'),team('away')],recentForm:{home:['W'],away:['L']},records:{home:{record:'1-0',sideRecord:'1-0'},away:{record:'0-1',sideRecord:'0-1'}}};
const feed={schemaVersion:1,asOf:new Date(now).toISOString(),pollSeconds:60,matches:[match]};
assert.deepEqual(inspect(feed,{asOf:feed.asOf},now).issues,[]);
assert.deepEqual(inspect(feed,{asOf:feed.asOf},now).missingStatsByLeague.kbo,{recentForm:0,seasonRecord:0,venueRecord:0});
assert.deepEqual(inspect({...feed,matches:[{...match,recentForm:{},records:{}}]},{asOf:feed.asOf},now).missingStatsByLeague.kbo,{recentForm:2,seasonRecord:2,venueRecord:2});
assert.match(inspect(feed,{asOf:feed.asOf},now+46*60000).issues.join(' '),/feed age/);
assert.match(inspect({...feed,matches:[{...match,teams:[{...team('home'),logo:''},team('away')]}]},{asOf:feed.asOf},now).issues.join(' '),/logo/);
assert.match(inspect({...feed,matches:[{...match,recentForm:{},records:{}}]},{asOf:feed.asOf},now).issues.join(' '),/KBO recent form/);
assert.match(inspect(feed,{asOf:feed.asOf,sourceStatus:{kbo:{fresh:false,checkedAt:feed.asOf}}},now).issues.join(' '),/source unavailable or stale: kbo/);
console.log('PASS feed freshness, source status, logo, and KBO record checks');
