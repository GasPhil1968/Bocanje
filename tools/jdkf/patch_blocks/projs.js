function drawProjs(){
 for(var i=0;i<projs.length;i++){
  var q=projs[i],k=q.kind==='mrkonja'?'props/knife_projectile':'props/plum_projectile',d=q.vx<0?-1:1;
  ctx.save();ctx.translate(q.x,q.y);
  /* motion ghost */
  ctx.save();ctx.globalAlpha=.22;ctx.translate(-d*18,0);ctx.rotate(q.rot-0.35);ctx.scale(d,1);imgC(k,0,0,0.9);ctx.restore();
  ctx.rotate(q.rot);ctx.scale(d,1);imgC(k,0,0,1);
  ctx.restore();
 }
}
