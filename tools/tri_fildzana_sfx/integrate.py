"""Patch TRI FILDŽANA index.html: file-based SFX instead of synthesized AU, background music per
scene, random level order.
usage: python3 integrate.py <index.html in> <sfx_manifest.json> <music.json> <index.html out>"""
import sys, json, re

src = open(sys.argv[1], encoding='utf-8').read()
man = json.load(open(sys.argv[2], encoding='utf-8'))
mus = sorted(json.load(open(sys.argv[3], encoding='utf-8')), key=lambda m: m['scene'])
s = src


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:90])
    s = s.replace(old, new)


# ---------------------------------------------------------------- new audio manager
table = ','.join(f"{e['id']}:[{len(e['variants'])},{e['recommended_gain']},{e['min_retrigger_s']}]" for e in man['sounds'])
start = s.index('/* ---------- audio ---------- */')
end = s.index('function vib(p)')
AU = r"""/* ---------- audio ---------- */
/* Zvukovi su gotove WAV datoteke (audio/sfx/). Nema sintetiziranih zvukova i nema
   zamjenskog piska: ako datoteka nedostaje ili se još nije učitala, play() šuti. */
var SFX = {""" + table + r"""};
/* pozadinska muzika – jedna petlja po scenografiji (indeks = SCENE_OF / BG_NAMES); a..b je petlja u sekundama */
var MUSIKA = [""" + ','.join("{f:'%s',a:%s,b:%s}" % (m['file'], m['loop_start_s'], m['loop_end_s']) for m in mus) + r"""];
var MUSIC_GAIN = 0.28;
var SFX_VOICE = {saner_annoyed:1,saner_angry:1,saner_nervous:1,saner_gasp:1,saner_chuckle:1,saner_poke:1};
var SFX_RR = {run_step:1,police_step:1};
var AU = {
  on: true, ctx: null, buf: {}, last: {}, lastT: {}, voice: null,
  init: function(){
    if(this.ctx) return;
    try{
      var C = window.AudioContext || window.webkitAudioContext;
      if(!C) return;
      this.ctx = new C();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.9;
      this.master.connect(this.ctx.destination);
      this.prefetch();
      for(var k in this.raw) this.decode(k);
    }catch(e){ this.ctx = null; }
  },
  /* datoteke se skidaju odmah pri učitavanju stranice; dekodiraju se čim postoji AudioContext */
  raw: null,
  prefetch: function(){
    if(this.raw) return;
    var self = this; this.raw = {};
    Object.keys(SFX).forEach(function(id){
      var n = SFX[id][0];
      self.buf[id] = new Array(n);
      for(var i=0;i<n;i++) (function(i){
        var f = 'audio/sfx/' + id + (n > 1 ? '_' + (i < 9 ? '0' : '') + (i+1) : '') + '.wav';
        try{
          fetch(f).then(function(r){ return r.ok ? r.arrayBuffer() : null; }).then(function(ab){
            if(!ab) return;
            self.raw[id + '#' + i] = ab;
            self.decode(id + '#' + i);
          }).catch(function(){});
        }catch(e){}
      })(i);
    });
  },
  decode: function(k){
    var self = this, ab = this.raw[k];
    if(!this.ctx || !ab) return;
    delete this.raw[k];
    var p = k.split('#'), id = p[0], i = +p[1];
    try{
      /* callback oblik radi i na starijem Safariju */
      this.ctx.decodeAudioData(ab, function(b){ self.buf[id][i] = b; }, function(){});
    }catch(e){}
  },
  ok: function(){
    if(!this.on || !this.ctx) return false;
    if(this.ctx.state === 'suspended'){ try{ this.ctx.resume(); }catch(e){} }
    return true;
  },
  /* ---- pozadinska muzika: učitava se po potrebi, u memoriji najviše trenutna i sljedeća ---- */
  mus: null, musBuf: {}, musLoad: {}, musWant: -1, musNext: -1,
  musicLoad: function(k){
    var self = this, m = MUSIKA[k];
    if(!m || !this.ctx || this.musBuf[k] || this.musLoad[k]) return;
    this.musLoad[k] = true;   /* neuspjelo učitavanje se ne ponavlja – tada je jednostavno tiho */
    try{
      fetch(m.f).then(function(r){ return r.ok ? r.arrayBuffer() : null; }).then(function(ab){
        if(!ab) return;
        self.ctx.decodeAudioData(ab, function(b){ self.musBuf[k] = b; delete self.musLoad[k]; self.musicTrim(); }, function(){});
      }).catch(function(){});
    }catch(e){}
  },
  musicTrim: function(){
    for(var k in this.musBuf){
      k = +k;
      if(k !== this.musWant && k !== this.musNext && !(this.mus && this.mus.k === k)) delete this.musBuf[k];
    }
  },
  musicPre: function(k){ this.musNext = k; this.musicLoad(k); },
  /* k: indeks u MUSIKA ili -1 za tišinu; lvl: 0..1 (npr. tiše za vrijeme racije) */
  music: function(k, lvl){
    if(!this.ctx) return;
    if(!this.on || PAUSED) k = -1;
    this.musWant = k;
    var now = this.ctx.currentTime, m = this.mus;
    if(m && m.k !== k){
      try{ m.g.gain.cancelScheduledValues(now); m.g.gain.setValueAtTime(m.g.gain.value, now);
           m.g.gain.linearRampToValueAtTime(0, now + 1.2); m.s.stop(now + 1.3); }catch(e){}
      this.mus = m = null;
    }
    if(k < 0) return;
    var target = MUSIC_GAIN * lvl;
    if(!m){
      var b = this.musBuf[k];
      if(!b){ this.musicLoad(k); return; }
      try{
        var s = this.ctx.createBufferSource(), g = this.ctx.createGain();
        s.buffer = b; s.loop = true; s.loopStart = MUSIKA[k].a; s.loopEnd = MUSIKA[k].b;
        g.gain.setValueAtTime(0, now); g.gain.linearRampToValueAtTime(target, now + 1.5);
        s.connect(g); g.connect(this.master); s.start(now, MUSIKA[k].a);
        this.mus = {k:k, s:s, g:g, t:target};
      }catch(e){}
      return;
    }
    if(Math.abs(m.t - target) > 0.001){
      try{ m.g.gain.cancelScheduledValues(now); m.g.gain.setValueAtTime(m.g.gain.value, now);
           m.g.gain.linearRampToValueAtTime(target, now + 0.8); }catch(e){}
      m.t = target;
    }
  },
  /* o: {v: varijanta, delay: s, gain: x, pan: -1..1, dur: s (prekini s kratkim fade-om)} */
  play: function(id, o){
    o = o || {};
    if(!this.ok()) return null;
    var meta = SFX[id], list = this.buf[id];
    if(!meta || !list) return null;
    var now = this.ctx.currentTime, t0 = now + (o.delay || 0);
    if(meta[2] > 0 && this.lastT[id] !== undefined && t0 - this.lastT[id] < meta[2]) return null;
    var n = meta[0], v = o.v;
    if(v === undefined){
      if(n < 2) v = 0;
      else if(SFX_RR[id]) v = ((this.last[id] === undefined ? -1 : this.last[id]) + 1) % n;
      else { v = Math.floor(Math.random()*(n-1)); if(v >= (this.last[id] === undefined ? n : this.last[id])) v++; }
    }
    var b = list[v % n];
    if(!b) return null;
    this.last[id] = v % n; this.lastT[id] = t0;
    try{
      var s = this.ctx.createBufferSource(), g = this.ctx.createGain(), out = g;
      s.buffer = b;
      g.gain.value = meta[1] * (o.gain === undefined ? 1 : o.gain);
      s.connect(g);
      if(o.pan && b.numberOfChannels === 1 && this.ctx.createStereoPanner){
        var p = this.ctx.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, o.pan));
        g.connect(p); out = p;
      }
      out.connect(this.master);
      if(o.dur){
        g.gain.setValueAtTime(g.gain.value, t0 + o.dur);
        g.gain.linearRampToValueAtTime(0, t0 + o.dur + 0.03);
        s.stop(t0 + o.dur + 0.04);
      }
      /* Šaner ima jedan glas: nova reakcija prekida prethodnu */
      if(SFX_VOICE[id]){
        var pv = this.voice;
        if(pv){ try{ pv.g.gain.setValueAtTime(pv.g.gain.value, t0); pv.g.gain.linearRampToValueAtTime(0, t0 + 0.03); pv.s.stop(t0 + 0.04); }catch(e){} }
        this.voice = {s:s, g:g};
      }
      s.start(t0);
      return s;
    }catch(e){ return null; }
  }
};
"""
s = s[:start] + AU + s[end:]

