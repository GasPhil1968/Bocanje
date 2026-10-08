"""Integrate file-based music + gapless ambience into the SFX build of Galeb nad Jadranom and
remove every remaining run-time synthesizer.   usage: integrate.py <in.html> <assets.json> <out.html>"""
import sys, json, re

src, assets_path, out = sys.argv[1:4]
s = open(src, encoding='utf-8').read()
A = json.load(open(assets_path))


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, f'expected {count} x {old[:80]!r}, found {n}'
    s = s.replace(old, new)


def cut(start, end, new='', include_end=True):
    """replace text from `start` up to (and incl.) `end` with `new`; both anchors must be unique."""
    global s
    assert s.count(start) == 1, f'start anchor not unique: {start[:70]!r} ({s.count(start)})'
    i = s.index(start)
    j = s.index(end, i)
    if include_end: j += len(end)
    s = s[:i] + new + s[j:]


# ------------------------------------------------------------------ 1. data: music + gapless ambience
music = {k: v['b64'] for k, v in A.items() if v['kind'] == 'music'}
loops = {k: [v['pre'] / v['sr'], v['n'] / v['sr']] for k, v in A.items()}
data_script = ('<script>/* Background music (rendered files, MP3 with wrap-around padding for gapless loops) */\n'
               'window.GALEB_MUSIC_DATA=' + json.dumps(music, separators=(',', ':')) + ';\n'
               'window.GALEB_LOOPS=' + json.dumps(loops, separators=(',', ':')) + ';\n</script>\n')
anchor = '<script>/* Alte Canvas-Vogelbibliothek entfernt: nur PNG-Sprites aktiv. */</script>'
rep(anchor, data_script + anchor)

# replace the ambience MP3s inside GALEB_SFX_DATA with the padded versions
m = re.search(r'const GALEB_SFX_DATA = (\{.*?\});\n', s, re.S)
sfx = json.loads(m.group(1))
for k, v in A.items():
    if v['kind'] == 'amb':
        assert k in sfx, k
        sfx[k] = v['b64']
s = s[:m.start(1)] + json.dumps(sfx, separators=(',', ':')) + s[m.end(1):]

# ------------------------------------------------------------------ 2. decoding: trim MP3 encoder delay on one-shots
rep("      const buf=await ac.decodeAudioData(bytes.buffer);\n      sfxDecoded.set(id,buf);return buf;",
    "      const buf=await ac.decodeAudioData(bytes.buffer);\n"
    "      buf.__lead=GALEB_LOOPS[id]?0:leadIn(buf);        // MP3 encoder delay: start at the first sound\n"
    "      sfxDecoded.set(id,buf);return buf;")
rep("function playSfx(id,options={}){",
    "/* MP3 decoders keep ~25-50 ms of encoder delay in front of the sound; skip it so taps stay tight */\n"
    "function leadIn(buf){\n"
    "  const d=buf.getChannelData(0),lim=Math.min(d.length,Math.floor(buf.sampleRate*.12));\n"
    "  let pk=0;for(let i=0;i<Math.min(d.length,buf.sampleRate*.5);i++){const a=Math.abs(d[i]);if(a>pk)pk=a;}\n"
    "  const thr=Math.max(1e-4,pk*.004);\n"
    "  for(let i=0;i<lim;i++)if(Math.abs(d[i])>thr)return Math.max(0,i-24)/buf.sampleRate;\n"
    "  return 0;\n"
    "}\n"
    "function playSfx(id,options={}){")
rep("      src.start();\n    }catch(e){console.warn('SFX playback error:',id,e);}",
    "      src.start(0,buf.__lead||0);\n    }catch(e){console.warn('SFX playback error:',id,e);}")
# ambience loops: loop exactly the original period inside the padded file
rep("        const src=ac.createBufferSource();src.buffer=buf;src.loop=true;",
    "        const src=ac.createBufferSource();src.buffer=buf;src.loop=true;\n"
    "        const lp=GALEB_LOOPS[id];if(lp){src.loopStart=lp[0];src.loopEnd=lp[0]+lp[1];}")
rep("        g.gain.setTargetAtTime(vol,t0,.65);src.start(t0);",
    "        g.gain.setTargetAtTime(vol,t0,.65);src.start(t0,lp?lp[0]+Math.random()*lp[1]*.9:0);")

