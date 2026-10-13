"""Stream the existing Anima 2.9B checkpoint into standard Q5_0 GGUF."""
import collections
import os
from pathlib import Path
import time

os.environ['TMPDIR'] = os.environ['TEMP'] = os.environ['TMP'] = r'D:\AI\temp'
import gguf
import numpy as np
import torch
from safetensors import safe_open

torch.set_num_threads(6)
source = Path(r'D:\AI\ComfyUI\models\diffusion_models\Anima-2.9B-preview-v1.safetensors')
target = source.with_name('Anima-2.9B-preview-v1-Q5_0.gguf')
part = target.with_suffix('.gguf.part')
if target.exists() or part.exists():
    raise FileExistsError('Output already exists; inspect it instead of overwriting.')
start = time.monotonic()
writer = gguf.GGUFWriter(path=None, arch='cosmos', use_temp_file=True)
writer.add_quantization_version(gguf.GGML_QUANT_VERSION)
writer.add_file_type(gguf.LlamaFileType.MOSTLY_Q5_0)
writer.add_name('Anima-2.9B-preview-v1 Q5_0')
shapes = {}
counts = collections.Counter()
with safe_open(str(source), framework='pt', device='cpu') as f:
    keys = f.keys()
    for i, key in enumerate(keys):
        name = key.removeprefix('net.')
        if '_extra_state' in name or 'accum_' in name:
            continue
        tensor = f.get_tensor(key)
        data = tensor.float().numpy()
        shapes[name] = tuple(data.shape)
        if data.ndim >= 2 and data.shape[-1] % 32 == 0 and data.size > 1024 and 'pos_embedder' not in name:
            qtype = gguf.GGMLQuantizationType.Q5_0
        elif data.ndim == 1 or data.size <= 1024 or 'pos_embedder' in name:
            qtype = gguf.GGMLQuantizationType.F32
        else:
            qtype = gguf.GGMLQuantizationType.F16
        packed = gguf.quants.quantize(data, qtype)
        writer.add_tensor(name, packed, raw_dtype=qtype)
        counts[qtype.name] += 1
        if i == 0:
            restored = gguf.quants.dequantize(packed, qtype)
            assert restored.shape == data.shape
            assert np.isfinite(restored).all()
            relative_error = np.linalg.norm(restored - data) / np.linalg.norm(data)
            print(f'First tensor: {name}, shape={data.shape}, Q5 relative L2 error={relative_error:.6f}', flush=True)
        del tensor, data, packed
        if (i + 1) % 100 == 0:
            print(f'Quantized {i+1}/{len(keys)} tensors; {time.monotonic()-start:.1f}s', flush=True)
writer.write_header_to_file(path=part)
writer.write_kv_data_to_file()
writer.write_tensors_to_file(progress=False)
writer.close()
reader = gguf.GGUFReader(part)
actual = {t.name: tuple(int(x) for x in reversed(t.shape)) for t in reader.tensors}
assert actual == shapes, 'GGUF logical shapes differ from original checkpoint'
parameters = sum(int(np.prod(s)) for s in shapes.values())
assert parameters == 2921547563, parameters
del reader
part.rename(target)
print(f'COMPLETE path={target} bytes={target.stat().st_size} parameters={parameters} qtypes={dict(counts)} elapsed={time.monotonic()-start:.2f}s', flush=True)
