# Anima 2.9B 后端性能对照报告

日期：2026-10-14（Asia/Shanghai） · 硬件：GTX 1660 Ti 6GB / i7-9750H / 16GB RAM

## 结论摘要

**本机优先选择 cu130 + 原生 INT8 ConvRot。** 相同 512×512 / 28 步条件下，整次请求 **3 分 57 秒**；cu126 Q5 为 **14 分 40 秒**，cu130 Q5 为 **17 分 19 秒**。INT8 本次快约 **3.72–4.39 倍**，28 步成图明显优于 4 步测速图。

- 这是每组一次实测，不是按短测线性外推；不含服务启动、组间降温时间。
- 三组热状态不完全一致且仍有降频，不能仅凭两份 Q5 的差距判断 CUDA 版本优劣。
- INT8 使用约 4.0 GiB 整卡显存峰值（含桌面），不是 PyTorch 分配器显示的约 169 MiB。
- 默认启动入口仍保留旧 cu126 环境；报告中的推荐不代表已切换日常环境。

阅读顺序：[28 步数据与成图](#28step-results) → [原始记录与复现](#records-and-reproduction)；后文保留 4 步短测、旧驱动瓶颈定位及环境准备过程。

<a id="28step-results"></a>

## 28 步正式对照

用户要求三组各跑一次 28 步，继续保持 512×512、相同提示词/负面提示词、seed 20261013、CFG 4、Euler / sgm_uniform、FP16 计算、CPU 文本编码与 CPU VAE。驱动三组均为 616.92，无计时插桩。实际请求中除主模型加载节点和输出文件前缀外，其余节点相同；请求与 PNG 工作流元数据均设置为 28 步。

[作者模型卡](https://huggingface.co/Gazingstars123/Anima-2.9B#generation-recommendation)推荐 28–50 步；本轮选其步数下限，但保持之前 512×512 小图以比较性能，并未同时切换作者推荐的更大分辨率。三组各一次独立服务首张请求，整次耗时不包含启动服务和组间降温。

| 配置 | 整次请求 | 采样节点，含模型准备 | 设备显存峰值，含桌面 | 启动前温度 |
| --- | ---: | ---: | ---: | ---: |
| cu126 + Q5_0 | **879.89 s / 14 分 40 秒** | 851.21 s | 2882 MiB | 68°C |
| cu130 + Q5_0 | **1038.56 s / 17 分 19 秒** | 1009.63 s | 2834 MiB | 73°C |
| cu130 + 原生 INT8 ConvRot | **236.83 s / 3 分 57 秒** | 202.69 s | 4111 MiB | 74°C |

INT8 整次耗时分别为旧环境 Q5 的约 1/3.72、新环境 Q5 的约 1/4.39；相对新环境 Q5 减少约 77.2% 耗时。INT8 稳态进度多步约 7.0–7.2 s/step，不能使用初始化计时调整后的末尾累计均值作为真实稳态速度。Q5 cu126 最终平均约 30.13 s/step、后段约 33；Q5 cu130 平均约 35.77 s/step、后段约 35–37。

### 热状态与比较限制

每组前尝试等待温度 ≤70°C 且利用率 ≤15%，最长约 5 分钟。首组达到条件；第二、三组分别等待约 303 秒后仍为 73°C / 74°C，按预设等待上限继续，详见 `28step-cooldown.csv`。本轮不是严格等温、随机次序、多次重复的 CUDA 内核实验。

- GPU 利用率 ≥50% 的样本，cu126 Q5 共 383 次，其中 355 次软件热降频；忙时 75–88°C。显存频率 6000 MHz 有 85 次、810 MHz 有 298 次，解释了开始较快、后段变慢的现象。
- cu130 Q5 忙时 454 个样本均有软件热降频，76–89°C，显存频率全为 810 MHz。
- cu130 INT8 忙时 90 个样本均有软件热降频，78–88°C，显存频率全为 810 MHz。

因此不能仅凭 17:19 对 14:40 宣称 cu130 本身导致 Q5 变慢；温度、频率、测试顺序有影响。但 INT8 在相同低显存频率、持续热降频的这次真实使用状态下，依然明显领先 Q5。

### 画质与落地结论

已查看三张实际 PNG：28 步比 4 步的过亮、粗糙纹理明显改善；两张 Q5 视觉非常接近。INT8 同样形成清晰的橘猫、窗框、花盆及庭院构图，未见明显崩坏；条纹、花叶及局部构图有差别，不是逐像素一致。只凭一个提示词/种子，不把这个结果外推为所有题材质量完全相同。

**本机优先使用 cu130 + INT8 ConvRot：当前 512×512 / 28 步约 4 分钟，Q5 约 15–17 分钟。** 这是本次散热状态下的结果，不是硬件最佳上限，也不代表更大分辨率时间。

### 28 步图片对照

| cu126 + Q5 · 14:40 | cu130 + Q5 · 17:19 | cu130 + INT8 · 3:57 |
| --- | --- | --- |
| ![cu126 Q5 28 步](../../examples/images/Anima_2.9B_new-driver-cu126-q5-28step.png) | ![cu130 Q5 28 步](../../examples/images/Anima_2.9B_new-cu130-q5-28step.png) | ![cu130 INT8 28 步](../../examples/images/Anima_2.9B_new-cu130-int8-28step.png) |

三份实际命令、请求、历史、状态、采样计时、GPU CSV、日志在下方索引的 `*-28step/` 子目录。三次生成均成功，外层进程退出码均为 0；测试完成时 8188 / 8189 均无监听服务。

测试工具只新增 `--steps`，默认仍为 4，同时更新实际请求及 PNG 工作流元数据；长测传入 `--steps 28 --timeout 1800`，92°C 中断规则保持不变。参数支持已通过实际 28 步任务验证；历史 4 步默认值保留。

旧模型、环境与日常启动入口保留，未自动切换或删除模型；报告发布不改变运行配置。

<a id="records-and-reproduction"></a>

## 原始记录与复现

| 阶段 | cu126 + Q5 | cu130 + Q5 | cu130 + INT8 |
| --- | --- | --- | --- |
| 28 步 | [原始记录](new-driver-cu126-q5-28step/) | [原始记录](new-cu130-q5-28step/) | [原始记录](new-cu130-int8-28step/) |
| 4 步 | [原始记录](new-driver-cu126-q5/) | [原始记录](new-cu130-q5/) | [原始记录](new-cu130-int8/) |

每组保留 `request.json`、`command.json`、`history.json`、`status.json`、`sampler.json`、`gpu.csv`、`server.log`。其中 `command.json` 是 ComfyUI 服务启动命令；下方是外层测试命令。发布的 `server.log` 仅去除终端色码、行尾空格并整理换行，保留消息和数值；未经排版的原文件仍在本机 `generated/benchmark/<label>/server.log`。

- [28 步组间降温记录](28step-cooldown.csv)
- [旧驱动 CUDA 事件诊断](old-cu126-q5-events/)
- [cu126 依赖快照](environment/requirements-cu126.txt) / [cu130 依赖快照](environment/requirements-cu130.txt)
- [测试工具说明](../../scripts/benchmark/README.md)

以下为复现示例，不需要为了阅读/发布报告重新运行。执行目录为项目根目录；服务共用 `D:\AI\ComfyUI`，端口 8189。每次必须换一个未使用的 label，默认只监听本机；请串行执行并记录组间热状态。本次降温等待由外层调度完成，`run_anima.py` 本身不负责组间等待。

```powershell
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label repro-cu126-q5-28step --steps 28 --timeout 1800
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label repro-cu130-q5-28step --python 'D:\AI\environments\anima-cu130\Scripts\python.exe' --steps 28 --timeout 1800
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label repro-cu130-int8-28step --python 'D:\AI\environments\anima-cu130\Scripts\python.exe' --int8 --steps 28 --timeout 1800
```

PNG 内嵌的是带 `LabProfileKSampler` 的测试工作流；日常 8188 服务未加载这个实验节点，因此测试图片不等于可直接拖入日常环境使用的一键工作流。这里只发布实验产物，不自动替换日常入口。

## 4 步短测（历史对照）

全部关闭 CUDA 事件插桩，固定 512×512、4 步、CFG 4、seed 20261013、Euler / sgm_uniform、FP16 计算、CPU 文本编码与 CPU VAE。同一 ComfyUI 源码与提示词，每组各一次独立服务冷请求；启动服务所需时间不计入请求耗时。不是常驻模型的热缓存速度测试。

| 环境与主模型 | 整次请求 | 采样节点，含模型准备 | 设备显存峰值，含桌面 | GPU 忙时温度 |
| --- | ---: | ---: | ---: | --- |
| cu126 + Q5_0 | 161.80 s | 134.06 s | 2854 MiB | 83–87°C |
| cu130 + Q5_0 | 166.63 s | 141.61 s | 2797 MiB | 84–88°C |
| cu130 + 原生 INT8 ConvRot | **54.51 s** | **30.64 s** | 4064 MiB | 81–83°C |

按整次请求，INT8 比 cu130 Q5 快约 **3.06 倍**，耗时减少约 **67.3%**；采样节点含准备时间约快 4.62 倍。换 CUDA wheel 本身没有在此次 Q5 短测中带来提速。

GPU 利用率 ≥50% 的样本：三组分别为 58 / 62 / 13 次，均记录 SW Thermal Slowdown Active，显存频率均为 810 MHz。INT8 温度更低，且量化、加载器与动态显存路径一并变化，因此这是实际可用配置比较，不是严格隔离 INT8 内核收益的实验，也不代表冷机/正常散热时的性能上限。

INT8 日志确认原生 `int8_tensorwise` 可用，并使用 mixed precision operations / dynamic VRAM loading，没有改成 BF16 大模型。其 PyTorch 分配器统计仅约 169 MiB，未涵盖全部动态显存分配；显存比较应使用本表的 NVIDIA 整卡采样值，不能把 169 MiB 当作总占用。

INT8 的进度条在模型初始化后出现计时基准调整，末尾显示的 3.61 s/it 不作为稳定每步速度。以已同步的采样节点 30.64 s 和端到端 54.51 s 为准。各 `sampler.json` 的通用 note 仍沿用工具的插桩说明，但三份记录 `profile_enabled=false`，本轮没有算子计时插桩。

### 4 步成图及使用边界

三组均成功保存 512×512 PNG，已直接查看。两组 Q5 视觉接近；INT8 的猫朝向、造型发生变化。三组都存在低步数的过亮和密集粗糙纹理，4 步只证明通路及短测速度，不证明正常步数画质。这是此前 4 步阶段的结论；之后已按用户要求完成以下 28 步实测。

图片：[cu126 Q5](../../examples/images/Anima_2.9B_new-driver-cu126-q5_4step.png)、[cu130 Q5](../../examples/images/Anima_2.9B_new-cu130-q5_4step.png)、[cu130 INT8](../../examples/images/Anima_2.9B_new-cu130-int8_4step.png)。每组子目录保留实际请求、完整命令、ComfyUI 历史、状态、采样计时、NVIDIA 采样与服务日志；原始服务输出仍在 Git 忽略的 `generated/benchmark/`。

**4 步阶段建议优先用 cu130 + INT8 继续测试；现已完成下方 28 步对照。** Q5 权重及旧环境保持原样；日常 `D:\AI\Start-ComfyUI.cmd` 仍指向旧环境，未自动切换。独立测试服务在各组完成后退出；测试未调整风扇、电源或驱动设置。

来源：[官方驱动页](https://www.nvidia.com/en-us/drivers/details/278456/)、[NVIDIA 显示驱动安装参数](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/windows.html)、[PyTorch 同版本 cu130 构建](https://pytorch.org/get-started/previous-versions/)、[原作者 INT8 权重](https://huggingface.co/Gazingstars123/Anima-2.9B/blob/main/Anima-2.9B-preview-v1_int8_convrot.safetensors)。


## 旧驱动瓶颈分析（历史诊断）

- 驱动 546.33，PyTorch 2.12.1+cu126，原有 Q5_0 / FP16、CPU 文本及 VAE。
- 请求固定为 512×512、4 步、CFG 4、seed 20261013、Euler / sgm_uniform。
- Prompt ID：`9a518f6f-407b-492e-b1c0-7e877d4ee2f7`；成功出图。
- 含模型准备的采样节点约 **139.14 秒**；客户端记录完整请求约 **167.61 秒**。这是带计时的诊断运行，不替换历史无计时的 127.10 秒基准。
- CUDA 事件区间：线性层 **97.37 秒**；GGUF 反量化 **25.58 秒**；注意力 **5.88 秒**。权重准备（含反量化）25.59 秒，类别嵌套不能求和，也不是纯 PCIe 传输时间。
- 记录到的线性层输入和权重均为 **FP16**，没有在这些线性层中发现意外 FP32 计算。
- 主模型再次完整进入显存；PyTorch 峰值已分配显存约 **2239.35 MiB**。
- NVIDIA 采样 77 次，温度 **81～88°C**；63 次记录软件热降频 Active。显存频率为 810MHz（63 次）或空闲 405MHz（14 次），没有观测到原先一次 Q5 测试中的 6000MHz。

**阶段结论：反量化有成本，但本次最大计时区间是线性层计算；实测有明确热降频。仅凭 cu130 警告或模型文件大小解释全部耗时不成立。** CUDA 事件区间还包括主机发射间隙，不应当成独占 GPU 内核分析。

首次独立服务因缺少用户目录而退出，已修正；一次完整 PyTorch profiler 在完成 4 步后汇总阶段遇到客户端等待超时，未取得有效 profiler 汇总，因而没有用于上述结论。随后改用轻量 CUDA 事件计时并成功完成；失败运行仅保留在被 Git 忽略的 `generated/benchmark/`。

## 驱动安装及环境就绪

作者发布的 INT8 ConvRot 权重已经下载到原模型目录：3,082,486,758 字节，头部含 2208 个张量，其中 640 个 I8 权重。量化配置为 `int8_tensorwise`、`convrot=true`、groupsize 256，不是 GGUF 文件。

独立环境 `D:\AI\environments\anima-cu130` 已完成安装及依赖检查，PyTorch / torchvision 为 2.12.1+cu130 / 0.27.1+cu130。87 个安装包与旧环境相比，仅这两个 CUDA wheel 构建不同，其余版本一致；清单在 `environment/`。

NVIDIA Studio 616.92 官方笔记本安装包支持 GTX 1660 Ti Notebook / Windows 10。最初的管理员启动命令被执行环境策略拦截，安装脚本及旧驱动导出均未执行。随后用户手动安装，首次因 C 盘空间不足失败：`C:\Windows\INF\setupapi.dev.log` 明确记录 Error 112 / FAILURE(0x00000070)，失败发生于复制到 DriverStore。关闭失败安装器后，C 盘从约 4.29 GiB 恢复至 7.94 GiB；临时解压目录随安装器退出而删除，没有手动清理系统 DriverStore。

用户改用 D 盘现有解压目录再次安装并报告成功。本次已实测 `nvidia-smi` 驱动 616.92，C 盘约 5.51 GiB 可用。cu130 GPU 冒烟测试成功：GTX 1660 Ti、计算能力 (7, 5)、32×32 FP16 全 1 矩阵相乘得到 32.0。没有触发自动重启，也没有声称保留了未曾导出的旧驱动备份。
