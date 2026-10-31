"""Galeb nad Jadranom v16 – ideas taken over from Soko v100 (step 1).

usage: python3 patch_v16.py <in index.html> <out index.html>

1. Sound preloading (Soko v89): fetch all SFX bytes after page load (before the first tap),
   decode them two at a time after the first tap; after an error wait 5 s before retrying.
2. Buttons (Soko v99): 44 px, own speaker / note icons, "off" = faded with a red slash;
   the language button moves up when the pause button is hidden.
3. Place badge (Soko v99): larger name on a dark plate with a gold rim; below it the route
   Pula → Dubrovnik as seven dots (visited in this flight / current) and "3/7".
4. Version mark "© by FG · v16".
"""
import sys

VERSION = '16'
src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, f'{n} x {old[:90]!r}'
    s = s.replace(old, new)


SPEAKER = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5h3.6L12.5 5v14l-4.9-4.5H4z" fill="currentColor"/>'
           '<path d="M15.5 8.6a4.6 4.6 0 0 1 0 6.8M18 6.2a8 8 0 0 1 0 11.6" fill="none" stroke="currentColor" '
           'stroke-width="1.9" stroke-linecap="round"/></svg>')
NOTE = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 17.2V6.3l9-2.3v10.9" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linejoin="round"/><ellipse cx="7.2" cy="17.4" rx="2.6" ry="2.1" fill="currentColor"/>'
        '<ellipse cx="16.2" cy="15.1" rx="2.6" ry="2.1" fill="currentColor"/></svg>')

# ------------------------------------------------------------------ 1. sound preloading
rep("""    try{
      const res=await fetch(GALEB_SFX_DATA[id]);
      if(!res.ok) throw new Error('sfx '+res.status);
      const raw=await res.arrayBuffer();
      const buf=await ac.decodeAudioData(raw.slice(0));
      sfxDecoded.set(id,buf);return buf;
    }catch(e){console.warn('Audio decode error:',id,e);return null;}""",
    """    try{
      let raw=sfxRaw.get(id);                          // v16: bytes may already be here (prefetch)
      if(!raw){
        const res=await fetch(GALEB_SFX_DATA[id]);
        if(!res.ok) throw new Error('sfx '+res.status);
        raw=await res.arrayBuffer();
      }
      const buf=await ac.decodeAudioData(raw.slice(0));
      sfxRaw.delete(id);
      sfxDecoded.set(id,buf);return buf;
    }catch(e){sfxRetry.set(id,performance.now()+5000);console.warn('Audio decode error:',id,e);return null;}""")
rep("""  if(sfxLoading.has(id)) return sfxLoading.get(id);
  const job=(async()=>{""",
    """  if(sfxLoading.has(id)) return sfxLoading.get(id);
  if((sfxRetry.get(id)||0)>performance.now()) return Promise.resolve(null);   // v16: after an error wait 5 s
  const job=(async()=>{""")
rep("""  let i=0;const next=()=>{if(i>=ids.length)return;decodeSfx(ids[i++]).finally(()=>setTimeout(next,0));};next();
}""",
    """  /* v16 (wie Soko v89): danach ALLE kurzen Effekte im Hintergrund dekodieren, je zwei gleichzeitig.
     Vorher wurde ein Effekt erst beim ersten Gebrauch geladen und verworfen, wenn das > 0,85 s dauerte. */
  const all=sfxOrder(ids);
  let i=0;const next=()=>{if(i>=all.length)return;decodeSfx(all[i++]).finally(()=>setTimeout(next,15));};next();next();
}
const sfxRaw=new Map(), sfxRetry=new Map();
function sfxOrder(first){
  const rest=Object.keys(GALEB_SFX_DATA).filter(id=>!id.startsWith('amb_')&&!first.includes(id));
  return first.filter(id=>!id.startsWith('amb_')).concat(rest);
}
/* v16: die Bytes schon vor dem ersten Tippen holen (dekodieren darf der Browser erst danach) */
function prefetchSfx(){
  const ids=sfxOrder(['sfx_galeb_flap_01','sfx_galeb_flap_02','sfx_galeb_flap_03','sfx_score_tick','sfx_gate_pass',
    'sfx_gate_clean','sfx_ui_start','sfx_ui_select']);
  let i=0;
  const next=()=>{
    if(i>=ids.length)return;const id=ids[i++];
    if(sfxRaw.has(id)||sfxDecoded.has(id)||sfxLoading.has(id))return next();
    fetch(GALEB_SFX_DATA[id]).then(r=>r.ok?r.arrayBuffer():null).then(d=>{if(d&&!sfxDecoded.has(id))sfxRaw.set(id,d);})
      .catch(()=>{}).then(()=>setTimeout(next,15));
  };
  next();next();
}
{const go=()=>setTimeout(prefetchSfx,1500);if(document.readyState==='complete')go();else window.addEventListener('load',go,{once:true});}""")

# ------------------------------------------------------------------ 2. buttons
rep('<button id="sound" class="nostart" aria-label="Zvuk">♪</button>',
    f'<button id="sound" class="nostart" aria-label="Zvuk">{SPEAKER}</button>')