# ---------------------------------------------------------------- call sites
P = lambda *a: '; '.join(a)
# state changes
rep("    AU.win(); vib([20,40,20,40]);", "    AU.play('title_sting'); AU.play('audience_murmur', {delay:0.35}); vib([20,40,20,40]);")
rep("    AU.tone(520, 0.08, 'square', 0.06, 380);\n    return;", "    AU.play('audience_murmur');\n    return;")
rep("save(); AU.gameover(); vib([40,60,40,60,120]);", "save(); AU.play('game_over'); vib([40,60,40,60,120]);")
rep("  AU.sirena(); vib([60,80,60,80,60]);",
    "  AU.play('police_siren'); AU.play('saner_gasp', {delay:0.15});\n"
    "  AU.play('police_step', {delay:0.10}); AU.play('police_step', {delay:0.38}); AU.play('police_step', {delay:0.66, gain:0.85});\n"
    "  vib([60,80,60,80,60]);")
rep("  AU.tone(200, 0.4, 'sawtooth', 0.10, 120); vib([40,60,40]);", "  AU.play('police_warning'); vib([40,60,40]);")
rep("  AU.gameover(); vib([60,80,60,80,160]);", "  G.escT = 0; AU.play('police_grab'); AU.play('game_over', {delay:0.2}); vib([60,80,60,80,160]);")
rep("  AU.sirena(); vib([30,60,30,60,120]);", "  G.escT = 0; AU.play('police_grab'); AU.play('police_siren', {delay:0.1}); vib([30,60,30,60,120]);")
rep("  AU.tone(180, 0.4, 'sine', 0.1, 90);\n  vib([20, 40, 20]);", "  AU.play('levat_reaction');\n  vib([20, 40, 20]);")
rep("  AU.tone(240,0.5,'sawtooth',0.10,130);\n  vib([30,60,30]);", "  AU.play('saner_annoyed', {v:0});\n  vib([30,60,30]);")
rep("  save(); AU.win(); vib([20,50,20,50,120]);", "  save(); AU.play('escape_victory'); vib([20,50,20,50,120]);")
rep("G.clothFly = 0; G.fleeStep = 0; G.clothSnd = false; G.stepT = 0;", "G.clothFly = 0; G.fleeStep = 0; G.clothSnd = false; G.stepT = 0; G.runSnd = false;")
# rounds
rep("  AU.chip(); vib(12);\n  if(G.minka === 1){\n    AU.ring(); vib([20,40,20]);",
    "  AU.play('bet_place'); vib(12);\n  if(G.minka === 1){\n    AU.play('telephone_ring', {delay:0.2}); vib([20,40,20]);")
