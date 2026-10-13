"""One bounded Anima run on an isolated ComfyUI port, with telemetry and cleanup.

Shares read-only model/source locations, but never alters the normal 8188 service.
Results include exact request, command, node timing, server logs and NVIDIA samples.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--python", default=r"D:\AI\ComfyUI\.venv\Scripts\python.exe")
parser.add_argument("--comfy", type=Path, default=Path(r"D:\AI\ComfyUI"))
parser.add_argument("--label", required=True)
parser.add_argument("--profile", action="store_true")
parser.add_argument("--int8", action="store_true")
parser.add_argument("--port", type=int, default=8189)
parser.add_argument("--timeout", type=int, default=600)
parser.add_argument("--steps", type=int, default=4)
args = parser.parse_args()
if args.steps < 1:
    parser.error("steps must be positive")
if not args.label.replace("-", "").replace("_", "").isalnum():
    parser.error("label must be alphanumeric with dashes/underscores")
out = ROOT / "generated/benchmark" / args.label
out.mkdir(parents=True, exist_ok=False)
for folder in ("user", "images", "temporary"):
    (out / folder).mkdir()
base = f"http://127.0.0.1:{args.port}"


def api(path, data=None):
    request = urllib.request.Request(base + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


with socket.socket() as check:
    if check.connect_ex(("127.0.0.1", args.port)) == 0:
        raise RuntimeError("Benchmark port is already occupied; refusing to reuse another service")
config = out / "extra_paths.yaml"
config.write_text("lab:\n  custom_nodes: " + (ROOT / "scripts/benchmark/nodes").as_posix() + "\n", encoding="utf-8")
env = os.environ.copy()
env.update({"PYTHONUTF8":"1", "OMP_NUM_THREADS":"6", "MKL_NUM_THREADS":"6",
    "HF_HOME":r"D:\AI\cache\huggingface", "TORCH_HOME":r"D:\AI\cache\torch",
    "TEMP":r"D:\AI\temp", "TMP":r"D:\AI\temp",
    "LAB_RESULT_DIR":str(out), "LAB_PROFILE":"1" if args.profile else "0"})
command = [args.python, str(args.comfy / "main.py"), "--listen", "127.0.0.1", "--port", str(args.port),
    "--fp16-unet", "--cpu-vae", "--disable-pinned-memory", "--reserve-vram", "0.8",
    "--disable-partner-nodes", "--disable-auto-launch", "--preview-method", "none",
    "--extra-model-paths-config", str(config), "--user-directory", str(out / "user"),
    "--output-directory", str(out / "images"), "--temp-directory", str(out / "temporary"),
    "--database-url", "sqlite:///:memory:"]
(out / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
query = "timestamp,temperature.gpu,utilization.gpu,clocks.gr,clocks.mem,memory.used,power.draw,clocks_throttle_reasons.active,clocks_throttle_reasons.sw_thermal_slowdown,clocks_throttle_reasons.hw_thermal_slowdown,clocks_throttle_reasons.hw_power_brake_slowdown"
status = {"label":args.label, "profile":args.profile, "int8":args.int8, "steps":args.steps, "success":False}
log = (out / "server.log").open("w", encoding="utf-8")
telemetry = (out / "gpu.csv").open("w", encoding="utf-8", newline="")
writer = csv.writer(telemetry)
writer.writerow(query.split(","))
process = subprocess.Popen(command, cwd=args.comfy, env=env, stdout=log, stderr=subprocess.STDOUT,
                           creationflags=subprocess.CREATE_NO_WINDOW)
status["server_parent_pid"] = process.pid
try:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Benchmark server exited: {process.returncode}")
        try:
            api("/system_stats")
            break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)
    else:
        raise TimeoutError("Benchmark server startup timeout")
    info = api("/object_info/LabProfileKSampler")
    if "LabProfileKSampler" not in info:
        raise RuntimeError("Profiler node did not load; inspect server.log")
    request = json.loads((ROOT / "workflows/api/anima-q5-smoke.json").read_text(encoding="utf-8"))
    request["prompt"]["76"]["class_type"] = "LabProfileKSampler"
    request["prompt"]["76"]["inputs"]["steps"] = args.steps
    request["prompt"]["46"]["inputs"]["filename_prefix"] = args.label
    if args.int8:
        request["prompt"]["78"] = {"class_type":"UNETLoader", "inputs":{
            "unet_name":"Anima-2.9B-preview-v1_int8_convrot.safetensors", "weight_dtype":"default"}}
    for node in request["extra_data"]["extra_pnginfo"]["workflow"]["nodes"]:
        if node["id"] == 76:
            node["type"] = "LabProfileKSampler"
            node["properties"]["Node name for S&R"] = "LabProfileKSampler"
            node["widgets_values"][1] = "fixed"
            node["widgets_values"][2] = args.steps
            node["title"] = f"Anima benchmark · {args.steps} steps"
        if args.int8 and node["id"] == 78:
            node["type"] = "UNETLoader"
            node["properties"] = {"Node name for S&R":"UNETLoader"}
            node["widgets_values"] = ["Anima-2.9B-preview-v1_int8_convrot.safetensors", "default"]
            node["title"] = "Anima 2.9B INT8 ConvRot"
    (out / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    submitted = api("/prompt", request)
    prompt_id = submitted["prompt_id"]
    status["prompt_id"] = prompt_id
    print(f"SUBMITTED {args.label} {prompt_id}", flush=True)
    start = time.monotonic()
    while time.monotonic() - start < args.timeout:
        metrics = subprocess.run(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        if metrics.returncode == 0:
            row = next(csv.reader(io.StringIO(metrics.stdout)))
            writer.writerow([v.strip() for v in row]); telemetry.flush()
            if float(row[1]) >= 92:
                api("/interrupt", {}); raise RuntimeError("Temperature reached 92 C; test interrupted")
        try:
            history = api("/history/" + prompt_id)
        except (urllib.error.URLError, TimeoutError):
            if process.poll() is not None:
                raise RuntimeError("Benchmark server exited during execution")
            continue  # Long CPU summaries can temporarily delay the HTTP event loop.
        if prompt_id in history:
            (out / "history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            status["success"] = history[prompt_id]["status"]["status_str"] == "success"
            status["request_wall_seconds"] = time.monotonic() - start
            break
        if process.poll() is not None:
            raise RuntimeError("Benchmark server exited during execution")
        time.sleep(2)
    else:
        api("/interrupt", {}); raise TimeoutError("Bounded benchmark exceeded deadline")
    if not status["success"]:
        raise RuntimeError("Generation failed; inspect history.json")
    print(json.dumps(status), flush=True)
except Exception as error:
    status["error"] = repr(error)
    raise
finally:
    try:
        api("/free", {"unload_models":True,"free_memory":True})
    except Exception:
        pass
    # Kill only this spawned Python process tree (venv launcher plus runtime child).
    import psutil
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            child.terminate()
        parent.terminate()
        psutil.wait_procs(children + [parent], timeout=10)
    except psutil.NoSuchProcess:
        pass
    telemetry.close(); log.close()
    status["server_exit_code"] = process.poll()
    (out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
