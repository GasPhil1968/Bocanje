function drawBoot(tm){
 ctx.fillStyle='#0d0908';ctx.fillRect(0,0,W,H);
 var k=clamp(tm/700,0,1);
 if(I('screens/logo_fg')){
  ctx.save();ctx.globalAlpha=k;ctx.translate(W/2,H/2-40);var s=0.7+0.3*k;ctx.scale(s,s);
  imgC('screens/logo_fg',0,-10,1);
  ctx.restore();
 }
 if(tm>900){ctx.globalAlpha=clamp((tm-900)/500,0,1);txt('© by FG',W/2,H/2+170,28,'#c9b68e','center',700);ctx.globalAlpha=1;}
 if(tm>1500){ctx.globalAlpha=clamp((tm-1500)/600,0,1);txt(t('bootline'),W/2,H/2+212,18,'#8a7b60','center',600);ctx.globalAlpha=1;}
 if(!ASSETS.ready&&ASSETS.total){
  var pct=Math.floor(100*ASSETS.done/ASSETS.total);
  txt((LANG==='de'?'Lade Grafiken ':'Učitavam grafiku ')+pct+'%',W/2,H-40,18,'#8a7b60','center',600);
 }
}
var demoFoe=null,versusFighter=null,versusStage=-1,endingFighter=null;
function drawTitle(tm){
 drawBG(0,tm);
 ctx.save();ctx.fillStyle='rgba(12,8,7,.42)';ctx.fillRect(0,0,W,H);ctx.restore();
 /* Saner pozira */
 if(!demoFoe)demoFoe=mkFighter({x:W/2,dir:1,scale:1.25,style:SANER_STYLE,hp:100});
 demoFoe.x=W/2+250;demoFoe.dir=-1;demoFoe.t=tm;demoFoe.state='idle';
 demoFoe.blocking=(Math.floor(tm/900)%2===1);
 demoFoe.pose=demoFoe.blocking?P.block:P.idle;
 demoFoe.pts=buildPts(demoFoe,demoFoe.pose);
 drawFighter(demoFoe);
 var bob=Math.sin(tm*0.0022)*6;
 ctx.save();ctx.translate(W/2-140,196+bob);ctx.rotate(-0.03);imgC('screens/logo_title',0,0,0.95);ctx.restore();
 txt(TXT.sub[LANG]||TXT.sub.bks,W/2-140,330+bob,26,'#ffdca0','center',700);
 if(Math.floor(tm/500)%2===0)
  txt(TOUCH?t('starttouch'):t('start'),W/2,486,34,'#fff2cd','center',900);
 txt(t('hi')+': '+S.hi,W/2,542,22,'#e4cfa2','center',700);
 txt(t('ctrl'),W/2,588,17,'#cbb894','center',600);
 txt('© by FG  ·  FG Arkada',W/2,H-24,18,'#a7906c','center',700);
 /* language + sound chips */
 img('buttons/lang_chip_normal',CHIP_LANG.x,CHIP_LANG.y,CHIP_LANG.w,CHIP_LANG.h);
 txt(LANG==='de'?'DE':'BKS',CHIP_LANG.x+CHIP_LANG.w/2,CHIP_LANG.y+20,17,'#f0dfb8','center',800);
 img(A.on?'buttons/sound_chip_normal':'buttons/sound_chip_pressed',CHIP_SND.x,CHIP_SND.y,CHIP_SND.w,CHIP_SND.h);
 imgC(A.on?'icons/icon_sound_on':'icons/icon_sound_off',CHIP_SND.x+CHIP_SND.w/2,CHIP_SND.y+CHIP_SND.h/2,1.1);
}