rep("    AU.tone(340, 0.14, 'square', 0.07, 220);", "    AU.play('cup_rattle', {v:1, delay:0.25});")
rep("  G.st = S.SHOW; G.t = 0;", "  G.st = S.SHOW; G.t = 0;\n  AU.play('cup_lift', {v:0, delay:0.05});")
rep("  if(!longest)AU.whoosh();", "  if(!longest)AU.play('cup_slide');")
rep("  AU.tap(); vib(10);", "  G.revLift = 0; G.resSnd1 = false; G.resSnd2 = false;\n  AU.play('cup_select'); vib(10);")
rep("    AU.win(); vib([16,40,16]);", "    AU.play('round_win'); AU.play('coins_large', {delay:0.12}); vib([16,40,16]);")
rep("    AU.lose(); vib([30,50,30]);", "    AU.play('round_lose'); vib([30,50,30]);")
rep("G.poke = 0.6; AU.tone(200, 0.25, 'sawtooth', 0.10, 120);", "G.poke = 0.6; AU.play('saner_angry', {v:1});")
rep("      AU.tone(520, 0.28, 'triangle', 0.08, 300);", "      AU.play('audience_murmur');")
rep("AU.tone(330,0.08,'square',0.06,260);", "AU.play('saner_annoyed', {v:1});")
rep("    AU.tone(220,0.14,'sawtooth',0.09,150);", "    AU.play('saner_annoyed', {v:0});")
rep("    say(T('zaTebe'), 2.6);\n    AU.chip(); vib(20);", "    say(T('zaTebe'), 2.6);\n    vib(20);   /* bet_place svira startRound */")
# flee
rep("  if(ft <= G.fleeRunAt) return;", "  if(ft <= G.fleeRunAt) return;\n  if(!G.runSnd){ G.runSnd = true; AU.play('escape_swish'); }")
rep("    AU.tone(96, 0.07, 'sine', 0.09, 60);", "    AU.play('run_step');")
rep("        AU.tone(180, 0.2, 'sawtooth', 0.10, 60);", "        AU.play('table_overturn');   /* udarac stola pada na ~0.42 s = ft 1.32 */")
rep("        AU.thunk(); AU.noise(0.55, 260, 0.8, 0.20, 0.05, 90);", "        AU.play('cups_scatter'); AU.play('coins_large', {delay:0.1, gain:0.8});")
rep("          AU.tone(500+i*120, 0.10, 'triangle', 0.10, 260, i*0.06);\n", "")
rep("        AU.tone(700, 0.18, 'triangle', 0.10, 1500);", "        AU.play('saner_chuckle', {v:0});")
rep("        AU.noise(0.7, 500, 0.6, 0.22, 0, 120);\n        AU.tone(90, 0.3, 'sine', 0.25, 40);", "        AU.play('smoke_puff'); AU.play('escape_swish', {delay:0.05});")
rep("        AU.tone(2100, 0.09, 'square', 0.08, 2600);\n        AU.tone(2100, 0.12, 'square', 0.08, 1700, 0.12);", "        AU.play('distraction_whistle');")
rep("        G.flash = 0.8; AU.whoosh();", "        G.flash = 0.8; AU.play('escape_swish');")
rep("        say(T('zatvoreno'), 2.0);\n        AU.whoosh();", "        say(T('zatvoreno'), 2.0);\n        AU.play('bundle_pack');")
rep("if(!cf.grab){ cf.grab = true; AU.tone(560+i*110, 0.09, 'triangle', 0.11, 320); }", "if(!cf.grab){ cf.grab = true; }")
rep("          AU.noise(0.35, 520, 0.8, 0.15, 0, 1900);", "          AU.play('cloth_swish');")
# update()
rep("    G.nervRekao = G.nerv;\n", "    G.nervRekao = G.nerv;\n    AU.play('saner_nervous', {delay:0.4});\n")
rep("      AU.tone(180, 0.22, 'sawtooth', 0.10, 110);", "      AU.play('saner_annoyed');")
rep("        AU.thunk(); G.shake = 12; vib([30,50,30]);", "        AU.play('table_bump'); AU.play('cup_rattle', {v:0, delay:0.1}); G.shake = 12; vib([30,50,30]);")
old_med = s[s.index("      if(G.medjuCue < 1 && ml > 0.02){"):s.index("      if(ml > mi.dur){")]
new_med = """      if(G.medjuCue < 1 && ml > 0.02){
        G.medjuCue = 1;
        AU.play(['transition_swish','moving_rumble','advert_sting','news_sting','telephone_ring','paper_map',
                 'transition_swish','news_sting','transition_swish','transition_swish','transition_swish','advert_sting'][G.medju]);
      }
      /* svaka međuigra ima svoj udarac negdje na sredini */
      if(G.medjuCue < 2 && ml > mi.cut*0.5){
        G.medjuCue = 2;
        if(G.medju === 0){ AU.play('film_clapper'); G.shake = 20; vib(24); }
        else{
          var hit = [null,null,'coins_small','tv_static_cut','telephone_pickup','paper_map','audience_murmur',
                     'tv_static_cut','film_clapper',null,'levat_reaction','coins_small'][G.medju];
          if(hit) AU.play(hit);
        }
      }
      if(G.medjuCue < 3 && ml > mi.cut){
        G.medjuCue = 3;
        G.sceneLevel = G.level;              /* rez na novo mjesto */
        AU.play('scene_transition');
      }
      if(G.medjuCue < 4 && ml > mi.cut + 0.7){ G.medjuCue = 4; AU.play('ui_confirm'); }
"""
assert 'AU.pluck(f4[q4]' in old_med
s = s.replace(old_med, new_med)
rep("    AU.tone(1400,0.05,'square',0.06,900); AU.tone(1400,0.05,'square',0.05,900,0.14);", "    AU.play('minka_attention');")
# intro
rep("        AU.noise(0.10, 2400, 1.4, 0.13); AU.tone(70, 0.28, 'sine', 0.13, 44);", "        AU.play('tv_switch_on');")
rep("        if(iv === 1) AU.tone(440, 0.35, 'sine', 0.05, 440);\n        else AU.tone(1000, 1.45, 'sine', 0.045);",
    "        AU.play('tv_test_tone', iv === 1 ? {dur:0.35} : null);")
