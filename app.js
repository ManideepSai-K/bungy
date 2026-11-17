const $ = id => document.getElementById(id);
const canvas = $("map"), ctx = canvas.getContext("2d"), size = 60;
let grid, path = [], rover = null, frame = 0, ready = false, busy = false, timer;
const inputs = ["sx","sy","gx","gy"];
const point = prefix => [Number($(prefix+"x").value), Number($(prefix+"y").value)];
function makeMap() {
  grid = Array.from({length:12}, () => Array(12).fill(0));
  for(let y=0;y<12;y++) if(y!==5 || $("seal").checked) grid[y][6]=1;
  [[2,2],[3,2],[2,3],[9,8],[9,9],[10,9]].forEach(([x,y])=>grid[y][x]=1);
}
function stop() {cancelAnimationFrame(frame); rover=null;}
function invalidate() {
  stop(); path=[]; $("drive").disabled=true;
  ["distance","time","expanded"].forEach(id=>$(id).textContent="—");
  if(ready) $("status").textContent="Mission changed. Plan a route to continue.";
  draw();
}
function draw() {
  ctx.clearRect(0,0,720,720);
  for(let y=0;y<12;y++) for(let x=0;x<12;x++) {
    ctx.fillStyle=["#98684c","#a17050","#aa7856","#92654a"][(x*7+y*3)%4];
    ctx.fillRect(x*size,y*size,size,size);
    ctx.strokeStyle="#201d1625";ctx.strokeRect(x*size,y*size,size,size);
    if(grid[y][x]) {
      ctx.fillStyle="#4c4438";ctx.beginPath();
      ctx.moveTo(x*size+9,y*size+39);ctx.lineTo(x*size+15,y*size+12);
      ctx.lineTo(x*size+40,y*size+7);ctx.lineTo(x*size+52,y*size+32);
      ctx.lineTo(x*size+40,y*size+50);ctx.closePath();ctx.fill();
      ctx.strokeStyle="#c8a68170";ctx.stroke();
    }
  }
  if(path.length) {
    ctx.strokeStyle="#d9f29d";ctx.lineWidth=5;ctx.lineJoin="round";ctx.beginPath();
    path.forEach(([x,y],i)=>i?ctx.lineTo((x+.5)*size,(y+.5)*size):ctx.moveTo((x+.5)*size,(y+.5)*size));ctx.stroke();
  }
  [["s","#c9efa2","S"],["g","#f3e2bd","G"]].forEach(([prefix,color,label])=>{
    const [x,y]=point(prefix);if(!Number.isFinite(x+y))return;
    ctx.fillStyle=color;ctx.beginPath();ctx.arc((x+.5)*size,(y+.5)*size,16,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#202620";ctx.font="bold 15px system-ui";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(label,(x+.5)*size,(y+.5)*size);
  });
  if(rover) {
    const [x,y]=rover;ctx.fillStyle="#172421";ctx.fillRect((x+.5)*size-16,(y+.5)*size-12,32,24);
    ctx.fillStyle="#e9f5ca";ctx.fillRect((x+.5)*size-10,(y+.5)*size-8,20,16);
  }
}
function lock(value) {
  busy=value;inputs.forEach(id=>$(id).disabled=value);$("seal").disabled=value;
  $("reset").disabled=value;$("plan").disabled=value||!ready;
}
const worker = new Worker("worker.js");
function fail(message) {
  clearTimeout(timer);worker.terminate();ready=false;lock(false);
  $("plan").textContent="Reload to retry";$("drive").disabled=true;
  $("status").textContent=message;
}
timer=setTimeout(()=>fail("Python loading timed out. Check your internet connection and reload."),90000);
worker.onerror=()=>fail("The planning worker failed. Reload to retry.");
worker.onmessage=({data})=>{
  clearTimeout(timer);
  if(data.type==="ready") {
    ready=true;lock(false);$("plan").textContent="Plan route →";
    $("status").textContent="Ready. Place your endpoints or try the default mission.";
  } else if(data.type==="error") fail("Python could not run. Check your connection and reload.");
  else {
    lock(false);const r=data.result;path=r.path||[];draw();
    const messages={SUCCESS:"Route found. Ready to drive.",NO_ROUTE:"No route: the free cells do not connect these endpoints.",START_BLOCKED:"Start is inside a rock. Choose a free cell.",GOAL_BLOCKED:"Destination is inside a rock. Choose a free cell.",BUDGET_EXCEEDED:"Planning budget exceeded; this does not prove no route exists."};
    $("status").textContent=messages[r.status]||"Invalid mission: "+r.status;
    $("distance").textContent=r.distance_m==null?"—":r.distance_m+" m";
    $("time").textContent=r.planning_ms==null?"—":r.planning_ms.toFixed(2)+" ms";
    $("expanded").textContent=r.expanded??"—";$("drive").disabled=r.status!=="SUCCESS";
  }
};
$("plan").onclick=()=>{
  if(inputs.some(id=>!$(id).checkValidity()||$(id).value==="")) {
    $("status").textContent="Enter whole-number coordinates from 0 to 11.";return;
  }
  invalidate();lock(true);$("status").textContent="Planning…";
  timer=setTimeout(()=>fail("Planning timed out. Reload to restart the engine."),10000);
  worker.postMessage({grid,start:point("s"),goal:point("g")});
};
canvas.onclick=e=>{
  if(busy)return;const rect=canvas.getBoundingClientRect();
  const x=Math.min(11,Math.max(0,Math.floor((e.clientX-rect.left)/rect.width*12)));
  const y=Math.min(11,Math.max(0,Math.floor((e.clientY-rect.top)/rect.height*12)));
  const prefix=$("mode").value==="start"?"s":"g";
  $(prefix+"x").value=x;$(prefix+"y").value=y;invalidate();
};
inputs.forEach(id=>$(id).oninput=invalidate);
$("seal").onchange=()=>{makeMap();invalidate();};
$("reset").onclick=()=>{
  [1,9,10,2].forEach((v,i)=>$(inputs[i]).value=v);$("seal").checked=false;
  makeMap();invalidate();
};
$("drive").onclick=()=>{
  stop();$("drive").disabled=true;const began=performance.now();
  function tick(now) {
    const progress=Math.min((now-began)/300,path.length-1),i=Math.floor(progress),t=progress-i;
    const a=path[i],b=path[Math.min(i+1,path.length-1)];
    rover=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];draw();
    if(progress<path.length-1)frame=requestAnimationFrame(tick);
    else {$("status").textContent="Destination reached. Mission complete.";$("drive").disabled=false;}
  }
  frame=requestAnimationFrame(tick);
};
makeMap();draw();
