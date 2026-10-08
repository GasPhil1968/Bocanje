function speechBubble(x,y,w,text,name,flip,accent){
 var lineFont='700 22px Trebuchet MS, Verdana, system-ui, sans-serif', lines=wrapLines(text,w-26,lineFont), h=56+lines.length*24;
 ctx.save();ctx.translate(x,y);
 var tail=I('screens/speech_tail');
 if(tail){ctx.save();ctx.translate(flip?30:w-30,h-8);if(!flip)ctx.scale(-1,1);ctx.drawImage(tail,-8,0,36,25);ctx.restore();}
 nine('screens/speech_bubble_9slice',0,0,w,h,66,24,24,24);
 ctx.fillStyle='#fff3cf';ctx.font='900 16px Trebuchet MS, Verdana, system-ui, sans-serif';ctx.textAlign='left';ctx.fillText(name,14,23);
 ctx.font=lineFont;ctx.fillStyle='#2a211c';for(var i=0;i<lines.length;i++)ctx.fillText(lines[i],14,54+i*24);
 ctx.restore();
}