rep("          AU.thunk(); AU.tone(1600, 0.10, 'square', 0.12, 900);", "          AU.play('film_clapper');")
rep("          AU.noise(0.5, 1100, 0.5, 0.11, 0, 380);", "          AU.play('tv_static_cut');")
rep("          AU.tone(880, 0.07, 'square', 0.04, 700);", "          AU.play('telephone_pickup');")
rep("          say(T('intTel2'), 1.9);\n          AU.tone(180, 0.3, 'sawtooth', 0.12, 90);", "          say(T('intTel2'), 1.9);\n          AU.play('saner_gasp');")
rep("          AU.tone(520, 0.10, 'square', 0.06, 400);", "          AU.play('news_sting');")
rep("          say(T('brojiPare'), 1.60);", "          say(T('brojiPare'), 1.60);\n          AU.play('banknotes_count');")
rep("          AU.noise(0.22, 300, 0.7, 0.16, 0, 1500);\n          AU.tone(180, 0.3, 'sawtooth', 0.12, 90);", "          AU.play('saner_gasp');")
rep("            AU.thunk(); G.shake = 7;", "            AU.play('cup_set_down', {v:i % 3}); G.shake = 7;")
rep("        AU.tone(84, 0.55, 'sine', 0.17, 46);\n        AU.pluck(293.66, 0.7, 0.16);", "        AU.play('title_sting');")
# show / mix / pick / reveal / result
rep("          AU.thunk(); vib(18);", "          AU.play('cup_set_down'); vib(18);")
rep("            AU.thunk(); dust(SLOTX[hcc.slot], TABLEY, 5); vib(14);", "            AU.play('cup_set_down'); dust(SLOTX[hcc.slot], TABLEY, 5); vib(14);")
rep("          AU.tone(300, 0.2, 'sine', 0.08, 180);", "          AU.play('cup_lift', {v:1}); AU.play('audience_murmur', {delay:0.25});")
rep("{HAND_REACH=[null,null];AU.whoosh();}", "{HAND_REACH=[null,null];AU.play('cup_slide');}")
rep("          AU.glint();\n", "          AU.play('cheat_glint');\n")
rep("          AU.tone(110,0.07,'sine',0.10,70);", "          AU.play('cup_set_down');")
rep("            AU.tone(420, 0.12, 'triangle', 0.09, 300);", "            AU.play('saner_chuckle', {v:1});")
rep("              AU.tone(600, 0.10, 'square', 0.06, 480);", "              AU.play('audience_murmur');")
rep("        AU.noise(0.8, 320, 0.5, 0.16, 0, 1100);", "        AU.play('wind_gust');")
rep("          AU.thunk(); vib(14);\n          G.vjetar = null;", "          AU.play('cup_set_down'); vib(14);\n          G.vjetar = null;")
rep("nkc.lift = 0; nkc.tilt = 0; AU.thunk(); }", "nkc.lift = 0; nkc.tilt = 0; AU.play('cup_set_down'); }")
rep("        if(G.t<.38){G.cups.forEach(function(c){c.lift=0;});break;}",
    "        if(G.t<.38){G.cups.forEach(function(c){c.lift=0;});break;}\n        if(!G.revLift){ G.revLift = 1; AU.play('cup_lift'); }")
