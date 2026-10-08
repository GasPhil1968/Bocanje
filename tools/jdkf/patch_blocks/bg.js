/* stage plates are single images (bg_0..bg_6); everything that moves is an overlay sprite */
var TORCH_X=[108,284,459,633,808,983,1158],TORCH_TOP=509;
function wrapX(v,span){span=span||W;return ((v%span)+span)%span;}
function crowdRow(tm,a){
 var im=I('overlays/crowd_row_'+(1+Math.floor(tm/420)%2));if(!im)return;
 var w=im.naturalWidth,h=im.naturalHeight;ctx.globalAlpha=a;
 for(var x=0;x<W;x+=w)ctx.drawImage(im,x,GROUND-2-h,w,h);
}
function drawAmbient(idx,tm){
 ctx.save();
 if(idx===0||idx===1||idx===5)crowdRow(tm,idx===1?.35:.45);
 if(idx===0){
  /* pigeons */
  for(var a=0;a<5;a++){var dirA=a%2?1:-1,ax=wrapX(150+a*243+tm*.014*dirA),ay=235+(a*43)%120;ctx.save();ctx.translate(ax,ay);if(dirA<0)ctx.scale(-1,1);ctx.globalAlpha=.85;imgC('overlays/pigeon_'+(1+Math.floor(tm/170+a)%2),0,0,1.2);ctx.restore();}
 }
 if(idx===1){
  /* drifting leaves + falling plums */
  ctx.globalAlpha=.85;
  for(var i=0;i<18;i++){var x=wrapX(i*83+tm*.012),y=280+(i*37)%260;imgC('overlays/leaf_'+(1+i%3),x,y,1.5,tm*.001+i);}
  ctx.globalAlpha=.9;
  for(var pl=0;pl<4;pl++){var py=GROUND-140+((tm*.05+pl*37)%120),px2=160+pl*270+Math.sin(tm*.004+pl)*12;imgC('overlays/falling_plum',px2,py,1.3);}
 }
 if(idx===2||idx===4){
  /* water glints + gulls */
  ctx.globalAlpha=.75;
  for(var j=0;j<16;j++)imgC('overlays/water_glint_'+(1+Math.floor(tm/240+j)%3),wrapX(j*97+tm*.04),idx===2?560+(j*11)%28:470+(j*17)%105,1);
  ctx.globalAlpha=.9;
  for(var g=0;g<3;g++){var gx=wrapX(tm*.015+g*330),gy=(idx===2?170:140)+g*32;imgC('overlays/gull_'+(1+Math.floor(tm/200+g)%2),gx,gy,1.3);}
  if(idx===4){ctx.globalAlpha=1;var bx=(tm*.03)%(W+140)-70;imgC('overlays/sailboat',bx+26,GROUND-176,1.15);}
 }
 if(idx===3){
  /* mist + fireflies */
  ctx.globalAlpha=.32;
  for(var m=0;m<4;m++){var mx=((m*370+tm*.008)%1600)-170;imgC('overlays/mist_bank',mx,440+m*23,2);}
  for(var ff=0;ff<14;ff++){var fx2=wrapX(ff*103+tm*.02),fy2=300+(ff*47)%180+Math.sin(tm*.003+ff)*10;ctx.globalAlpha=.85;imgC('overlays/firefly_'+(1+Math.floor(tm/260+ff)%2),fx2,fy2,1.5);}
 }
 if(idx===5){
  /* banners on the Kastel wall */
  ctx.globalAlpha=.95;
  for(var b=0;b<3;b++)imgC('overlays/banner_'+(b===1?'oxblood':'brass')+'_'+(1+Math.floor(tm/210+b)%3),239+b*410,377,2);
 }
 if(idx===6){
  /* stars, torches, smoke, cat */
  for(var st2=0;st2<60;st2++){ctx.globalAlpha=0.3+0.6*Math.abs(Math.sin(tm*0.002+st2));imgC('overlays/star_'+(1+st2%2),(st2*211)%W,(st2*97)%320,1.4);}
  for(var q=0;q<TORCH_X.length;q++){
   var tx=TORCH_X[q],fl=Math.sin(tm*.014+q);
   ctx.globalAlpha=.30+.06*fl;imgC('overlays/torch_glow',tx,TORCH_TOP-16,1.5+fl*.05);
   ctx.globalAlpha=1;imgC('overlays/torch_flame_'+(1+Math.floor(tm/90+q)%4),tx,TORCH_TOP-18,1.6);
   ctx.globalAlpha=.35;imgC('overlays/smoke_wisp_'+(1+Math.floor(tm/260+q)%3),tx+3,TORCH_TOP-64,1.5);
  }
  ctx.globalAlpha=.9;var catx=((tm*.04)%(W+120))-60;imgC('overlays/cat_'+(1+Math.floor(tm/120)%4),catx,GROUND-16,1.5);
 }
 ctx.restore();
}
function drawBG(idx,tm){
 if(!img('bg/bg_'+idx,0,0,W,H)){ctx.fillStyle='#120d0a';ctx.fillRect(0,0,W,H);}
 drawAmbient(idx,tm);
}
