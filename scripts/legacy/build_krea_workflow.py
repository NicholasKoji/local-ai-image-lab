import copy
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = root / 'generated/legacy/krea2'
out.mkdir(parents=True, exist_ok=True)
official = json.loads((root / 'references/workflows/krea2-official.json').read_text(encoding='utf-8-sig'))
core = {n['id']: copy.deepcopy(n) for n in official['definitions']['subgraphs'][0]['nodes']}
ids = [10, 11, 12, 6, 13, 5, 3, 8]
nodes = [core[i] for i in ids]
prompt = 'A photo of an orange tabby cat sitting on a wooden windowsill, soft morning sunlight, green plants outside the window, natural colors, detailed fur, cozy atmosphere.'
titles = {10:'主模型 · Krea 2 Turbo',11:'文本编码器 · 保持默认',12:'VAE · 保持默认',6:'① 在这里填写画面描述',13:'负面条件 · 无需修改',5:'② 图片尺寸 · 先从 512 开始',3:'③ 采样 · 8 步 / CFG 1',8:'分块解码 · 节省内存'}
positions = {10:[20,40],11:[20,220],12:[20,410],6:[450,40],13:[450,390],5:[450,510],3:[980,40],8:[980,490]}
for order,n in enumerate(nodes):
    n['inputs']=[i for i in n.get('inputs',[]) if not i.get('widget')]
    for i in n.get('inputs',[]): i['link']=None
    for o in n.get('outputs',[]): o['links']=[]
    n['title']=titles[n['id']]
    n['pos']=positions[n['id']]
    n['order']=order
    n['size']=[390,180] if n['id'] in [10,11,12] else n['size']
    n['properties']={'Node name for S&R':n['type'],'cnr_id':'comfy-core'}
core[6]['widgets_values']=[prompt]
core[6]['size']=[450,300]
core[5]['widgets_values']=[512,512,1]
core[3]['widgets_values']=[20261013,'randomize',8,1.0,'euler','simple',1.0]
core[3]['size']=[340,380]
core[8]['type']='VAEDecodeTiled'
core[8]['properties']['Node name for S&R']='VAEDecodeTiled'
core[8]['widgets_values']=[256,64,64,8]
core[8]['size']=[340,220]
save=copy.deepcopy(next(n for n in official['nodes'] if n['type']=='SaveImage'))
save.update(id=29,pos=[1380,40],size=[500,560],title='④ 生成结果 · 自动保存到 output',order=8)
save['widgets_values']=['Krea2_Turbo']
save['inputs'][0]['link']=None
nodes.append(save)
allnodes={n['id']:n for n in nodes}
edges=[(11,0,6,0,'CLIP'),(10,0,3,0,'MODEL'),(6,0,3,1,'CONDITIONING'),(13,0,3,2,'CONDITIONING'),(5,0,3,3,'LATENT'),(3,0,8,0,'LATENT'),(12,0,8,1,'VAE'),(6,0,13,0,'CONDITIONING'),(8,0,29,0,'IMAGE')]
links=[]
for lid,(src,ss,dst,ds,kind) in enumerate(edges,1):
    links.append([lid,src,ss,dst,ds,kind])
    allnodes[src]['outputs'][ss]['links'].append(lid)
    allnodes[dst]['inputs'][ds]['link']=lid
workflow={'last_node_id':29,'last_link_id':len(links),'nodes':nodes,'links':links,'groups':[], 'config':{},'extra':{'ds':{'scale':0.65,'offset':[80,80]}},'version':0.4}
target=out/'Krea2_Turbo_6GB.json'
target.parent.mkdir(parents=True,exist_ok=True)
for path in [target]:
    path.write_text(json.dumps(workflow,ensure_ascii=False,indent=2),encoding='utf-8')
api={
 '10':{'class_type':'UNETLoader','inputs':{'unet_name':'krea2_turbo_fp8_scaled.safetensors','weight_dtype':'default'}},
 '11':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_4b_fp8_scaled.safetensors','type':'krea2','device':'default'}},
 '12':{'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
 '6':{'class_type':'CLIPTextEncode','inputs':{'clip':['11',0],'text':prompt}},
 '13':{'class_type':'ConditioningZeroOut','inputs':{'conditioning':['6',0]}},
 '5':{'class_type':'EmptyLatentImage','inputs':{'width':512,'height':512,'batch_size':1}},
 '3':{'class_type':'KSampler','inputs':{'model':['10',0],'positive':['6',0],'negative':['13',0],'latent_image':['5',0],'seed':20261013,'steps':8,'cfg':1.0,'sampler_name':'euler','scheduler':'simple','denoise':1.0}},
 '8':{'class_type':'VAEDecodeTiled','inputs':{'samples':['3',0],'vae':['12',0],'tile_size':256,'overlap':64,'temporal_size':64,'temporal_overlap':8}},
 '29':{'class_type':'SaveImage','inputs':{'images':['8',0],'filename_prefix':'Krea2_First_Test'}}}
(out/'krea2-prompt.json').write_text(json.dumps({'prompt':api,'extra_data':{'extra_pnginfo':{'workflow':workflow}}},ensure_ascii=False),encoding='utf-8')
print('Prepared beginner workflow:',target)