rep("        var cc2 = G.cups[G.cube];", "        var cc2 = G.cups[G.cube];\n        if(G.revLift < 2){ G.revLift = 2; AU.play('cup_lift'); }")
rep("          AU.tone(660,0.18,'triangle',0.12,880);", "          AU.play('ball_reveal');")
rep("    case S.RESULT:\n", """    case S.RESULT:
      /* Šanerova lica: ljut kad dobiješ, likuje kad izgubiš (svaki drugi put, da ne dosadi) */
      if(G.won && !G.resSnd1 && G.t >= 1.0){ G.resSnd1 = true; AU.play('saner_angry'); }
      if(!G.won && !G.resSnd1 && G.t >= 2.95){
        G.resSnd1 = true; G.chuckleN = (G.chuckleN || 0) + 1;
        if(G.chuckleN % 2) AU.play('saner_chuckle');
      }
      if(!G.resSnd2 && G.t >= 2.5){ G.resSnd2 = true; AU.play('cup_set_down'); }
""")
# police
rep("          AU.thunk(); G.shake = 14; vib(40);", "          AU.play('police_grab'); G.shake = 14; vib(40);")
rep("        AU.thunk(); G.shake = 12;\n", "        AU.play('cup_rattle', {v:0}); G.shake = 12;\n")
rep("          say(T('nemaOdgovora'), 3.0);\n          AU.thunk(); G.shake = 16; vib([60,80,60]);",
    "          say(T('nemaOdgovora'), 3.0);\n          AU.play('bribe_rejected'); AU.play('police_grab', {delay:0.2}); G.shake = 16; vib([60,80,60]);")
