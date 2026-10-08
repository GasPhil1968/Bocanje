function partKind(c){
 switch(c){
  case '#ff9a7a':case '#ff6b5a':case '#ff9a4a':return 'salmon';
  case '#b67a42':return 'wood';
  case '#dce8ef':return 'steel';
  case '#d8cdb5':case '#c58ad4':return 'cloth';
  case '#e4c993':return 'dust';
 }
 return 'gold';
}
function drawParts(){
 for(var i=0;i<parts.length;i++){
  var p=parts[i],k=1-p.t/p.life,pr=1-k,kind=partKind(p.c),fi;
  if(p.type==='s'){
   ctx.globalAlpha=Math.min(1,k*1.4);
   if(kind==='dust'){fi=1+Math.min(2,Math.floor(pr*3));imgC('fx/dust_puff_'+fi,p.x,p.y,p.r/5);}
   else if(kind==='wood'||kind==='steel'||kind==='cloth'){fi=1+Math.min(2,Math.floor(pr*3));imgC('fx/spark_'+kind+'_'+fi,p.x,p.y,p.r/4);}
   else{fi=1+Math.min(3,Math.floor(pr*4));imgC('fx/hit_spark_'+kind+'_'+fi,p.x,p.y,p.r/7);}
  }else if(p.type==='r'){
   ctx.globalAlpha=Math.min(1,k*1.2);fi=1+Math.min(3,Math.floor(pr*4));
   imgC('fx/impact_ring_'+(kind==='salmon'?'salmon':'gold')+'_'+fi,p.x,p.y,p.r/22);
  }else{
   ctx.save();ctx.globalAlpha=clamp(k*1.6,0,1);
   ctx.translate(p.x,p.y-(1-k)*34);ctx.rotate(p.rot);
   var sc=0.7+0.5*(1-k*k);ctx.scale(sc,sc);
   imgC('fx/comic_burst_'+(p.rot<0?1:2)+'_'+(kind==='salmon'?'salmon':'gold'),0,-13,1.45);
   ctx.font='900 40px Impact,Haettenschweiler,system-ui,sans-serif';
   ctx.textAlign='center';ctx.lineJoin='round';
   ctx.lineWidth=7;ctx.strokeStyle=INK;ctx.strokeText(p.txt,0,0);
   ctx.fillStyle='#fff6dc';ctx.fillText(p.txt,0,0);
   ctx.restore();
  }
 }
 ctx.globalAlpha=1;
}