# ------------------------------------------------------------------ 3. the music player
music_js = r"""
/* ══════════ Hintergrundmusik: gerenderte Stücke statt Echtzeit-Synthese ══════════
   Ein Stück pro Ort (mit synchroner Intensitätsspur für die Serie), Menü, Fever und
   Endbildschirm. Jede Datei loopt sample-genau über loopStart/loopEnd. */
const CITY_TRACK = {'Split':'mus_city_split','Dubrovnik':'mus_city_dubrovnik','Šibenik':'mus_city_sibenik',
  'Makarska':'mus_city_makarska','Zadar':'mus_city_zadar','Pula':'mus_city_pula'};
const cityTrack = () => CITY_TRACK[SCENE().name] || 'mus_city_split';
const MUSIC = (() => {
  const bufs = new Map(), loading = new Map();
  let out = null, cur = null, want = null;
  const VOL = .75;
  function decode(id){
    if(bufs.has(id)) return Promise.resolve(bufs.get(id));
    if(loading.has(id)) return loading.get(id);
    const job = (async () => {
      try{
        const str = atob(window.GALEB_MUSIC_DATA[id]);
        const bytes = new Uint8Array(str.length);
        for(let i=0;i<str.length;i++) bytes[i] = str.charCodeAt(i);
        const buf = await ac.decodeAudioData(bytes.buffer);
        bufs.set(id, buf); return buf;
      }catch(e){ console.warn('Music decode error:', id, e); return null; }
      finally{ loading.delete(id); }
    })();
    loading.set(id, job); return job;
  }
  function bus(){
    if(!out){ out = ac.createGain(); out.gain.value = musicOn ? 1 : 0; out.connect(busMusic); }
    return out;
  }
  function voice(id, buf, when, offset){
    const lp = GALEB_LOOPS[id];
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
    src.loopStart = lp[0]; src.loopEnd = lp[0] + lp[1];
    const g = ac.createGain(); g.gain.value = 0;
    src.connect(g); g.connect(bus());
    src.start(when, lp[0] + offset);
    return {src, g};
  }
  function fadeOut(v, fade){
    if(!v) return;
    const t = ac.currentTime;
    for(const x of [v.base, v.layer]) if(x){
      x.g.gain.cancelScheduledValues(t); x.g.gain.setValueAtTime(x.g.gain.value, t);
      x.g.gain.linearRampToValueAtTime(0, t + fade);
      try{ x.src.stop(t + fade + .05); }catch(e){}
    }
  }
  async function play(id, fade = 2.0){
    if(!ac || !window.GALEB_MUSIC_DATA[id]) return;
    want = id;
    if(cur && cur.id === id) return;
    const layerId = window.GALEB_MUSIC_DATA[id + '_layer'] ? id + '_layer' : null;
    const [b, l] = await Promise.all([decode(id), layerId ? decode(layerId) : null]);
    if(!b || want !== id || (cur && cur.id === id)) return;
    const t = ac.currentTime + .03;
    const old = cur;
    const base = voice(id, b, t, 0);
    base.g.gain.setValueAtTime(0, t); base.g.gain.linearRampToValueAtTime(VOL, t + fade);
    const layer = l ? voice(layerId, l, t, 0) : null;           // same start time -> lock-step
    cur = {id, base, layer};
    setLayer(state === 'playing' ? nizLayer() : 0, .5);
    fadeOut(old, Math.max(.3, fade * .8));
    // free the decoded audio of cities left behind (one minute of stereo is ~20 MB)
    // (only when a new city starts: fever and end screen keep the current city ready)
    if(id.startsWith('mus_city'))
      for(const k of [...bufs.keys()]) if(k.startsWith('mus_city') && k !== id && k !== layerId) bufs.delete(k);
  }
  function stop(fade = 1.5){ want = null; if(cur){ fadeOut(cur, fade); cur = null; } }
  function setLayer(level, tc = .35){
    if(!cur || !cur.layer || !ac) return;
    const target = [0, .45, .7, .9][Math.max(0, Math.min(3, level|0))] * VOL;
    cur.layer.g.gain.setTargetAtTime(target, ac.currentTime, tc);
  }
  function setOn(on){ if(ac) bus().gain.setTargetAtTime(on ? 1 : 0, ac.currentTime, .2); }
  function duck(db = -7, hold = 1.5){
    if(!ac || !musicOn) return;
    const g = bus().gain, t = ac.currentTime, low = Math.pow(10, db / 20);
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(low, t + .25); g.setValueAtTime(low, t + hold); g.linearRampToValueAtTime(1, t + hold + 1);
  }
  function preload(id){ if(ac && window.GALEB_MUSIC_DATA[id]) decode(id); }
  return {play, stop, setLayer, setOn, duck, preload, get current(){ return cur && cur.id; }, get wanted(){ return want; }};
})();
/* Tab oder App im Hintergrund: Klang anhalten, beim Zurückkommen fortsetzen */
document.addEventListener('visibilitychange', () => {
  if(!ac) return;
  if(document.hidden){ if(ac.state === 'running') ac.suspend().catch(()=>{}); }
  else if(ac.state === 'suspended') ac.resume().catch(()=>{});
});
/* Der erste Tipp weckt die Musik passend zum Zustand */
function musicKick(){
  if(!ac || MUSIC.current || MUSIC.wanted) return;
  MUSIC.play(state === 'playing' ? cityTrack() : state === 'dead' ? 'mus_end_screen' : 'mus_menu', 1.2);
}
"""
rep("\nlet ac=null, noiseGain=null, master=null;", music_js + "\nlet ac=null, noiseGain=null, master=null;")

