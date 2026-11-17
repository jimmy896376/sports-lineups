import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function check(storage, inaccessible = false) {
  const elements = new Map();
  const element = () => ({listeners:{},addEventListener(type,fn){this.listeners[type]=fn;},setAttribute(){},innerHTML:'',textContent:''});
  const getElement = id => {if(!elements.has(id))elements.set(id,element());return elements.get(id);};
  const context = vm.createContext({document:{documentElement:{dataset:{}},getElementById:getElement,querySelector:element,addEventListener(){}},window:{setInterval(){}},atob,TextDecoder,Uint8Array});
  if(inaccessible)Object.defineProperty(context,'localStorage',{get(){throw new Error('SecurityError: sandboxed storage');}});
  else context.localStorage=storage;
  for(const file of ['football-ko.js','player-ko.js','win-probability.js','player-name-fallback.js','app.js'])vm.runInContext(fs.readFileSync(new URL('../dist/'+file,import.meta.url),'utf8').replace(/loadGames\(\);\s*$/,''),context);
  assert.equal(vm.runInContext('theme',context),storage?.getItem?.('sports-lineups-theme') || 'dark');
  assert.equal(typeof getElement('refresh').listeners.click,'function','Initialization must reach lineup event handlers');
  const before=context.document.documentElement.dataset.theme;
  getElement('theme').listeners.click();
  assert.notEqual(context.document.documentElement.dataset.theme,before,'Theme toggle must work without persistent storage');
}
check(undefined,true);
check({getItem(){return null;},setItem(){throw new Error('QuotaExceededError');}});
const saved=[];
check({getItem(){return 'light';},setItem(key,value){saved.push([key,value]);}});
assert.deepEqual(saved,[['sports-lineups-theme','dark']],'Keep theme persistence when storage is available');
console.log('Embedded storage: blocked access, blocked writes, initialization, theme toggle and normal persistence passed.');
