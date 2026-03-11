/**
 * 神奈川ナース転職 — 転職診断UI (vanilla JS, <5KB)
 */
(function(){
'use strict';
var L='https://lin.ee/oUgDB3x',D=null,A={s:'',a:'',t:''},C;
fetch(new URL('jobs-summary.json',document.currentScript.src).href)
.then(function(r){return r.json()}).then(function(d){D=d}).catch(function(){});
var Q=[
{k:'s',t:'あなたの職種は？',e:'shindan_q1',ek:'shikaku',o:[
{l:'正看護師',v:'kango'},{l:'准看護師',v:'junkango'},
{l:'助産師',v:'josanshi'},{l:'保健師',v:'hokenshi'}]},
{k:'a',t:'希望エリアは？',e:'shindan_q2',ek:'area',o:[
{l:'横浜・川崎',v:'yokohama_kawasaki'},{l:'湘南・鎌倉',v:'shonan_kamakura'},
{l:'小田原・西湘',v:'odawara_seisho'},{l:'相模原・県央',v:'sagamihara_kenoh'},
{l:'横須賀・三浦',v:'yokosuka_miura'}]},
{k:'t',t:'転職したい時期は？',e:'shindan_q3',ek:'timing',o:[
{l:'すぐにでも',v:'urgent'},{l:'3ヶ月以内',v:'3months'},
{l:'半年以内',v:'6months'},{l:'情報収集中',v:'info'}]}
];
function ga(e,p){if(typeof gtag==='function')gtag('event',e,p||{})}
function $(tag,cls,h){var e=document.createElement(tag);if(cls)e.className=cls;if(h)e.innerHTML=h;return e}
function fi(n){n.style.opacity='0';n.style.transition='opacity .3s';n.offsetHeight;n.style.opacity='1'}

function prog(s){
var w=$('div','shindan-progress'),b=$('div','shindan-progress-bar');
b.style.width=Math.round((s+1)/3*100)+'%';w.appendChild(b);
w.appendChild($('div','shindan-progress-label',(s+1)+' / 3'));return w;
}

function step(i){
var q=Q[i];C.innerHTML='';
var s=$('div','shindan-step');s.appendChild(prog(i));
s.appendChild($('h3','shindan-title',q.t));
var g=$('div','shindan-options');
q.o.forEach(function(o){
var b=$('button','shindan-btn',o.l);b.type='button';
b.addEventListener('click',function(){
A[q.k]=o.v;
g.querySelectorAll('.shindan-btn').forEach(function(x){x.classList.remove('selected')});
b.classList.add('selected');
var p={};p[q.ek]=o.v;ga(q.e,p);
setTimeout(function(){i<2?step(i+1):result()},200);
});g.appendChild(b);
});
s.appendChild(g);C.appendChild(s);fi(s);
}

function card(j,bl){
var c=$('div','shindan-job-card'+(bl?' blurred':''));
var tags=[];if(j.type)tags.push(j.type);if(j.bonus)tags.push('賞与あり');if(j.holidays)tags.push('年休'+j.holidays);
c.innerHTML='<div class="shindan-job-name">'+(j.title||j.name||'非公開求人')+'</div>'+
'<div class="shindan-job-salary">'+(j.salary||'')+'</div>'+
(tags.length?'<div class="shindan-job-tags">'+tags.map(function(t){return'<span>'+t+'</span>'}).join('')+'</div>':'');
return c;
}

function result(){
C.innerHTML='';
var ar=D&&D.areas?D.areas:D,d=ar&&ar[A.a]&&ar[A.a].count>0?ar[A.a]:ar&&ar.all?ar.all:null,
ct=d?d.count:0,sn=d?d.salary_min:350,sx=d?d.salary_max:550;
ga('shindan_complete',{match_count:ct,area:A.a,shikaku:A.s});
var r=$('div','shindan-result'),p=prog(2);
p.querySelector('.shindan-progress-bar').style.width='100%';r.appendChild(p);
r.appendChild($('h3','shindan-result-heading','あなたにマッチする求人 <strong>'+ct+'件</strong>'));
r.appendChild($('div','shindan-salary-range','年収 <strong>'+sn+'〜'+sx+'万円</strong>'));
if(A.t==='urgent')r.appendChild($('div','shindan-badge','急募求人あり'));
if(d&&d.sample)r.appendChild(card(d.sample,false));
if(d&&d.blurred)d.blurred.forEach(function(j){r.appendChild(card(j,true))});
var txt=A.t==='info'?'まずは情報だけ受け取る':'LINEで求人を受け取る',
u=L+'?utm_source=lp&utm_medium=shindan&utm_content='+encodeURIComponent(A.s+'_'+A.a+'_'+A.t),
a=$('a','shindan-cta',txt);
a.href=u;a.target='_blank';a.rel='noopener';
a.addEventListener('click',function(){
ga('shindan_line_click',{area:A.a,shikaku:A.s,timing:A.t});
if(typeof fbq==='function')fbq('track','Lead');
});
r.appendChild(a);C.appendChild(r);fi(r);
}

function init(){C=document.getElementById('shindan-container');if(!C)return;ga('shindan_start');step(0)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
