const {JSDOM}=require('jsdom'),fs=require('node:fs'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync('dist/qdii.json','utf8'));
async function boot(fail=false,snapshot=data){const dom=new JSDOM(fs.readFileSync('dist/index.html','utf8'),{url:'https://ndx5s.test/#qdii',runScripts:'outside-only'}),w=dom.window;
 w.fetch=async url=>({ok:!fail,json:async()=>url==='/qdii.json'?JSON.parse(JSON.stringify(snapshot)):{success:true}});w.console.error=()=>{};w.eval(fs.readFileSync('web/qdii.js','utf8'));await new Promise(r=>setTimeout(r,30));return w;}
(async()=>{
 const w=await boot(),d=w.document;assert.equal(d.querySelector('#ndx-view').hidden,false);assert.equal(d.querySelector('#qdii-view').hidden,false);
 const cards=[...d.querySelectorAll('.qdii-group')];
 assert.deepEqual(cards.map(card=>card.getAttribute('aria-label')),['纳指有额度','标普有额度','纳指无额度','标普无额度']);
 assert.equal(d.querySelectorAll('.qdii-fund-row').length,data.group_count);
 assert.equal(d.querySelector('#qdii-list h3, .qdii-share, .qdii-index, #qdii-metrics'),null);
 for(const g of data.groups){
  const index=g.index==='ndx'?'纳指':'标普';
  const available=g.shares.some(s=>s.status!=='paused');
  const card=cards.find(e=>e.getAttribute('aria-label')===index+(available?'有额度':'无额度'));
  const row=[...card.querySelectorAll('.qdii-fund-row')].find(e=>e.firstElementChild.textContent===g.name);
  assert.ok(row,g.name);
  assert.equal(row.children.length,2);
  assert.ok(row.children[1].classList.contains('qdii-limit'));
 }
 const mixed=await boot(false,{...data,groups:[
  {name:'限额测试',index:'ndx',shares:[{status:'limited',limit_yuan:100},{status:'limited',limit_yuan:200}]},
  {name:'不限测试',index:'spx',shares:[{status:'limited',limit_yuan:100},{status:'unlimited'}]},
  {name:'暂停测试',index:'ndx',shares:[{status:'paused'},{status:'paused'}]}
 ]});
 assert.deepEqual([...mixed.document.querySelectorAll('.qdii-limit')].map(e=>e.textContent),['200元','不限购','暂停申购']);
 for(const selector of ['#nav-ndx','#nav-qdii','#qdii-captured','#qdii-source-age','#qdii-warning','#qdii-search','.qdii-filters','#qdii-count','.qdii-history'])assert.equal(d.querySelector(selector),null);
 assert.equal(d.querySelector('#qdii-title').textContent,'QDII申购额度');assert.ok(d.querySelector('#ndx-view').compareDocumentPosition(d.querySelector('#qdii-view')) & w.Node.DOCUMENT_POSITION_FOLLOWING);

 const bad=await boot(true);assert.equal(bad.document.querySelector('#qdii-error').hidden,false);assert.equal(bad.document.querySelector('#qdii-content').hidden,true);
 console.log('PASS: QDII four untitled groups, per-fund quota, single-page layout and fetch failure');
})().catch(e=>{console.error(e);process.exitCode=1});