# ------------------------------------------------------------------ 4. remove the synthesizers
cut("/* Hall aus abklingendem Rauschen — eine Steinschlucht ohne Aufnahme */\nfunction makeIR(secs, decay){",
    "  return b;\n}\n", '')
rep("  // Music-only reverb: the imported effects remain dry, with their own tails.\n"
    "  const conv=ac.createConvolver();conv.buffer=makeIR(1.4,2.7);\n"
    "  wet=ac.createGain();wet.gain.value=.13;conv.connect(wet);wet.connect(master);\n"
    "  sendMusic=ac.createGain();sendMusic.gain.value=.18;busMusic.connect(sendMusic);sendMusic.connect(conv);\n",
    "  // Kein künstlicher Hall mehr: Musik und Effekte bringen ihren Raum als Aufnahme mit.\n")
cut("function setRoom(){\n  if(!ac)return;\n  if(wet)wet.gain.setTargetAtTime(.13,ac.currentTime,.7);",
    "  refreshAmbient();\n}\n", "function setRoom(){\n  if(!ac)return;\n  refreshAmbient();\n}\n")
cut("/* Gezupfte Saite nach Karplus-Strong — klingt wie eine Šargija, nicht wie ein Piepton */\nconst pluckCache = {};",
    "let beepFenster = 0, beepZahl = 0;\n", '')
rep("audioInit(); musicStart(); musicSet(!musicOn);", "audioInit(); musicSet(!musicOn); musicKick();")
cut("/* ══════════ Musik: Klapa, poskočica und die istrische Zweistimmigkeit ══════════ */\nlet musicOn = true,",
    "const PHRASE = [0,2,3,4,3,2,0,-1, 4,5,4,3,2,0,-1,-1, 0,3,4,6,7,6,4,3, 2,0,2,0,-1,-1,-1,-1];\n",
    "/* ══════════ Musik ══════════ (siehe MUSIC: gerenderte Stücke) */\nlet musicOn = true;\n")
cut("/* ══════════ Instrumente ══════════\n   Nicht jede Gegend spielt dieselbe Saite.",
    "  src.start(when);\n}\n\n/* ══════════ Der Klang des Absturzes ══════════",
    "/* ══════════ Der Klang des Absturzes ══════════")
rep("  playSfx('sfx_game_over',{gain:.9});\n  if(ac&&musicNode){\n    const now=ac.currentTime;\n"
    "    musicNode.g.gain.cancelScheduledValues(now);\n    musicNode.g.gain.setValueAtTime(musicNode.g.gain.value,now);\n"
    "    musicNode.g.gain.linearRampToValueAtTime(0,now+.7);\n  }\n",
    "  playSfx('sfx_game_over',{gain:.9});\n"
    "  MUSIC.stop(.7);                                   // die Musik tritt ab ...\n"
    "  setTimeout(()=>{ if(state==='dead') MUSIC.play('mus_end_screen', 2.0); }, 2600);   // ... und kommt leise zurück\n")
