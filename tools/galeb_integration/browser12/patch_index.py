"""Podaca music + gapless music loops for the BROWSER build. usage: patch_index.py <index.html> <loops.json>"""
import sys, json
p, loops_path = sys.argv[1], sys.argv[2]
s = open(p, encoding='utf-8').read()
loops = json.load(open(loops_path))


def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, f'{n} x {old[:90]!r}'
    s = s.replace(old, new)


# 1. file list + metadata
rep('"mus_city_sibenik_layer":"assets/audio/music/mus_city_sibenik_layer.m4a"};',
    '"mus_city_sibenik_layer":"assets/audio/music/mus_city_sibenik_layer.m4a",'
    '"mus_city_podaca":"assets/audio/music/mus_city_podaca.m4a",'
    '"mus_city_podaca_layer":"assets/audio/music/mus_city_podaca_layer.m4a"};\n'
    '/* Loop region of every music file: [loopStart, length] in seconds. The files carry 0.5 s of\n'
    '   wrap-around padding on both ends, so AAC encoder delay/padding can never cause a gap. */\n'
    'window.GALEB_MUSIC_LOOPS = ' + json.dumps(loops, separators=(',', ':')) + ';')
rep('{"id":"mus_fever","layer_id":null,"volume_recommendation":0.75}',
    '{"id":"mus_city_podaca","layer_id":"mus_city_podaca_layer","volume_recommendation":0.75},'
    '{"id":"mus_city_podaca_layer","layer_id":null,"volume_recommendation":0.75},'
    '{"id":"mus_fever","layer_id":null,"volume_recommendation":0.75}')
# 2. Podaca gets its own piece
rep("Makarska:'mus_city_makarska',Podaca:'mus_city_makarska',", "Makarska:'mus_city_makarska',Podaca:'mus_city_podaca',")
# 3. gapless looping in the player
rep("""  function voice(buffer,startAt){
    const src=ac.createBufferSource();src.buffer=buffer;src.loop=true;
    const g=ac.createGain();g.gain.value=0;
    src.connect(g);g.connect(ensure());src.start(startAt);""",
    """  function voice(buffer,startAt,id){
    const src=ac.createBufferSource();src.buffer=buffer;src.loop=true;
    const lp=window.GALEB_MUSIC_LOOPS&&window.GALEB_MUSIC_LOOPS[id];
    if(lp&&buffer.duration>=lp[0]+lp[1]){src.loopStart=lp[0];src.loopEnd=lp[0]+lp[1];}   // sample-exact loop region
    const g=ac.createGain();g.gain.value=0;
    src.connect(g);g.connect(ensure());src.start(startAt,lp&&buffer.duration>=lp[0]+lp[1]?lp[0]:0);""")
rep("const base=voice(b,at),layer=l?voice(l,at):null;", "const base=voice(b,at,id),layer=l?voice(l,at,row.layer_id):null;")
open(p, 'w', encoding='utf-8').write(s)
print('patched', p)
