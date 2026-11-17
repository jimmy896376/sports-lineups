'use strict';
(function(root){
function hangulizeLatin(value) {
  const initial={g:'ㄱ',k:'ㅋ',c:'ㅋ',q:'ㅋ',d:'ㄷ',t:'ㅌ',b:'ㅂ',p:'ㅍ',f:'ㅍ',v:'ㅂ',m:'ㅁ',n:'ㄴ',r:'ㄹ',l:'ㄹ',s:'ㅅ',z:'ㅈ',j:'ㅈ',h:'ㅎ',w:'ㅇ',y:'ㅇ',x:'ㅋ'};
  const final={g:'ㄱ',k:'ㄱ',c:'ㄱ',q:'ㄱ',d:'ㄷ',t:'ㅅ',b:'ㅂ',p:'ㅂ',m:'ㅁ',n:'ㄴ',r:'ㄹ',l:'ㄹ',s:'ㅅ',z:'ㅅ',x:'ㄱ'};
  const vowels={a:'ㅏ',e:'ㅔ',i:'ㅣ',o:'ㅗ',u:'ㅜ',y:'ㅣ'};
  const clusters=[['tch','ch'],['sch','sh'],['sh','s'],['ch','c'],['th','s'],['ph','f'],['wh','w'],['ck','k'],['qu','kw'],['ee','i'],['ea','i'],['oo','u'],['ou','u'],['ow','aw'],['ai','e'],['ay','e'],['oi','o'],['oy','o'],['x','ks']];
  const initialIndex={'ㄱ':0,'ㄲ':1,'ㄴ':2,'ㄷ':3,'ㄸ':4,'ㄹ':5,'ㅁ':6,'ㅂ':7,'ㅃ':8,'ㅅ':9,'ㅆ':10,'ㅇ':11,'ㅈ':12,'ㅉ':13,'ㅊ':14,'ㅋ':15,'ㅌ':16,'ㅍ':17,'ㅎ':18};
  const vowelIndex={'ㅏ':0,'ㅐ':1,'ㅑ':2,'ㅒ':3,'ㅓ':4,'ㅔ':5,'ㅕ':6,'ㅖ':7,'ㅗ':8,'ㅘ':9,'ㅙ':10,'ㅚ':11,'ㅛ':12,'ㅜ':13,'ㅝ':14,'ㅞ':15,'ㅟ':16,'ㅠ':17,'ㅡ':18,'ㅢ':19,'ㅣ':20};
  const finalIndex={'ㄱ':1,'ㄴ':4,'ㄷ':7,'ㄹ':8,'ㅁ':16,'ㅂ':17,'ㅅ':19,'ㅇ':21};
  const compose=(a,v,b)=>String.fromCharCode(0xac00+((initialIndex[a]??11)*21+(vowelIndex[v]??20))*28+(finalIndex[b]||0));
  return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[A-Za-z]+/g,word=>{
    let text=word.toLowerCase();
    for(const [from,to] of clusters) text=text.replaceAll(from,to);
    text=text.replace(/c(?=[eiy])/g,'s');
    if(text.length>3&&/[^aeiou]e$/.test(text)) text=text.slice(0,-1);
    const nuclei=[]; let pending='';
    for(const char of text){
      if(vowels[char]){nuclei.push({onset:pending,vowel:vowels[char],coda:''});pending='';}
      else if(initial[char]) pending+=char;
    }
    if(!nuclei.length) return [...word].map(char=>initial[char.toLowerCase()]?compose('ㅇ','ㅡ','')+compose(initial[char.toLowerCase()],'ㅣ',''):char).join('');
    for(let i=0;i<nuclei.length;i++){
      const run=nuclei[i].onset;
      if(!run) { nuclei[i].onset=''; continue; }
      if(i===0){nuclei[i].onset=run.length>1?run[0]:run.at(-1); if(run.length>1) nuclei[i].coda=final[run[0]]||'';}
      else if(run.length>1){
        const stopLiquid=run.length===2&&['k','p','t','b','g','d'].includes(run[0])&&['l','r'].includes(run[1]);
        nuclei[i-1].coda=stopLiquid||run==='rn'||run==='rs'?'':final[run[0]]||'';
        nuclei[i].onset=run.at(-1);
        if(stopLiquid) nuclei[i-1].insert=compose(initial[run[0]],'ㅡ','');
      }
      else nuclei[i].onset=run;
    }
    const tail=pending;
    let suffix='';
    if(tail){
      const last=nuclei.at(-1);
      if(tail==='r') suffix=compose('ㄹ','ㅡ','');
      else if(tail.length>1){last.coda=tail[0]==='r'?'':final[tail[0]]||'';suffix=[...tail.slice(1)].map(char=>compose(initial[char]||'ㅇ','ㅡ','')).join('');}
      else last.coda=final[tail[0]]||'';
    }
  return nuclei.map(part=>compose(initial[part.onset]||'ㅇ',part.vowel,part.coda)+(part.insert||'')).join('')+suffix;
  });
}
function createPlayerNameFallback(reviewed){
  const words=new Map();
  const normalize=word=>word.normalize('NFD').replace(/\p{M}/gu,'').toLowerCase();
  const distance=(left,right)=>{
    let row=Array.from({length:right.length+1},(_,index)=>index);
    for(let i=0;i<left.length;i++){
      const next=[i+1];
      for(let j=0;j<right.length;j++)next.push(Math.min(next[j]+1,row[j+1]+1,row[j]+(left[i]!==right[j])));
      row=next;
    }
    return row[right.length];
  };
  for(const [original,korean] of Object.entries(reviewed||{})){
    const source=original.split(/[\s-]+/),target=korean.split(/[\s-]+/);
    if(source.length!==target.length)continue;
    if(source.length===2){
      const phonetic=source.map(hangulizeLatin);
      const direct=distance(phonetic[0],target[0])+distance(phonetic[1],target[1]);
      const reversed=distance(phonetic[0],target[1])+distance(phonetic[1],target[0]);
      if(reversed+1<direct)target.reverse();
    }
    source.forEach((word,index)=>{
      if(!/^[A-Za-zÀ-ž]+$/.test(word)||!/^[가-힣]+$/.test(target[index]))return;
      const key=normalize(word),existing=words.get(key);
      words.set(key,existing===undefined?target[index]:existing===target[index]?existing:null);
    });
  }
  const special={'Ł':'L','ł':'l','Ø':'O','ø':'o','Æ':'Ae','æ':'ae','Đ':'D','đ':'d','Ð':'D','ð':'d','Þ':'Th','þ':'th','ß':'ss','ı':'i','Ŋ':'Ng','ŋ':'ng'};
  return name=>String(name||'').replace(/[\p{Script=Latin}\p{M}]+/gu,word=>{
    const latin=word.normalize('NFD').replace(/\p{M}/gu,'').replace(/[ŁłØøÆæĐđÐðÞþßıŊŋ]/g,char=>special[char]);
    return words.get(latin.toLowerCase())||hangulizeLatin(latin);
  });
}
root.createPlayerNameFallback=createPlayerNameFallback;
if(typeof module!=='undefined'&&module.exports)module.exports=createPlayerNameFallback;
})(globalThis);
