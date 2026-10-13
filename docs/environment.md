# 本机环境与模型来源

这是 2026-10-13～14 生图会话的环境记录，不是持续更新的依赖锁文件。

## 已有运行环境

| 项目 | 会话中使用的配置 |
| --- | --- |
| CPU / 内存 | Intel i7-9750H / 16GB |
| GPU / 驱动 | NVIDIA GTX 1660 Ti 6GB / 546.33 |
| ComfyUI | `D:\AI\ComfyUI`，v0.39.0 |
| Python | 3.12.11，`D:\AI\ComfyUI\.venv\Scripts\python.exe` |
| PyTorch / torchvision | 2.12.1+cu126 / 0.27.1+cu126 |
| ComfyUI 前端 | 1.53.10 |
| ComfyUI-GGUF | city96 上游，提交 `6ea2651` |
| gguf / protobuf | 0.19.0 / 7.36.2 |
| 缓存 / 临时文件 / 日志 | `D:\AI\cache` / `D:\AI\temp` / `D:\AI\logs` |

启动参数以 `scripts/launch/start-comfy.ps1` 为准：仅监听 `127.0.0.1:8188`，FP16 主模型、CPU VAE、禁用 pinned memory、预留 0.8GB 显存、不显示采样预览；保留动态显存机制。原始 `first-run-crash.log` 记录的是更早的 PyTorch 2.7.1 配置，不代表最后运行环境。

## 当前工作流所需权重

以下路径相对于 `D:\AI\ComfyUI\models`。权重不包含在 Git 仓库中。

| 相对路径 | 字节数 | 用途 |
| --- | ---: | --- |
| `diffusion_models/Anima-2.9B-preview-v1-Q5_0.gguf` | 2,009,066,560 | Anima 主模型，本机从 BF16 转换 |
| `text_encoders/qwen_3_06b_base.safetensors` | 1,192,135,096 | Anima CPU 文本编码器 |
| `diffusion_models/krea2_turbo-Q2_K.gguf` | 4,889,589,024 | Krea 主模型 |
| `text_encoders/Qwen3VL-4B-Instruct-Q4_K_M.gguf` | 2,497,281,664 | Krea CPU 文本编码器 |
| `vae/qwen_image_vae.safetensors` | 253,806,246 | 两套工作流共用 VAE |

Anima 量化是 **Q5_0，不是 Q5_K_M，也不是普通 Anima 2B**。928 个张量，2,921,547,563 参数；707 个 Q5_0、220 个 F32、1 个 F16。没有对所有张量强行量化成 5 bit。

## 历史空间清理状态

截至上轮生图结束：旧 Krea FP8 主模型已删除；旧 Anima BF16 主模型和旧 Krea FP8 文本编码器仍保留，因为当时删除命令被执行环境拦截。**本次只整理项目，没有再次删除权重。** 旧说明中剩余磁盘空间是当时的快照，不能作为当前实时值。

## 来源

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)
- [GGUF Python 量化实现](https://github.com/ggml-org/llama.cpp/tree/master/gguf-py)
- [Anima 2.9B 原模型](https://huggingface.co/Gazingstars123/Anima-2.9B)
- [Anima 官方教程](https://docs.comfy.org/tutorials/image/anima/anima)
- [Krea 2 Turbo GGUF](https://huggingface.co/vantagewithai/Krea-2-Turbo-GGUF)
- [Qwen3-VL-4B GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF)
- [Krea 2 官方教程](https://docs.comfy.org/tutorials/image/krea/krea-2)

参考 JSON 是会话当时保存的副本，不会自动跟随上游更新。模型使用条款请以各发布页为准。