rep("    case S.UHAPSEN: break;\n    case S.ODVELI: break;", """    case S.UHAPSEN:
    case S.ODVELI:
      /* koraci dok ga vode (escort sličice od t=1.05 do 3.75 s) */
      if(G.t >= 1.05 && G.t < 3.75){
        G.escT -= dt;
        if(G.escT <= 0){ G.escT = 0.26; AU.play('police_step', {gain:lerp(0.9, 0.6, (G.t-1.05)/2.7)}); }
      }
      break;""")
# pigeon / poke
rep("  if(b.phase === 0){\n", "  if(b.phase === 0){\n    if(!b.inSnd){ b.inSnd = true; AU.play('pigeon_wings', {v:1}); }\n")
rep("b.perch = true; AU.coo(); vib(8); }", "b.perch = true; b.inSnd = false; AU.play('pigeon_coo'); vib(8); }")
rep("      AU.noise(0.28, 900, 0.9, 0.09, 0, 2600);", "      AU.play('pigeon_wings', {v:0});")
rep("  AU.poke(); vib(8);", "  AU.play('saner_poke'); vib(8);")
# bribes, power-ups
rep("      AU.tone(160, 0.3, 'sawtooth', 0.10, 90); vib(30);", "      AU.play('bribe_rejected'); vib(30);")
rep("        AU.coin(4); vib(20);", "        AU.play('money_handover'); AU.play('coins_large', {delay:0.2}); vib(20);")
rep("        say(pick(LB('MITO_MALO')), 3.2);\n        AU.thunk(); G.shake = 16; vib([60,80,60]);",
    "        say(pick(LB('MITO_MALO')), 3.2);\n        AU.play('money_handover'); AU.play('bribe_rejected', {delay:0.35}); G.shake = 16; vib([60,80,60]);")
rep("    AU.coin(2); vib(14);", "    AU.play('money_handover'); AU.play('coins_small', {delay:0.15}); vib(14);")
rep("    AU.pluck(392,0.5,0.16); vib(14);", "    AU.play('coffee_activate'); vib(14);")
rep("    AU.glint(); vib(10);", "    AU.play('eye_activate'); vib(10);")
rep("    AU.coo(); vib(12);", "    vib(12);   /* krila pa gugutanje svira updateBird */")
# interface
n = s.count('AU.chip()'); assert n == 15, n
s = s.replace('AU.chip()', "AU.play('ui_confirm')")
# wipe animation – edge detect, same condition as sanerPose()
rep("  switch(G.st){\n    case S.INTRO: {", """  var wipeNow = sanerEmotion()==='sweat' && [S.BET,S.PICK].includes(G.st) && (G.st!==S.PICK||G.t>.7) && G.gt%8>6.4;
  if(wipeNow && !G.wipeSnd) AU.play('saner_wipe_forehead');
  G.wipeSnd = wipeNow;
  /* pozadinska muzika: petlja scenografije dok traje runda; tiše za racije; tišina za uvod,
     bijeg, međuigre i završne ekrane (tamo sviraju vlastiti efekti) */
  var muzK = -1, muzL = 1;
  if(G.levatLeavePhase !== 4 && ![S.INTRO,S.BJEG,S.POBJEDA,S.OVER,S.UHAPSEN,S.ODVELI].includes(G.st)){
    muzK = scena();
    if(G.st === S.RACIJA || G.st === S.MITO) muzL = 0.3;
  }
  AU.music(muzK, muzL);
  AU.musicPre(SCENE_OF[G.level % SCENE_OF.length]);   /* sljedeće mjesto se učita unaprijed */

  switch(G.st){
    case S.INTRO: {""")
