let engine;
async function initialize() {
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.29.4/full/pyodide.js");
  engine = await loadPyodide();
  const response = await fetch("simulator.py?v=2");
  if (!response.ok) throw new Error("Cannot load simulation engine");
  await engine.runPythonAsync(await response.text());
  postMessage({type:"ready"});
}
initialize().catch(error=>postMessage({type:"error",message:String(error)}));
onmessage=({data})=>{
  try {
    engine.globals.set("mission_payload",JSON.stringify(data));
    postMessage({type:"result",result:JSON.parse(engine.runPython("dispatch(mission_payload)"))});
  } catch(error) {postMessage({type:"error",message:String(error)});}
};

