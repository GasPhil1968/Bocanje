import sys
s = open(sys.argv[1], encoding='utf-8').read()
anchor = "  pokreniUvod();\n  requestAnimationFrame(loop);\n"
assert s.count(anchor) == 1
hook = ("window.__G={get state(){return state},get bird(){return bird},get H(){return H},get score(){return score},"
        "get ac(){return ac},MUSIC,get pipes(){return pipes},gap:(p)=>otvori(p),get scene(){return SCENE().name},"
        "goto:(i)=>{sceneIdx=sceneShown=i;MUSIC.play(cityTrack(),.3);},cityTrack:()=>cityTrack(),"
        "feverStart:()=>feverStart(),feverKraj:()=>{fever=0;feverKraj();},setNiz:(n)=>{niz=n;layerChange(true);}};\n")
s = s.replace(anchor, anchor + "  " + hook)
open(sys.argv[2], 'w', encoding='utf-8').write(s)
