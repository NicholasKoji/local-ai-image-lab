import copy
import json
from pathlib import Path

work = Path(__file__).resolve().parent
out = work.parent / 'outputs'
root = Path(r'D:\AI\ComfyUI')
target = root / 'user/default/workflows/Krea2_Turbo_6GB.json'
before = work / 'krea2-before-q2.json'
if not before.exists():
    before.write_bytes(target.read_bytes())
w = json.loads(before.read_text(encoding='utf-8'))
nodes = {n['id']:n for n in w['nodes']}
loader = nodes[10]
loader.update(type='UnetLoaderGGUFAdvanced', title='主模型 · Krea 2 Turbo Q2_K',
              properties={'Node name for S&R':'UnetLoaderGGUFAdvanced'},
              widgets_values=['krea2_turbo-Q2_K.gguf','default','default',False],
              size=[390,190])
loader['inputs'] = []
nodes[11]['pos'] = [20,430]
nodes[11].update(type='Krea2TextGGUFLoader',title='文本编码器 · Qwen3VL 4B Q4_K_M',
                 widgets_values=['Qwen3VL-4B-Instruct-Q4_K_M.gguf','cpu'],
                 properties={'Node name for S&R':'Krea2TextGGUFLoader'},inputs=[])
nodes[12]['pos'] = [20,650]
compute = {'id':30,'type':'ModelComputeDtype','pos':[20,260],'size':[390,110],
           'flags':{},'order':1,'mode':0,'title':'计算精度 · FP16（短测验证后使用）',
           'inputs':[{'name':'model','type':'MODEL','link':10}],
           'outputs':[{'name':'MODEL','type':'MODEL','links':[]}],
           'properties':{'Node name for S&R':'ModelComputeDtype','cnr_id':'comfy-core'},
           'widgets_values':['fp16']}
for link in w['links']:
    if link[1] == 10 and link[3] == 3:
        link[1] = 30
        compute['outputs'][0]['links'].append(link[0])
loader['outputs'][0]['links'] = [10]
w['links'].append([10,10,0,30,0,'MODEL'])
w['nodes'].append(compute)
w['last_node_id'] = 30
w['last_link_id'] = 10
nodes[29]['widgets_values'] = ['Krea2_Turbo_Q2_K']
nodes[3]['widgets_values'] = [20261013,'randomize',8,1.0,'euler','simple',1.0]
api = json.loads((work/'krea2-prompt.json').read_text(encoding='utf-8'))['prompt']
api['10'] = {'class_type':'UnetLoaderGGUFAdvanced','inputs':{
    'unet_name':'krea2_turbo-Q2_K.gguf','dequant_dtype':'default','patch_dtype':'default','patch_on_device':False}}
api['11'] = {'class_type':'Krea2TextGGUFLoader','inputs':{
    'clip_name':'Qwen3VL-4B-Instruct-Q4_K_M.gguf','device':'cpu'}}
api['30'] = {'class_type':'ModelComputeDtype','inputs':{'model':['10',0],'dtype':'fp16'}}
api['3']['inputs']['model'] = ['30',0]
api['3']['inputs']['steps'] = 8
api['29']['inputs']['filename_prefix'] = 'Krea2_Q2_K_First_Test'
request = {'prompt':api,'extra_data':{'extra_pnginfo':{'workflow':w}}}
(work/'krea2-q2-full.json').write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
smoke = copy.deepcopy(request)
smoke['prompt']['3']['inputs']['steps'] = 2
smoke['prompt']['29']['inputs']['filename_prefix'] = 'Krea2_Q2_K_2step_Speed_Test'
snodes = {n['id']:n for n in smoke['extra_data']['extra_pnginfo']['workflow']['nodes']}
snodes[3]['widgets_values'][2] = 2
snodes[3]['title'] = '短测专用 · 2 步，不代表完整画质'
(work/'krea2-q2-smoke.json').write_text(json.dumps(smoke,ensure_ascii=False),encoding='utf-8')
(work/'krea2-q2-workflow.json').write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared Q2_K workflow and 2-step precision/speed check; active user workflow is not replaced yet.')
