/* Python runs off the UI thread. Runtime is pinned for reproducibility. */
let engine;
async function initialize() {
  importScripts("https://cdn.jsdelivr.net/pyodide/v0.29.4/full/pyodide.js");
  engine = await loadPyodide();
  const response = await fetch("planner.py");
  if (!response.ok) throw new Error("Cannot load planner.py");
  await engine.runPythonAsync(await response.text());
  postMessage({type: "ready"});
}
initialize().catch(error => postMessage({type:"error", message:String(error)}));
onmessage = async ({data}) => {
  try {
    engine.globals.set("mission_payload", JSON.stringify(data));
    const result = JSON.parse(engine.runPython("plan_json(mission_payload)"));
    postMessage({type:"result", result});
  } catch(error) { postMessage({type:"error", message:String(error)}); }
};
