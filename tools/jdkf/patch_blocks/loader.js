
/* ============================================================
   ASSETS - every graphic is a raster image (asset pack v1)
   Files are 2x game size; img()/imgC() draw them at half size.
   ============================================================ */
var ASSET_BASE='../assets/';
var ASSET_MANIFEST=/*@@MANIFEST@@*/null;
var ASSET_DATA=/*@@DATA@@*/null;
var IMG={},FR={},ASSETS={total:0,done:0,ready:false};
function assetURL(rel){return (ASSET_DATA&&ASSET_DATA[rel])||(ASSET_BASE+rel);}
function loadImg(rel){
 ASSETS.total++;var im=new Image();
 im.onload=im.onerror=function(){ASSETS.done++;if(ASSETS.done>=ASSETS.total)ASSETS.ready=true;};
 im.src=assetURL(rel);return im;
}
function loadAssets(man){
 var k,id,n,d;
 for(k in man.images)IMG[k]=loadImg(man.images[k]);
 for(id in man.fighters){FR[id]={};for(n in man.fighters[id]){d=man.fighters[id][n];FR[id][n]={im:loadImg(d.src),ox:d.ox/2,oy:d.oy/2,w:d.w/2,h:d.h/2};}}
 if(!ASSETS.total)ASSETS.ready=true;
 try{var ri=document.getElementById('rotimg');if(ri&&man.images['icons/icon_rotate_phone'])ri.src=assetURL(man.images['icons/icon_rotate_phone']);}catch(e){}
}
if(ASSET_MANIFEST)loadAssets(ASSET_MANIFEST);
else{try{fetch(ASSET_BASE+'manifest.json').then(function(r){return r.json();}).then(loadAssets)['catch'](function(){ASSETS.ready=true;});}catch(e){ASSETS.ready=true;}}
function I(k){var im=IMG[k];return (im&&im.complete&&im.naturalWidth)?im:null;}
/* top-left placement; default size = half the file size */
function img(k,x,y,w,h){var im=I(k);if(!im)return false;ctx.drawImage(im,x,y,w===undefined?im.naturalWidth/2:w,h===undefined?im.naturalHeight/2:h);return true;}
/* centred placement, sc = extra scale, optional rotation */
function imgC(k,cx,cy,sc,rot){
 var im=I(k);if(!im)return false;var w=im.naturalWidth/2*(sc||1),h=im.naturalHeight/2*(sc||1);
 if(rot){ctx.save();ctx.translate(cx,cy);ctx.rotate(rot);ctx.drawImage(im,-w/2,-h/2,w,h);ctx.restore();}
 else ctx.drawImage(im,cx-w/2,cy-h/2,w,h);
 return true;
}
/* 9-slice; insets t,r,b,l are file pixels, drawn at half size */
function nine(k,x,y,w,h,t,r,b,l){
 var im=I(k);if(!im)return false;var iw=im.naturalWidth,ih=im.naturalHeight;
 var sx=[0,l,iw-r,iw],sy=[0,t,ih-b,ih],dx=[x,x+l/2,x+w-r/2,x+w],dy=[y,y+t/2,y+h-b/2,y+h];
 for(var j=0;j<3;j++)for(var i=0;i<3;i++){
  var sw=sx[i+1]-sx[i],sh=sy[j+1]-sy[j],dw=dx[i+1]-dx[i],dh=dy[j+1]-dy[j];
  if(sw>0&&sh>0&&dw>0&&dh>0)ctx.drawImage(im,sx[i],sy[j],sw,sh,dx[i],dy[j],dw,dh);
 }
 return true;
}
