import copy
import json
from pathlib import Path

work = Path(__file__).resolve().parent
request = json.loads((work / 'anima-prompt.json').read_text(encoding='utf-8'))
w = request['extra_data']['extra_pnginfo']['workflow']
nodes = {n['id']: n for n in w['nodes']}
nodes[78].update(type='UnetLoaderGGUFAdvanced', title='主模型 · Anima 2.9B Q5_0',
                 widgets_values=['Anima-2.9B-preview-v1-Q5_0.gguf', 'default', 'default', False],
                 properties={'Node name for S&R': 'UnetLoaderGGUFAdvanced'}, size=[380,190])
nodes[71]['widgets_values'][2] = 'cpu'
nodes[71]['title'] = '文本编码器 · Qwen 0.6B / CPU'
nodes[71]['pos'] = [20,420]
nodes[72]['pos'] = [20,610]
compute = {'id':79, 'type':'ModelComputeDtype', 'pos':[20,260], 'size':[380,110],
           'flags':{}, 'order':1, 'mode':0, 'title':'计算精度 · FP16',
           'inputs':[{'name':'model','type':'MODEL','link':10}],
           'outputs':[{'name':'MODEL','type':'MODEL','links':[3]}],
           'properties':{'Node name for S&R':'ModelComputeDtype','cnr_id':'comfy-core'},
           'widgets_values':['fp16']}
nodes[78]['outputs'][0]['links'] = [10]
for link in w['links']:
    if link[0] == 3:
        link[1] = 79
w['nodes'].append(compute)
w['links'].append([10,78,0,79,0,'MODEL'])
w['last_node_id'] = 79
w['last_link_id'] = 10
nodes[46]['widgets_values'] = ['Anima_2.9B_Q5']
api = request['prompt']
api['78'] = {'class_type':'UnetLoaderGGUFAdvanced','inputs':{
    'unet_name':'Anima-2.9B-preview-v1-Q5_0.gguf','dequant_dtype':'default',
    'patch_dtype':'default','patch_on_device':False}}
api['79'] = {'class_type':'ModelComputeDtype','inputs':{'model':['78',0],'dtype':'fp16'}}
api['76']['inputs']['model'] = ['79',0]
api['71']['inputs']['device'] = 'cpu'
api['46']['inputs']['filename_prefix'] = 'Anima_2.9B_Q5_28step'
(work/'anima-q5-full.json').write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
(work/'anima-q5-workflow.json').write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
short = copy.deepcopy(request)
short['prompt']['76']['inputs']['steps'] = 4
short['prompt']['46']['inputs']['filename_prefix'] = 'Anima_2.9B_Q5_4step_Speed_Test'
for n in short['extra_data']['extra_pnginfo']['workflow']['nodes']:
    if n['id'] == 76:
        n['widgets_values'][2] = 4
        n['title'] = '短测 · 4 步，只测流程与速度'
(work/'anima-q5-smoke.json').write_text(json.dumps(short,ensure_ascii=False),encoding='utf-8')
print('Prepared 4-step smoke and 28-step full workflow; active workflow unchanged until tested.')
