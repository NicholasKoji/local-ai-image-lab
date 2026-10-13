import copy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
work = root / 'generated/legacy/anima'
work.mkdir(parents=True, exist_ok=True)
out = work
official = json.loads((root / 'references/workflows/anima-official.json').read_text(encoding='utf-8'))
core = {n['id']: copy.deepcopy(n) for n in official['definitions']['subgraphs'][0]['nodes']}
ids = [78, 71, 72, 77, 75, 74, 76, 73]
nodes = [core[i] for i in ids]
positive = ('masterpiece, best quality, anime illustration, no humans, a fluffy orange tabby cat '
            'sitting on a wooden windowsill inside a cozy countryside cottage, looking outside, '
            'one small blue ceramic flowerpot beside the cat, soft morning sunlight through the window, '
            'a peaceful green garden in the background, warm colors, clean lineart, soft cel shading, '
            'detailed fur, charming storybook atmosphere, medium shot')
negative = 'worst quality, low quality, blurry, jpeg artifacts, text, watermark, logo, deformed, extra limbs'
titles = {78:'主模型 · Anima 2.9B', 71:'文本编码器 · 保持默认', 72:'VAE · 共用已有文件',
          77:'① 正面提示词 · 描述你想画的内容', 75:'负面提示词 · 不想出现的内容',
          74:'② 尺寸 · 先用 512 × 512 / 单张', 76:'③ 采样 · 28 步 / CFG 4', 73:'分块解码 · 节省内存'}
positions = {78:[20,40],71:[20,230],72:[20,420],77:[440,40],75:[440,365],74:[440,590],76:[950,40],73:[950,490]}
for order, n in enumerate(nodes):
    n['inputs'] = [i for i in n.get('inputs',[]) if not i.get('widget')]
    for i in n.get('inputs',[]): i['link'] = None
    for o in n.get('outputs',[]): o['links'] = []
    n.update(title=titles[n['id']], pos=positions[n['id']], order=order,
             properties={'Node name for S&R':n['type'], 'cnr_id':'comfy-core'})
    if n['id'] in (78,71,72): n['size'] = [380,165]
core[78]['widgets_values'] = ['Anima-2.9B-preview-v1.safetensors','default']
core[71]['widgets_values'] = ['qwen_3_06b_base.safetensors','stable_diffusion','default']
core[72]['widgets_values'] = ['qwen_image_vae.safetensors']
core[77]['widgets_values'] = [positive]
core[77]['size'] = [460,270]
core[75]['widgets_values'] = [negative]
core[75]['size'] = [460,170]
core[74]['widgets_values'] = [512,512,1]
core[74]['size'] = [360,140]
core[76]['widgets_values'] = [20261013,'randomize',28,4.0,'euler','sgm_uniform',1.0]
core[76]['size'] = [350,390]
core[73]['type'] = 'VAEDecodeTiled'
core[73]['properties']['Node name for S&R'] = 'VAEDecodeTiled'
core[73]['widgets_values'] = [256,64,64,8]
core[73]['size'] = [350,220]
save = copy.deepcopy(next(n for n in official['nodes'] if n['type']=='SaveImage'))
save.update(id=46, title='④ 生成结果 · 自动保存到 output', pos=[1350,40], size=[500,560], order=8)
save['widgets_values'] = ['Anima_2.9B']
save['inputs'][0]['link'] = None
nodes.append(save)
allnodes = {n['id']:n for n in nodes}
edges = [(71,0,77,0,'CLIP'), (71,0,75,0,'CLIP'), (78,0,76,0,'MODEL'),
         (77,0,76,1,'CONDITIONING'), (75,0,76,2,'CONDITIONING'), (74,0,76,3,'LATENT'),
         (76,0,73,0,'LATENT'), (72,0,73,1,'VAE'), (73,0,46,0,'IMAGE')]
links = []
for lid,(src,ss,dst,ds,kind) in enumerate(edges,1):
    links.append([lid,src,ss,dst,ds,kind])
    allnodes[src]['outputs'][ss]['links'].append(lid)
    allnodes[dst]['inputs'][ds]['link'] = lid
workflow = {'last_node_id':78,'last_link_id':len(links),'nodes':nodes,'links':links,
            'groups':[],'config':{},'extra':{'ds':{'scale':0.65,'offset':[80,80]}},'version':0.4}
for target in [out/'Anima_2.9B_6GB.json']:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(workflow,ensure_ascii=False,indent=2),encoding='utf-8')
api = {
 '78':{'class_type':'UNETLoader','inputs':{'unet_name':'Anima-2.9B-preview-v1.safetensors','weight_dtype':'default'}},
 '71':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen_3_06b_base.safetensors','type':'stable_diffusion','device':'default'}},
 '72':{'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
 '77':{'class_type':'CLIPTextEncode','inputs':{'clip':['71',0],'text':positive}},
 '75':{'class_type':'CLIPTextEncode','inputs':{'clip':['71',0],'text':negative}},
 '74':{'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},
 '76':{'class_type':'KSampler','inputs':{'model':['78',0],'positive':['77',0],'negative':['75',0],
       'latent_image':['74',0],'seed':20261013,'steps':28,'cfg':4.0,'sampler_name':'euler','scheduler':'sgm_uniform','denoise':1.0}},
 '73':{'class_type':'VAEDecodeTiled','inputs':{'samples':['76',0],'vae':['72',0],
       'tile_size':256,'overlap':64,'temporal_size':64,'temporal_overlap':8}},
 '46':{'class_type':'SaveImage','inputs':{'images':['73',0],'filename_prefix':'Anima_2.9B_First_Test'}}}
(work/'anima-prompt.json').write_text(json.dumps({'prompt':api,'extra_data':{'extra_pnginfo':{'workflow':workflow}}},ensure_ascii=False),encoding='utf-8')
print('Prepared Anima_2.9B_6GB.json: 512x512, 28 steps, CFG 4, euler/sgm_uniform; no custom nodes.')
