#!/usr/bin/env python3
"""One-off migration: turns jedan-dva-kung-fu-v10.html (procedural Canvas art)
into the sprite-based source jedan-dva-kung-fu/src/jedan-dva-kung-fu.html.

Usage: python3 apply_patch.py <v10.html> <out.html>
Line ranges refer to the unmodified v10 file.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def block(name):
    with open(os.path.join(HERE, 'patch_blocks', name)) as fh:
        return fh.read().rstrip('\n').split('\n')


def main(src, out):
    with open(src, encoding='utf-8') as fh:
        L = fh.read().split('\n')

    def rep(a, b, new, expect):
        """replace 1-based inclusive lines a..b; sanity-check the first line"""
        assert L[a - 1].startswith(expect), (a, L[a - 1][:60])
        L[a - 1:b] = new

    # bottom-up so earlier line numbers stay valid
    rep(1765, 1801, [], 'function drawTitle(')
    rep(1724, 1764, block('boot_title.js'), 'function drawBoot(')
    rep(1721, 1721, block('bubble.js'), 'function speechBubble(')
    rep(1672, 1711, block('hud.js'), 'function miniPortrait(')
    rep(1651, 1663, [], 'function bar(')
    rep(1370, 1388, block('projs.js'), 'function drawProjs(')
    rep(985, 1215, block('bg.js'), 'function sky(')
    rep(960, 980, block('parts.js'), 'function drawParts(')
    rep(692, 760, block('fighter.js'), 'function drawDroppedWeapon(')
    rep(557, 691, [], 'function torsoShape(')
    rep(517, 526, [], 'function faceMood(')   # expressions are baked into the frames
    rep(464, 474, [], 'function limb(')
    rep(128, 128, block('loader.js') + [''], '')
    assert L[126].startswith('resize();')

    s = '\n'.join(L)

    def sub(old, new, count=1):
        nonlocal s
        assert s.count(old) == count, (old[:70], s.count(old))
        s = s.replace(old, new)

    # rotate overlay icon is an image now
    sub('<div class="ico">↻</div>', '<img id="rotimg" class="ico" alt="" width="128" height="128">')
    sub('#rotate .ico{font-size:64px;', '#rotate .ico{width:128px;height:128px;')
    # boot waits for the asset pack
    sub("if(S.sceneT>3200||KP.start){S.scene='title'", "if(ASSETS.ready&&(S.sceneT>3200||KP.start)){S.scene='title'")
    # tappable title chips (touch + mouse)
    sub("  if(b){activeTouch[tp.identifier]=b;pressButton(b);continue;}",
        "  if(titleChipAt(g)){chip=true;continue;}\n  if(b){activeTouch[tp.identifier]=b;pressButton(b);continue;}")
    sub(" TOUCH=true;A.init();K.any=true;\n", " TOUCH=true;A.init();K.any=true;var chip=false;\n")
    sub(" if(S.scene!=='fight')KP.start=true;e.preventDefault();",
        " if(S.scene!=='fight'&&!chip)KP.start=true;e.preventDefault();")
    sub("cv.addEventListener('mousedown',function(){A.init();KP.start=true;});",
        "cv.addEventListener('mousedown',function(e){A.init();if(titleChipAt(toGame(e.clientX,e.clientY)))return;KP.start=true;});")
    # travel map: road strip + node sprites
    sub("ctx.save();ctx.globalAlpha=.95;ctx.strokeStyle='#e5cc96';ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(140,360);ctx.lineTo(1140,360);ctx.stroke();"
        "for(var i=0;i<FOES.length;i++){var px=140+i*(1000/(FOES.length-1));ctx.fillStyle=i<S.stage?'#b0671b':(i===S.stage?'#ffd76a':'#705841');"
        "ctx.beginPath();ctx.arc(px,360,i===S.stage?18:13,0,6.284);ctx.fill();ctx.lineWidth=3;ctx.strokeStyle=INK;ctx.stroke();}ctx.restore();",
        "ctx.save();ctx.globalAlpha=.95;img('screens/travel_road',140,356,1000,8);"
        "for(var i=0;i<FOES.length;i++){var px=140+i*(1000/(FOES.length-1));"
        "imgC(i<S.stage?'screens/node_travel_cleared':(i===S.stage?'screens/node_travel_current':'screens/node_travel_upcoming'),px,360,1);}ctx.restore();")
    # versus: walking Šaner + signature intro frames
    sub("var ps={x:player.x,y:player.y,dir:player.dir,pose:player.pose,pts:player.pts,state:player.state,onGround:player.onGround};",
        "var ps={x:player.x,y:player.y,dir:player.dir,pose:player.pose,pts:player.pts,state:player.state,onGround:player.onGround,vx:player.vx,walkPh:player.walkPh};")
    sub("var pBase=(tm>2350&&tm<4200)?walkPose(tm*.0105,false,2.1):P.idle;",
        "var pWalk=(tm>2350&&tm<4200),pBase=pWalk?walkPose(tm*.0105,false,2.1):P.idle;if(pWalk){player.state='walk';player.vx=2;player.walkPh=tm*.0105;}else player.vx=0;")
    sub("  foe.pose=cutscenePose(foe,'intro',tm,fBase);",
        "  foe.sprOverride=(cfg.id==='ciro'&&fBase===P.punchHigh)?'nun_high_strike':(cfg.id==='mrkonja'&&fBase===P.punchHigh)?'slash_high_strike':(cfg.id==='mujo'&&fBase===P.block)?'block':null;foe.vy=0;\n"
        "  foe.pose=cutscenePose(foe,'intro',tm,fBase);")
    sub("player.state=ps.state;player.onGround=ps.onGround;\n",
        "player.state=ps.state;player.onGround=ps.onGround;player.vx=ps.vx;player.walkPh=ps.walkPh;foe.sprOverride=null;\n")
    # stage-clear sparkle row
    sub("ctx.save();ctx.globalAlpha=.22;ctx.fillStyle='#ffd76a';ctx.beginPath();for(var i=0;i<8;i++){var ax=260+i*38,ay=124+Math.sin(tm*.01+i)*12;ctx.arc(ax,ay,3+(i%2),0,6.284);}ctx.fill();ctx.restore();",
        "ctx.save();ctx.globalAlpha=.5;for(var i=0;i<8;i++){var ax=260+i*38,ay=124+Math.sin(tm*.01+i)*12;imgC('fx/hit_spark_gold_'+(1+Math.floor(tm/120+i)%4),ax,ay,.35+(i%2)*.1);}ctx.restore();")
    # ending: win frame
    sub("var f=endingFighter;f.t=tm;", "var f=endingFighter;f.t=tm;f.state='win';")

    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(s)
    print('written', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
