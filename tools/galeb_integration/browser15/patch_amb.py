"""Register the 10 ambience loops and make them loop gaplessly. usage: patch_amb.py <index.html> <amb_loops.json>"""
import sys, json
p, lp = sys.argv[1], sys.argv[2]
s = open(p, encoding='utf-8').read(); loops = json.load(open(lp))
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80]); s = s.replace(old, new)
paths = ''.join(f'"{k}":"assets/audio/ambience/{k}.m4a",' for k in sorted(loops))
rep('const GALEB_SFX_DATA = {', 'const GALEB_SFX_DATA = {' + paths)
rep('const GALEB_SFX_META = {',
    '/* Ambience loop region [loopStart, length] in seconds; files carry 0.5 s wrap-around padding */\n'
    'const GALEB_AMB_LOOPS = ' + json.dumps(loops, separators=(',', ':')) + ';\n'
    'const GALEB_SFX_META = {')
rep("        const src=ac.createBufferSource();src.buffer=buf;src.loop=true;",
    "        const src=ac.createBufferSource();src.buffer=buf;src.loop=true;\n"
    "        const lp=GALEB_AMB_LOOPS[id];if(lp&&buf.duration>=lp[0]+lp[1]){src.loopStart=lp[0];src.loopEnd=lp[0]+lp[1];}")
rep("        g.gain.setTargetAtTime(vol,t0,.65);src.start(t0);",
    "        g.gain.setTargetAtTime(vol,t0,.65);src.start(t0,src.loopEnd>0?lp[0]+Math.random()*lp[1]*.9:0);")
open(p, 'w', encoding='utf-8').write(s); print('ambience patched')
