import sys
s = open(sys.argv[1], encoding='utf-8').read()
end = '})();\n})();\n</script>'
i = s.rindex(end)
hook = ("window.__G={get state(){return state},get bird(){return bird},get H(){return H},get score(){return score},"
        "get ac(){return ac},get soundOn(){return soundOn},get musicOn(){return musicOn},"
        "MUSIC:(typeof MUSIC!=='undefined'?MUSIC:null),decodeSfx:(typeof decodeSfx!=='undefined'?decodeSfx:null),"
        "SFXIDS:(typeof GALEB_SFX_DATA!=='undefined'?Object.keys(GALEB_SFX_DATA):[]),"
        "get pipes(){return pipes},gap:(p)=>otvori(p),get niz(){return niz},"
        "get fever(){return fever},feverStart:()=>feverStart(),feverKraj:()=>{fever=0;feverKraj();},"
        "setNiz:(n)=>{niz=n;layerChange(true);},nizLayer:()=>nizLayer()};\n")
s = s[:i] + hook + s[i:]
s = s.replace("function playSfx(id,options={}){", "function playSfx(id,options={}){(window.__played||(window.__played=[])).push(id);", 1)
open(sys.argv[2], 'w', encoding='utf-8').write(s)
