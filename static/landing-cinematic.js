/* Native scrolling drives the editorial scenes; content is visible without JS. */
(() => {
 const root=document.querySelector('.push-cinema'); if(!root)return;
 const media=matchMedia('(prefers-reduced-motion: reduce)');
 const button=root.querySelector('.cinema-motion-control');
 const hero=root.querySelector('.cinema-hero');
 const scene=root.querySelector('.cinema-scene');
 const gallery=root.querySelector('.cinema-gallery');
 const track=root.querySelector('.cinema-gallery-track');
 const close=root.querySelector('.cinema-close');
 const purpose=root.querySelector('.cinema-purpose');
 const panels=[...root.querySelectorAll('.cinema-gallery-panel')];
 const film=root.querySelector('video');
 let paused=false,frame=0; const animations=[];
 const clamp=x=>Math.max(0,Math.min(1,x));
 function draw(){
  frame=0;if(paused||media.matches||document.hidden)return;
  const h=hero.getBoundingClientRect(), g=gallery.getBoundingClientRect(), p=purpose.getBoundingClientRect();
  const panelRects=panels.map(el=>el.getBoundingClientRect());
  const desktop=innerWidth>850;
  const progress=clamp(-g.top/Math.max(1,g.height-innerHeight+76));
  const distance=desktop?Math.max(0,track.scrollWidth-gallery.clientWidth):0;
  scene.style.transform=`translate3d(0,${Math.min(90,Math.max(0,-h.top)*.16)}px,0) scale(1.08)`;
  gallery.style.setProperty('--gallery-shift',`${-distance*progress}px`);
  const reveal=clamp((innerHeight-p.top)/(innerHeight+p.height));
  purpose.style.setProperty('--print-shift-one',`${(reveal-.5)*-38}px`);
  purpose.style.setProperty('--print-shift-two',`${(reveal-.5)*30}px`);
  panels.forEach((el,i)=>el.style.setProperty('--scene-drift',`${desktop?Math.max(-18,Math.min(18,-panelRects[i].left*.016)):0}px`));
  hero.style.setProperty('--hero-fade',String(1-clamp(-h.top/Math.max(1,h.height))*.65));
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(draw)}
 function mode(){
  root.classList.toggle('motion-on',!paused&&!media.matches);root.classList.toggle('motion-suspended',document.hidden);
  button.hidden=media.matches;button.textContent=paused?'Resume motion':'Pause motion';button.setAttribute('aria-pressed',String(paused));
  if(paused||media.matches){scene.style.transform='';gallery.style.removeProperty('--gallery-shift');purpose.style.removeProperty('--print-shift-one');purpose.style.removeProperty('--print-shift-two');hero.style.removeProperty('--hero-fade');panels.forEach(el=>el.style.removeProperty('--scene-drift'));animations.forEach(a=>a.finish())}
  schedule();
 }
 button.addEventListener('click',()=>{paused=!paused;mode()});media.addEventListener('change',mode);
 addEventListener('scroll',schedule,{passive:true});addEventListener('resize',schedule);
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&film)film.pause();mode()});
 if('IntersectionObserver'in window){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
   entry.target.classList.toggle('is-in-view',entry.isIntersecting);
   if(entry.target===film&&!entry.isIntersecting)film.pause();
   if(entry.isIntersecting&&entry.target.matches('.cinema-film,.cinema-payment')&&!entry.target.dataset.shutterSeen){entry.target.dataset.shutterSeen='true';if(!paused&&!media.matches)entry.target.classList.add('shutter-enter')}
   if(entry.isIntersecting&&entry.target.matches('.cinema-steps li,.cinema-section-head')&&!entry.target.dataset.motionSeen){
    entry.target.dataset.motionSeen='true';
    if(!paused&&!media.matches){animations.push(entry.target.animate([{transform:'translateY(24px)',opacity:.5},{transform:'translateY(0)',opacity:1}],{duration:550,easing:'cubic-bezier(0.16, 1, 0.3, 1)'}))}
   }
  }),{threshold:.12});
  [hero,film,close,root.querySelector('.cinema-film'),root.querySelector('.cinema-payment'),...root.querySelectorAll('.cinema-steps li,.cinema-section-head')].filter(Boolean).forEach(el=>observer.observe(el));
 }
 mode();
})();
