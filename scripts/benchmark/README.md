# Anima 后端对照工具

默认使用仓库原有 Anima 请求：512×512、4 步（可用 `--steps` 调整）、CFG 4、seed 20261013、Euler / sgm_uniform、CPU 文本编码与 CPU VAE。独立服务监听 8189，共用已有模型和 ComfyUI 源码，用户目录、图片与日志写入 `generated/benchmark/<label>/`。不会修改 8188 的工作流。

```powershell
# 当前环境：CUDA 事件计时，仅用于瓶颈定位
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label q5-profile --profile

# 准备相同版本的 cu130 环境，旧环境保留
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/benchmark/prepare_cu130.ps1

# 新驱动生效后，先测旧环境，隔离驱动变化的影响
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label new-driver-cu126-q5

# 新环境 Q5：除 CUDA wheel 外保持依赖版本一致
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label new-cu130-q5 --python 'D:\AI\environments\anima-cu130\Scripts\python.exe'

# 新环境 INT8：改原生 UNETLoader，保持同一 FP16 计算节点
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/benchmark/run_anima.py --label new-cu130-int8 --int8 --python 'D:\AI\environments\anima-cu130\Scripts\python.exe'
```

每次使用新的 label，避免覆盖旧记录。默认任务超时 600 秒，GPU 温度达到 92°C 会中断本次测试；它不是风扇或功率控制器。测试完成/失败后只关闭自己启动的服务进程树，不停止常用 ComfyUI 服务。

`--profile` 使用 CUDA 事件测量反量化、权重准备、线性层和注意力的流内区间。事件区间包含主机提交间隙，且权重准备包含反量化，不可把所有类别直接相加。它不是 CUPTI 的独占内核时间；权重准备减去反量化也不是纯 PCIe 传输时间。正式速度对比不启用此开关。

同一测试内保留 `request.json`、`command.json`、`history.json`、`status.json`、`sampler.json`、`gpu.csv`、`server.log` 与图片。检查采样速度时同时看 thermal throttle、核心/显存频率与加载情况，不将不同热状态的运行当作严格 A/B。

## 驱动安装

`install_nvidia_display.ps1` 需要用户单独批准 Windows 管理员权限。它验证 NVIDIA 签名，先导出当前驱动，再按 NVIDIA 官方参数执行显示驱动单独安装；不安装 NVIDIA App，不使用清洁安装，不自动重启。

驱动安装目录为 `D:\AI\drivers\616.92`。旧 Python 环境始终保留；恢复原 Python 路径即可回到旧软件栈。驱动是系统共享组件，独立虚拟环境不隔离驱动；仅当此脚本成功执行时，旧驱动导出与状态才会写入该目录的 `installation/`。**本次脚本未实际执行，驱动由用户手动安装；没有本脚本导出的旧驱动备份。** 脚本作为未完成实装验证的辅助工具保留，不作为本次安装成功的证据。


## 指定步数

`--steps` 默认 4；28 步长测使用 `--steps 28 --timeout 1800`。它同时更新 API 请求和 PNG 内嵌 UI 工作流的采样步数，固定种子，其余参数不变。每组使用独立 label，例如 `new-cu130-int8-28step`。本次三组实际运行已记录在 `experiments/2026-10-14_backend_ab/`，不必为文档验证再次生成。
