'use strict';
(()=>{
const byId=id=>document.getElementById(id),node=(tag,cls,value)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(value!==undefined)e.textContent=value;return e;};
let data=null,loading=false;
const money=v=>Number(v).toLocaleString('zh-CN',{maximumFractionDigits:2})+'元';
function quota(shares){
 if(shares.some(share=>share.status==='unlimited')) return {available:true,label:'不限购',tone:'ok'};
 const limits=shares.filter(share=>share.status==='limited').map(share=>share.limit_yuan);
 if(limits.length) return {available:true,label:money(Math.max(...limits)),tone:'warn'};
 return {available:false,label:'暂停申购',tone:'mut'};
}
function render(){
 const sections=[
  {index:'ndx',label:'纳指',available:true},
  {index:'spx',label:'标普',available:true},
  {index:'ndx',label:'纳指',available:false},
  {index:'spx',label:'标普',available:false}
 ];
 const funds=data.groups.map(group=>({group,quota:quota(group.shares)}))
  .sort((a,b)=>a.group.name.localeCompare(b.group.name,'zh-CN'));
 const cards=sections.map(section=>{
  const card=node('ul','qdii-group');
  card.setAttribute('aria-label',section.label+(section.available?'有额度':'无额度'));
  for(const fund of funds){
   if(fund.group.index!==section.index||fund.quota.available!==section.available)continue;
   const row=node('li','qdii-fund-row');
   row.append(node('span','qdii-fund-name',fund.group.name),
    node('span','qdii-index',section.label),
    node('span','qdii-limit '+fund.quota.tone,fund.quota.label));
   card.append(row);
  }
  if(!card.children.length)card.append(node('li','qdii-empty','暂无基金'));
  return card;
 });
 byId('qdii-list').replaceChildren(...cards);
}
async function load(){
 if(loading||data)return;loading=true;byId('qdii-loading').hidden=false;byId('qdii-error').hidden=true;
 try{
  const r=await fetch('/qdii.json',{cache:'no-store'});if(!r.ok)throw Error('QDII HTTP '+r.status);data=await r.json();if(data.schema_version!==1||!Array.isArray(data.groups)||!data.groups.length)throw Error('QDII schema');
  byId('qdii-content').hidden=false;render();
 }catch(e){data=null;byId('qdii-error').hidden=false;byId('qdii-content').hidden=true;console.error(e);}
 finally{loading=false;byId('qdii-loading').hidden=true;}
}
byId('qdii-retry').onclick=load;
load();
})();
