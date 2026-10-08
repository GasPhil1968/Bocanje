import sys, numpy as np, songs
from compose import Song
def stems(name):
    s = songs.SONGS[name]()
    insts = sorted(set((e['inst'], e['part']) for e in s.events))
    res = {}
    allev = s.events
    for inst, part in insts:
        s.events = [e for e in allev if e['inst'] == inst and e['part'] == part]
        y = s.render(part)
        res[f'{part}:{inst}'] = 20*np.log10(np.sqrt(np.mean(y**2))+1e-12)
    return res
for n in sys.argv[1:]:
    print(n, {k: round(v,1) for k,v in stems(n).items()})
