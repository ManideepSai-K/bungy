const $=id=>document.getElementById(id);
const canvas=$("map"),ctx=canvas.getContext("2d"),S=20;
const configIds=["width","margin","clearance","slope","score","expansions","milliseconds"];
const endpointIds=["sx","sy","gx","gy"];
const colours={distance:"#9edcfa",terrain:"#d7ed9b",quick:"#f3b6d0"};
const names={distance:"Distance A*",terrain:"Terrain A*",quick:"Quick / weighted A*"};
let state=null,results=[],selected="terrain",ready=false,busy=false,driving=false,started=false;
let rover=null,timer,animation=0,animating=false;
const worker=new Worker("worker.js?v=2");
function message(text){$("status").textContent=text;}
function log(text) {
  const li=document.createElement("li");li.textContent=text;$("log").prepend(li);
  while($("log").children.length>30)$("log").lastChild.remove();
}
function controls(){
  const locked=busy||driving||started||animating;
  [...configIds,...endpointIds,"seed"].forEach(id=>$(id).disabled=locked||!ready);
  $("generate").disabled=busy||driving||animating||!ready;
  $("plan").disabled=busy||driving||animating||!ready||!state;
  $("plan").textContent=started?"Reset & compare":"Compare routes";
  const ended=started&&!['SELECTED','MOVED','REPLANNED'].includes(state?.event);
  $("drive").disabled=busy||driving||animating||ended||!results.some(r=>r.mode===selected&&r.status==="SUCCESS");
  $("drive").textContent=started?"Resume mission":"Drive selected route";
  $("pause").disabled=!driving;
}
function error(text){
  clearTimeout(timer);worker.terminate();ready=false;busy=false;driving=false;
  cancelAnimationFrame(animation);message(text+" Reload to retry.");controls();$("drive").disabled=true;
}
function send(op,extra={}){
  if(busy)return;busy=true;controls();
  timer=setTimeout(()=>error("Engine request timed out."),15000);
  worker.postMessage({op,...extra});
}
function inputsValid(){
  return [...configIds,...endpointIds,"seed"].every(id=>$(id).value!==""&&$(id).checkValidity());
}
function endpoints(prefix){return [Number($(prefix+"x").value),Number($(prefix+"y").value)];}
function invalidate(){
  cancelAnimationFrame(animation);results=[];started=false;rover=null;renderCards();controls();
  message("Mission changed. Compare routes to continue.");draw();
}
function updateTelemetry(){
  ["travel","spent","replans","discoveries"].forEach(id=>$(id).textContent=
    id==="travel"?state.travel+" m":id==="spent"?state.spent.toFixed(1):state[id]);
}
function reason(status){
  const map={SUCCESS:"Ready",NO_ROUTE:"No connected safe route on this map",
    SCORE_LIMIT:"Score budget exhausted during search",CANDIDATE_OVER_SCORE:"Candidate exceeds score limit; alternatives may exist",
    TIME_BUDGET:"Search time budget exhausted",EXPANSION_BUDGET:"Cell expansion budget exhausted",
    INTERNAL_ERROR:"Planner error",ARRIVED:"Destination reached. Mission complete.",
    MISSION_SCORE_LIMIT:"Stopped: mission score limit would be exceeded.",
    UNSEEN_HAZARD_STOP:"Stopped: ground truth guard detected a missed hazard.",
    REPLAN_LIMIT:"Stopped: replanning limit reached.",STOPPED:"Mission stopped."};
  if(map[status])return map[status];
  if(status.startsWith("REPLAN_"))return "Replanning stopped: "+reason(status.slice(7));
  return status.toLowerCase().replaceAll("_"," ");
}
function renderCards(){
  $("routes").replaceChildren();
  if(!results.length){const p=document.createElement("p");p.textContent="Compare routes to see distance, score and search effort.";$("routes").append(p);return;}
  for(const r of results){
    const card=document.createElement("button");card.className="route-card"+(r.mode===selected?" selected":"");
    card.style.setProperty("--route",colours[r.mode]);card.disabled=busy||driving||started||r.status!=="SUCCESS";
    const title=document.createElement("h3");title.textContent=names[r.mode];
    const badge=document.createElement("p");badge.textContent=reason(r.status);
    const stats=document.createElement("p");
    stats.textContent=(r.path.length?r.distance+" m \u00b7 score "+r.score.toFixed(1):"No executable route")+" \u00b7 "+r.planning_ms.toFixed(1)+" ms";
    const effort=document.createElement("small");effort.textContent=r.expanded+" cells expanded";
    const rejects=document.createElement("small");rejects.textContent=Object.entries(r.rejected).map(([k,v])=>k.toLowerCase().replaceAll("_"," ")+": "+v).join(" \u00b7 ")||"No unsafe edges encountered";
    card.append(title,badge,stats,effort,rejects);
    card.onclick=()=>{selected=r.mode;renderCards();controls();draw();};
    $("routes").append(card);
  }
}
function draw(){
  ctx.fillStyle="#332e25";ctx.fillRect(0,0,720,720);if(!state)return;
  const world=state.world,layer=$("layer").value,h=layer==="truth"?world.truth:world.known;
  $("maplabel").textContent=layer==="truth"?"OBSERVER / GROUND TRUTH":layer==="slope"?"ROVER / SLOPE":"ROVER / ESTIMATED ELEVATION";
  for(let y=0;y<36;y++)for(let x=0;x<36;x++){
    const gx=(h[y][Math.min(35,x+1)]-h[y][Math.max(0,x-1)])/2;
    const gy=(h[Math.min(35,y+1)][x]-h[Math.max(0,y-1)][x])/2;
    const slope=Math.atan(Math.hypot(gx,gy))*180/Math.PI;
    const light=Math.max(16,Math.min(66,43+h[y][x]*9-gx*15-gy*8));
    ctx.fillStyle=layer==="slope"?"hsl("+Math.max(0,100-slope*3)+",45%,"+(25+slope*.5)+"%)":"hsl(24,34%,"+light+"%)";
    ctx.fillRect(x*S,y*S,S+1,S+1);
    if(world.observed[y][x]){ctx.strokeStyle="#f3efd329";ctx.lineWidth=.7;ctx.strokeRect(x*S+1,y*S+1,S-2,S-2);}
  }
  for(const [x,y,r] of world.rocks){
    ctx.fillStyle="#332f28";ctx.beginPath();ctx.arc((x+.5)*S,(y+.5)*S,r*S,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle="#d5b89a70";ctx.lineWidth=1;ctx.stroke();
  }
  function line(path,color,width,dashed=false){
    if(!path?.length)return;
    ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dashed?[6,5]:[]);ctx.beginPath();
    path.forEach(([x,y],i)=>i?ctx.lineTo((x+.5)*S,(y+.5)*S):ctx.moveTo((x+.5)*S,(y+.5)*S));ctx.stroke();ctx.setLineDash([]);
  }
  if(!started)for(const r of results)line(r.path,colours[r.mode],r.mode===selected?3.5:1.5,r.status!=="SUCCESS");
  else line(state.path,colours[selected],3.5);
  const start=started?state.position:endpoints("s"),goal=endpoints("g");
  for(const [p,label,c] of [[start,"S","#d8ed9a"],[goal,"G","#f6ebd1"]]){
    if(!p.every(Number.isFinite))continue;
    ctx.fillStyle=c;ctx.beginPath();ctx.arc((p[0]+.5)*S,(p[1]+.5)*S,8,0,7);ctx.fill();
    ctx.fillStyle="#1b211b";ctx.font="bold 10px system-ui";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(label,(p[0]+.5)*S,(p[1]+.5)*S);
  }
  const p=rover||start,r=(Number($("width").value)/2+Number($("margin").value))*S;
  if(p.every(Number.isFinite)&&Number.isFinite(r)){
    ctx.strokeStyle="#fff4c9";ctx.lineWidth=1.5;ctx.beginPath();ctx.arc((p[0]+.5)*S,(p[1]+.5)*S,r,0,7);ctx.stroke();
    ctx.fillStyle="#e6eecf";ctx.fillRect((p[0]+.5)*S-5,(p[1]+.5)*S-4,10,8);
  }
}
function animateMove(from,to,done){
  animating=true;controls();
  const began=performance.now();
  function tick(now){
    const t=Math.min(1,(now-began)/130);
    rover=[from[0]+(to[0]-from[0])*t,from[1]+(to[1]-from[1])*t];draw();
    if(t<1)animation=requestAnimationFrame(tick);else {animating=false;done();}
  }animation=requestAnimationFrame(tick);
}
timer=setTimeout(()=>error("Python loading timed out."),90000);
worker.onerror=()=>error("Simulation worker failed.");
worker.onmessage=({data})=>{
  clearTimeout(timer);busy=false;
  if(data.type==="error"){error("Simulation engine failed.");return;}
  if(data.type==="ready"){ready=true;send("generate",{seed:Number($("seed").value)});return;}
  const r=data.result;
  if(r.event==="INVALID_INPUT"){driving=false;message(r.message);controls();return;}
  const old=state?.position;state=r;updateTelemetry();
  if(r.event==="GENERATED"){
    results=[];started=false;driving=false;rover=null;$("comparisonTime").textContent="";
    message("Surface ready. Set endpoints and compare routes.");log("Generated terrain seed "+r.world.seed+".");
  }else if(r.event==="COMPARED"){
    results=r.results;started=false;rover=null;
    selected=results.find(v=>v.mode==="terrain"&&v.status==="SUCCESS")?.mode||results.find(v=>v.status==="SUCCESS")?.mode||"terrain";
    $("comparisonTime").textContent="Total comparison: "+r.comparison_ms.toFixed(0)+" ms (including safety-map setup)";
    message(results.some(v=>v.status==="SUCCESS")?"Select a successful route, then drive.":"No candidate accepted. See each outcome below.");
    log("Compared three strategies on the same estimated map.");
  }else if(r.event==="SELECTED"){
    started=true;message("Driving. Nearby terrain is checked before each step.");
  }else if(r.event==="REPLANNED"){
    message("New terrain blocked the route. A replacement route is ready.");
    log("Replanned after local sensing: "+r.last_plan.planning_ms.toFixed(1)+" ms.");
  }else if(r.event==="MOVED"){
    if(r.new_details)log("Local scan refined "+r.new_details+" terrain cells.");
    message("Driving: "+r.travel+" m travelled.");
    controls();renderCards();
    animateMove(old,r.position,()=>{if(driving)send("step");else controls();});return;
  }else{
    driving=false;
    message(reason(r.event));log(reason(r.event));
    // A terminated mission requires a fresh comparison, not a misleading resume.
    started=true;
  }
  draw();renderCards();controls();
  if(driving&&(r.event==="SELECTED"||r.event==="REPLANNED"))send("step");
};
$("generate").onclick=()=>{
  if(!$("seed").checkValidity()||$("seed").value===""){message("Enter a valid seed.");return;}
  cancelAnimationFrame(animation);started=false;send("generate",{seed:Number($("seed").value)});
};
$("plan").onclick=()=>{
  if(!inputsValid()){message("Check the ranges on mission settings.");return;}
  cancelAnimationFrame(animation);driving=false;started=false;results=[];renderCards();message("Comparing bounded searches...");
  send("compare",{start:endpoints("s"),goal:endpoints("g"),settings:Object.fromEntries(configIds.map(id=>[id,Number($(id).value)]))});
};
$("drive").onclick=()=>{
  driving=true;controls();renderCards();
  if(started)send("step");else send("select",{mode:selected});
};
$("pause").onclick=()=>{driving=false;message("Paused. Resume or reset & compare.");controls();renderCards();};
[...configIds,...endpointIds].forEach(id=>$(id).oninput=invalidate);
$("layer").onchange=draw;
canvas.onclick=e=>{
  if(!ready||busy||driving||started)return;
  const rect=canvas.getBoundingClientRect(),p=$("mode").value==="start"?"s":"g";
  $(p+"x").value=Math.max(0,Math.min(35,Math.floor((e.clientX-rect.left)/rect.width*36)));
  $(p+"y").value=Math.max(0,Math.min(35,Math.floor((e.clientY-rect.top)/rect.height*36)));
  invalidate();
};
controls();draw();