# random level order: persistent bag, never the same place or the same set twice in a row
start = s.index("function novoMjesto(){")
end = s.index("function odaberiMedjuigru(){")
s = s[:start] + """function novoMjesto(){
  G.mjestoUzeto = true;
  var cur = G.level, curSc = SCENE_OF[cur], i, j;
  if(!G.levelBag || !G.levelBag.length){
    var b = [];
    for(i=0;i<MJESTA.length;i++) if(i !== cur) b.push(i);
    for(i=b.length-1;i>0;i--){ j = ri(0,i); var tmp = b[i]; b[i] = b[j]; b[j] = tmp; }
    G.levelBag = b;
  }
  /* svako mjesto jednom prije ponavljanja; nikad isto mjesto ni ista scenografija dva puta zaredom */
  var k = -1;
  for(j=0;j<G.levelBag.length;j++){ if(G.levelBag[j] !== cur && SCENE_OF[G.levelBag[j]] !== curSc){ k = j; break; } }
  if(k < 0) for(j=0;j<G.levelBag.length;j++){ if(G.levelBag[j] !== cur){ k = j; break; } }
  if(k < 0) k = 0;
  G.level = G.levelBag.splice(k, 1)[0];
  save();
}

""" + s[end:]
rep("      lvl: clamp(o.lvl|0, 0, 16),", "      lvl: clamp(o.lvl|0, 0, 16),\n      bag: Array.isArray(o.bag) ? o.bag.filter(function(v){ return v === (v|0) && v >= 0 && v <= 16; }) : [],")
rep("      lvl: G.level|0, ml: G.medjuLast,", "      lvl: G.level|0, bag: G.levelBag || [], ml: G.medjuLast,")
rep("""  /* svako pokretanje igre počinje na drugom mjestu */
  G.level = ri(0, MJESTA.length-1);
  G.levelBag = [];
  G.sceneLevel = G.level;""", """  /* svako pokretanje: nasumično mjesto iz sačuvane vreće – nikad mjesto (ni scenografija) prošlog puta */
  G.level = st ? st.lvl : -1;
  G.levelBag = (st && st.bag) ? st.bag.filter(function(v){ return v !== G.level; }) : [];
  novoMjesto();
  G.mjestoUzeto = false;
  G.sceneLevel = G.level;""")

# test hook
rep("if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);", "AU.prefetch();\nif(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);")
rep("  epizoda:epizoda, scena:scena, toRacija:toRacija, setCups:setCups\n};", "  epizoda:epizoda, scena:scena, toRacija:toRacija, setCups:setCups, AU:AU, SFX:SFX, MUSIKA:MUSIKA, SCENE_OF:SCENE_OF\n};")

# ---------------------------------------------------------------- nothing synthetic may remain
for bad in ['AU.tone', 'AU.noise', 'AU.pluck', 'AU.thunk', 'AU.whoosh', 'AU.tap', 'AU.chip', 'AU.glint', 'AU.coin',
            'AU.win', 'AU.lose', 'AU.coo', 'AU.ring', 'AU.sirena', 'AU.poke', 'AU.gameover', 'createOscillator',
            'noiseBuf', 'createBiquadFilter', 'createBuffer(']:
    assert bad not in s, bad
ids = set(re.findall(r"AU\.play\('(\w+)'", s)) | set(re.findall(r"'(\w+)'", new_med))
missing = {i for i in ids if i in {e['id'] for e in man['sounds']}} ^ {e['id'] for e in man['sounds']}
print('unused ids:', missing)
open(sys.argv[4], 'w', encoding='utf-8').write(s)
print('ok', len(src), '->', len(s))
