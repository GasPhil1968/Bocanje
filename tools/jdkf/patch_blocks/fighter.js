/* ---------- fighter sprites ----------
   The pose skeleton (buildPts) still drives hitboxes; what is drawn is a
   sprite frame chosen from state, move phase and velocity. */
function fid(f){return f&&f.cfg?f.cfg.id:'saner';}
function frameReady(fr){return fr&&fr.im.complete&&fr.im.naturalWidth;}
function hasFrame(id,n){return !!(FR[id]&&FR[id][n]);}
function firstHave(id,list){for(var i=0;i<list.length;i++)if(hasFrame(id,list[i]))return list[i];return null;}
function pickFrame(id,names){var set=FR[id]||{};for(var i=0;i<names.length;i++){if(frameReady(set[names[i]]))return set[names[i]];}return frameReady(set.idle)?set.idle:null;}
var ATK={
 punchHigh:{w:['punch_high_windup','punch_mid_windup'],s:['punch_high_strike','punch_mid_strike'],r:['punch_high_recover','punch_mid_recover']},
 punchMid :{w:['punch_mid_windup'],s:['punch_mid_strike'],r:['punch_mid_recover']},
 punchLow :{w:['punch_low_windup'],s:['punch_low_strike','punch_mid_strike'],r:['punch_low_recover','crouch']},
 kickHigh :{w:['kick_high_windup'],s:['kick_high_strike','kick_mid_strike'],r:['kick_high_recover']},
 kickMid  :{w:['kick_mid_windup'],s:['kick_mid_strike','kick_high_strike'],r:['kick_mid_recover']},
 sweep    :{w:['sweep_windup'],s:['sweep_strike','crouch'],r:['sweep_recover','crouch']},
 jumpKick :{w:['jump_kick'],s:['jump_kick'],r:['jump_kick']},
 slowPunch:{w:['slow_punch_windup','punch_mid_windup'],s:['slow_punch_strike','punch_mid_strike'],r:[]},
 slowKick :{w:['slow_kick_windup','wind','kick_mid_windup'],s:['slow_kick_strike','kick_mid_strike'],r:[]},
 poleHigh :{w:['pole_windup'],s:['pole_high_strike'],r:[]},
 poleMid  :{w:['pole_windup'],s:['pole_mid_strike'],r:[]},
 poleLow  :{w:['crouch'],s:['pole_low_strike'],r:[]},
 nunHigh  :{w:['nun_spin'],s:['nun_high_strike'],r:[]},
 nunMid   :{w:['nun_spin'],s:['nun_mid_strike'],r:[]},
 nunLow   :{w:['crouch'],s:['nun_low_strike'],r:[]},
 diveKick :{w:['dive_kick'],s:['dive_kick'],r:['dive_kick']},
 slash    :{w:['slash_high_windup'],s:['slash_high_strike'],r:[]},
 slashLow :{w:['crouch'],s:['slash_low_strike'],r:[]},
 toss     :{w:['toss_windup'],s:['toss_release'],r:['toss_release']}
};
function attackFrameNames(f){
 var id=fid(f),a=ATK[f.moveKey]||ATK.punchMid,m=f.move,t=f.t,n;
 if(t<m.st){n=firstHave(id,a.w);if(n)return [n];return t<m.st*.6?['idle']:a.s;}
 if(t<m.st+m.ac)return a.s;
 n=firstHave(id,a.r);if(n)return [n];
 return t<m.st+m.ac+m.rc*.5?a.s:['idle'];
}
function walkIndex(f){var c=Math.PI*2,ph=(((f.walkPh||0)%c)+c)%c,i=Math.floor(ph/(c/4))%4;return ((f.vx||0)*(f.dir||1)<0)?3-i:i;}
function frameNames(f){
 var id=fid(f);
 if(f.sprOverride)return [f.sprOverride];
 if(f.state==='ko')return f.deadT<260?['down','hurt']:['ko'];
 if(f.state==='down')return f.t<120?['hurt']:(f.t<880?['down']:['crouch']);
 if(f.state==='hurt')return ['hurt'];
 if(f.state==='win')return ['win'];
 if(f.state==='sit')return ['sit','crouch'];
 if(f.state==='attack'&&f.move)return attackFrameNames(f);
 if(!f.onGround){var vy=f.vy||0;return vy<-4?['jump_rise','jump']:(vy<3?['jump_apex','jump']:['jump_fall','jump']);}
 if(f.blocking)return ['block'];
 if(f.crouching)return ['crouch'];
 if(f.state==='swing'){var c=Math.PI*2,sp=(((f.spin||0)%c)+c)%c;return ['swing_'+(1+Math.floor(sp/(c/3))%3),'idle'];}
 if(f.landT>70)return ['land','crouch'];
 if(f.state==='walk'){var w=walkIndex(f)+1;return (Math.abs(f.vx)>2.8&&hasFrame(id,'run_1'))?['run_'+w]:['walk_'+w];}
 if(id==='zumbul'&&f.mode==='rest')return ['chain_rest','idle'];
 if(id==='mrkonja'&&f.phase2)return ['rage','idle'];
 return Math.floor((f.t||0)/520)%2?['idle_2','idle']:['idle'];
}
function drawSprite(f,fr,alpha,comp,dx){
 var s=f.scale,d=f.dir||1;
 ctx.save();
 if(alpha!==undefined)ctx.globalAlpha=alpha;
 if(comp)ctx.globalCompositeOperation=comp;
 ctx.translate(f.x+(dx||0),f.y);ctx.scale(d*s,s);
 ctx.drawImage(fr.im,fr.ox,fr.oy,fr.w,fr.h);
 ctx.restore();
}
function drawChainBall(f){
 if(fid(f)!=='zumbul'||!f.ball||!f.pts)return;
 if(f.state==='ko'&&f.deadT>120)return;
 var p=f.pts,s=f.scale,ax=f.swinging?p.sh.x:p.handF.x,ay=f.swinging?p.sh.y-6*s:p.handF.y;
 var bx=f.ball.x,by=f.ball.y,L=Math.hypot(bx-ax,by-ay),n=Math.max(2,Math.floor(L/(9*s))),ang=Math.atan2(by-ay,bx-ax);
 var link=I('props/chain_link');
 if(link){for(var i=1;i<n;i++){var t=i/n;ctx.save();ctx.translate(lerp(ax,bx,t),lerp(ay,by,t));ctx.rotate(ang);ctx.drawImage(link,-6*s,-4*s,12*s,8*s);ctx.restore();}}
 imgC('props/chain_ball',bx,by,s*0.9);
}
var DROP={handzar:'props/drop_handzar',motka:'props/drop_motka',nuncake:'props/drop_nunchaku',lanac:'props/drop_chainball'};
function drawDroppedWeapon(f){
 if(!f||f.state!=='ko'||!f.weapon||f.deadT<120)return;
 var im=I(DROP[f.weapon]);if(!im)return;
 var w=im.naturalWidth/2*f.scale,h=im.naturalHeight/2*f.scale;
 ctx.save();ctx.translate(f.x+f.dir*34,GROUND-h/2+2);ctx.rotate(-.06*f.dir);ctx.scale(f.dir,1);ctx.drawImage(im,-w/2,-h/2,w,h);ctx.restore();
}
function shouldAfterimage(f){var id=f&&f.cfg?f.cfg.id:'saner';return (id==='ero'&&!f.onGround)||(id==='ciro'&&f.state==='attack')||(id==='mrkonja'&&f.phase2&&f.state==='attack')||(f.isPlayer&&f.state==='attack'&&f.moveKey==='jumpKick');}
function drawAfterimage(f,fr){if(!shouldAfterimage(f)||!fr)return;for(var n=2;n>=1;n--)drawSprite(f,fr,CONFIG.AFTERIMAGE_ALPHA*(3-n)/2,null,-f.dir*n*14);}
function drawFighter(f){
 var fr=pickFrame(fid(f),frameNames(f)),s=f.scale;
 /* ground shadow + walk dust */
 var shy=f.shadowY||GROUND,air=clamp((GROUND-f.y)/220,0,1),sh=I('fx/shadow');
 if(sh){var sw=96*s*(1-air*.35),shh=22*s*(1-air*.35);ctx.save();ctx.globalAlpha=.75*(1-air*.5);ctx.drawImage(sh,f.x-sw/2,shy+4-shh/2,sw,shh);ctx.restore();}
 if(f.state==='walk'&&f.onGround&&Math.abs(f.vx)>1.4){var vv=Math.abs(f.vx),dk=Math.floor((f.walkPh||0)*1.3)%3+1;ctx.save();ctx.globalAlpha=vv>2.8?.38:.24;imgC('fx/dust_puff_'+dk,f.x-f.dir*(vv>2.8?26:20)*s,shy-6,s*(vv>2.8?1:.8));ctx.restore();}
 if(!fr)return;
 drawAfterimage(f,fr);
 ctx.save();
 var squash=(f.landT>0?clamp(f.landT/180,0,1):0),stretch=(f.flash>0?clamp(f.flash/170,0,1):0);
 if(squash||stretch){var sx=1+squash*.055-stretch*.018,sy=1-squash*.075+stretch*.025;ctx.translate(f.x,GROUND);ctx.scale(sx,sy);ctx.translate(-f.x,-GROUND);}
 drawSprite(f,fr);
 if(f.flash>0)drawSprite(f,fr,clamp(f.flash/120,0,1)*0.45,'lighter');
 ctx.restore();
 drawChainBall(f);
}