rep('<button id="music" class="nostart" aria-label="Glazba">♫</button>',
    f'<button id="music" class="nostart" aria-label="Glazba">{NOTE}</button>')
rep("""  soundBtn.textContent = soundOn ? '♪' : '✕';
  soundBtn.style.opacity = soundOn ? '1' : '.5';""",
    """  soundBtn.classList.toggle('off', !soundOn);""")
rep("musicBtn.style.opacity=on?'1':'.4';", "musicBtn.classList.toggle('off',!on);")
rep("if(so==='0'){ soundOn=false; soundBtn.textContent='✕'; soundBtn.style.opacity='.5'; }",
    "if(so==='0'){ soundOn=false; soundBtn.classList.add('off'); }")
rep("  musicBtn.style.opacity = musicOn ? '1' : '.4';", "  musicBtn.classList.toggle('off', !musicOn);")

# ------------------------------------------------------------------ 3. place badge with route
rep("function setPlace(n){ if(placeEl) placeEl.textContent = n; }",
    """/* v16 (wie Soko v99): Ortsname gut lesbar, darunter die Route Pula → Dubrovnik:
   gefüllte Punkte = in diesem Flug besucht, heller Punkt = hier, dazu „3/7“. */
let placeRun = new Set();
function setPlace(n){
  if(!placeEl) return;
  if(state === 'playing') placeRun.add(n);
  const name = document.createElement('b'); name.textContent = n;
  const route = document.createElement('div'); route.className = 'route';
  for(const c of PUT_RED){
    const i = document.createElement('i');
    if(placeRun.has(c)) i.className = 'v';
    if(c === n) i.className = 'c';
    i.title = c; route.appendChild(i);
  }
  if(state === 'playing'){
    const cnt = document.createElement('span'); cnt.textContent = placeRun.size + '/' + PUT_RED.length;
    route.appendChild(cnt);
  }
  placeEl.replaceChildren(name, route);
}""")
rep("  state='playing'; score=0; scoreEl.textContent='0'; if(ac)MUSIC.play(cityTrack(),1.2);\n",
    "  placeRun = new Set();\n  state='playing'; score=0; scoreEl.textContent='0'; if(ac)MUSIC.play(cityTrack(),1.2);\n"
    "  setPlace(SCENES[sceneShown].name);                // v16: Ortsanzeige mit Route ab dem ersten Ort\n")

# ------------------------------------------------------------------ 4. version mark
rep('<div id="fg">© by FG</div>', f'<div id="fg">© by FG · v{VERSION}</div>')
rep('<meta name="theme-color" content="#10303A">',
    f'<meta name="theme-color" content="#10303A">\n<meta name="galeb-version" content="{VERSION}">')

# ------------------------------------------------------------------ styles
css = """<style>
/* ══ v16: Knöpfe und Ortsanzeige (Ideen aus Soko v99) ══ */
#sound,#music,#pause,#jezik{width:44px!important;height:44px!important;line-height:44px!important;
  display:grid;place-items:center;padding:0;}
#sound{top:calc(env(safe-area-inset-top,0px) + 10px)!important;}
#music{top:calc(env(safe-area-inset-top,0px) + 60px)!important;}
#pause{top:calc(env(safe-area-inset-top,0px) + 110px)!important;}
#jezik{top:calc(env(safe-area-inset-top,0px) + 160px)!important;}
#pause.off + #jezik{top:calc(env(safe-area-inset-top,0px) + 110px)!important;}
#sound svg,#music svg{width:21px;height:21px;display:block;filter:drop-shadow(0 1px 1px rgba(6,20,26,.8));}
#sound.off,#music.off{opacity:.6;}
#sound.off::after,#music.off::after{content:'';position:absolute;left:10px;right:10px;top:calc(50% - 1.5px);height:3px;
  border-radius:2px;background:#E0483E;transform:rotate(-45deg);box-shadow:0 0 0 1px rgba(10,30,38,.55);}
#place{top:calc(env(safe-area-inset-top,0px) + 6px)!important;padding:6px 10px 6px;border-radius:9px;
  background:rgba(12,38,46,.76);border:1px solid #D9B45A;box-shadow:0 3px 12px rgba(6,22,28,.45);
  opacity:1!important;max-width:40vw;line-height:1.15;text-transform:none!important;letter-spacing:0!important;}
#place:empty{display:none;}
#place b{display:block;font-size:15px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#FAF5E8;
  overflow-wrap:anywhere;}
#place .route{display:flex;gap:4px;justify-content:flex-end;align-items:center;margin-top:5px;}
#place .route i{width:7px;height:7px;border-radius:50%;border:1px solid rgba(233,217,168,.85);box-sizing:border-box;}
#place .route i.v{background:#E9D9A8;}
#place .route i.c{background:#F5C84C;border-color:#F5C84C;box-shadow:0 0 0 2px rgba(245,200,76,.35);}
#place .route span{margin-left:4px;font-size:11px;font-weight:600;color:#E9D9A8;letter-spacing:.04em;}
</style>
"""
rep('<body>\n<canvas id="c"></canvas>', css + '<body>\n<canvas id="c"></canvas>')
open(out, 'w', encoding='utf-8').write(s)
print('v16 written', out)
