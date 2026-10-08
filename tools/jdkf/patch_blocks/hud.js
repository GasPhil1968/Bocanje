function lifeBar(x,v,max,foeSide){
 img(foeSide?'hud/hud_bar_foe':'hud/hud_bar_player',x,52,410,26);
 var im=I(foeSide?'hud/hud_fill_foe':'hud/hud_fill_player'),k=clamp(v/max,0,1);
 if(!im||k<=0)return;
 var fw=404*k,sw=im.naturalWidth*k;
 if(foeSide)ctx.drawImage(im,im.naturalWidth-sw,0,sw,im.naturalHeight,x+3+404-fw,55,fw,20);
 else ctx.drawImage(im,0,0,sw,im.naturalHeight,x+3,55,fw,20);
}
function portrait(x,y,id,boss,flip){
 img(boss?'hud/portrait_frame_boss':'hud/portrait_frame',x-27,y-27,54,54);
 ctx.save();ctx.translate(x,y);if(flip)ctx.scale(-1,1);img('hud/portrait_'+id,-22,-22,44,44);ctx.restore();
}
function drawHUD(){
 ctx.save();
 img('hud/hud_panel',0,0,W,108);
 var boss=foe.cfg&&foe.cfg.id==='mrkonja';
 portrait(34,54,'saner',false,false);portrait(W-34,54,fid(foe),boss,true);
 lifeBar(70,player.hp,player.hpMax,false);
 lifeBar(W-480,foe.hp,foe.hpMax,true);
 if(boss)img(foe.phase2?'hud/boss_phase_marker_bright':'hud/boss_phase_marker_dim',W-480+204,48,3,34);
 txt('ŠANER',70,40,22,'#f5e7c8','left');
 txt(foe.name.toUpperCase(),W-40,40,22,'#ffd9a8','right');
 var sec=Math.ceil(S.timer/1000);
 imgC('hud/timer_plate',W/2,55,0.78);
 txt(String(sec<0?0:sec),W/2,70,40,sec<=10?'#ff6a4a':'#ffe9b8','center',900);
 txt(t('score')+' '+S.score,40,102,18,'#e8d6ae','left',700);
 txt(t('hi')+' '+S.hi,W/2,102,18,'#e8d6ae','center',700);
 txt(t('stage')+' '+(S.stage+1)+'-'+(S.loop+1),W-40,102,18,'#e8d6ae','right',700);
 if(S.combo>1&&S.comboT>0)txt(S.combo+' '+t('combo'),W/2,148,26,'#ffe08a','center',900);
 if(S.counterT>0)txt(t('counter'),W/2,182,24,'#ffb064','center',900);
 if(S.parryT>0)txt(t('parry'),W/2,214,27,'#d9f4ff','center',900);
 if(S.bossRageT>0)txt(t('rage'),W/2,246,25,'#ffb15c','center',900);
 /* zivoti */
 for(var i=0;i<S.lives;i++)imgC('props/life_icon',W/2-40+i*30,16,0.82);
 ctx.restore();
}
function drawTouch(){
 if(!TOUCH)return;ctx.save();
 var act=JOY.id!==null;
 ctx.globalAlpha=act?.66:.46;
 img(act?'buttons/joy_base_highlighted':'buttons/joy_base_normal',JOY.cx-JOY.r,JOY.cy-JOY.r,JOY.r*2,JOY.r*2);
 var dx=JOY.x-JOY.cx,dy=JOY.y-JOY.cy,d=Math.hypot(dx,dy)||1,lim=Math.min(JOY.r*.58,d),kx=JOY.cx+dx/d*lim,ky=JOY.cy+dy/d*lim;
 ctx.globalAlpha=act?.9:.62;
 imgC(act?'buttons/joy_knob_pressed':'buttons/joy_knob_normal',act?kx:JOY.cx,act?ky:JOY.cy,1);
 for(var id in BTN){
  var b=BTN[id],on=K[id];
  ctx.globalAlpha=on?.92:.64;
  img('buttons/'+(id==='kick'?'btn_kick_':'btn_punch_')+(on?'pressed':'normal'),b.x-b.r,b.y-b.r,b.r*2,b.r*2);
  ctx.globalAlpha=on?1:.82;
  imgC(id==='kick'?'icons/icon_foot':'icons/icon_fist',b.x,b.y+(on?2:0),b.r/55);
 }
 ctx.restore();
}
/* title-screen chips (language / sound) are tappable */
var CHIP_LANG={x:28,y:H-48,w:64,h:26},CHIP_SND={x:W-70,y:H-54,w:40,h:40};
function inRect(g,r,pad){pad=pad||12;return g.x>=r.x-pad&&g.x<=r.x+r.w+pad&&g.y>=r.y-pad&&g.y<=r.y+r.h+pad;}
function titleChipAt(g){
 if(S.scene!=='title')return false;
 if(inRect(g,CHIP_LANG)){cycleLang();return true;}
 if(inRect(g,CHIP_SND)){A.toggle();return true;}
 return false;
}