cut("/* Bass der Harmonika: kurzer, tiefer Stoß auf der Eins */\nfunction bas(freq, when, vol){",
    "/* Die Stimmen kommen und gehen mit der Serie, ohne Anzeige */\n",
    "/* Die Intensitätsspur kommt und geht mit der Serie, ohne Anzeige */\n")
rep("function layerChange(up){\n  if(!ac || !musicNode) return;\n  const now = ac.currentTime;\n"
    "  if(musicNode.extra) musicNode.extra.gain.setTargetAtTime(nizLayer() > 0 ? 1 : 0, now, up ? 0.25 : 0.6);\n",
    "function layerChange(up){\n  if(!ac) return;\n  MUSIC.setLayer(nizLayer(), up ? 0.25 : 0.6);\n")
rep("  if(musicNode) musicNode.g.gain.linearRampToValueAtTime(on?1:0, ac.currentTime + 0.6);\n",
    "  MUSIC.setOn(on);\n")
rep("  if(uvod){ zavrsiUvod(); audioInit(); musicStart(); return; }", "  if(uvod){ zavrsiUvod(); audioInit(); musicKick(); return; }")
rep("  audioInit(); musicStart();\n", "  audioInit(); musicKick();\n")
rep("  if(ac && musicNode) musicNode.g.gain.linearRampToValueAtTime(musicOn?1:0, ac.currentTime + 1.2);\n", "")
rep("  if(musicNode && musicNode.extra) musicNode.extra.gain.value = 0;\n", "  MUSIC.setLayer(0, .1);\n")
rep("  setTimeout(()=>radioSay(L('Galeb je u zraku. Sretan let!',",
    "  MUSIC.play(cityTrack(), 1.5);                      // der Flug beginnt mit dem Stück des Ortes\n"
    "  setTimeout(()=>radioSay(L('Galeb je u zraku. Sretan let!',")
rep("      setRoom(); gradSignal();\n", "      setRoom(); gradSignal();\n      MUSIC.play(cityTrack(), 2.5);                    // neuer Ort, neues Stück\n")
rep("  layerChange(true);\n  if(ac && soundOn){\n    playSfx('sfx_fever_start');\n  }\n",
    "  layerChange(true);\n  if(ac && soundOn){\n    playSfx('sfx_fever_start');\n  }\n  MUSIC.play('mus_fever', .4);\n")
rep("function feverKraj(){\n  layerChange(false);\n  playSfx('sfx_fever_end');\n",
    "function feverKraj(){\n  layerChange(false);\n  playSfx('sfx_fever_end');\n  if(state==='playing') MUSIC.play(cityTrack(), 1.2);\n")
m2 = re.search(r"  if\(musicNode&&musicOn&&ac\)\{const now=ac\.currentTime;musicNode\.g\.gain[^\n]*\n", s)
assert m2 and s.count('if(musicNode&&musicOn&&ac)') == 1
s = s[:m2.start()] + "  MUSIC.duck(-9, 4.4);                                // das Radio spricht: Musik zurücknehmen\n" + s[m2.end():]
rep("  update(dt); render(); musicTick();\n", "  update(dt); render();\n")

# preload the next city's piece during the arrival glide is implicit (decode on arrival); preload menu early
rep("  primeSfx();refreshAmbient();\n", "  primeSfx();refreshAmbient();\n  MUSIC.preload('mus_menu');\n")

# ------------------------------------------------------------------ 5. leftovers
for name in ['musicNode', 'musicStart', 'musicTick', 'musicDrone', 'createOscillator', 'makeIR', 'pluck(',
             'scaleOf', 'beep(', 'noiseBurst(', 'tone(', 'createConvolver', 'createBiquadFilter']:
    hits = [mm.start() for mm in re.finditer(re.escape(name), s)]
    if hits:
        print('LEFTOVER', name, len(hits), [s[h - 60:h + 40].replace('\n', ' ') for h in hits[:3]])
open(out, 'w', encoding='utf-8').write(s)
print('written', out, round(len(s) / 1e6, 2), 'MB')
