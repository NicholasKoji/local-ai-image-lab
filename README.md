# Local AI Image Lab

本机 ComfyUI 生图实验项目：整理 2026-10-13～14 会话中的工作流、适配节点、量化工具、测试图片与运行记录。

**当前入口是 Anima 2.9B Q5_0；Krea 2 Turbo Q2_K 保留作对比。** 这是针对 GTX 1660 Ti 6GB 的本机配置，不是包含模型的一键安装包。

## 快速使用

1. 双击 `scripts/launch/Start-ComfyUI.cmd`，打开 <http://127.0.0.1:8188>。
2. 将下面任一工作流 JSON 拖入 ComfyUI：
   - [Anima 2.9B Q5_0：4 步短测](workflows/anima/Anima_2.9B_Q5_6GB.json)
   - [Krea 2 Turbo Q2_K：2 步短测](workflows/krea2/Krea2_Turbo_Q2_K_6GB.json)
3. 修改正面提示词，保持 512×512、单张，点击运行。
4. 图片保存到 `D:\AI\ComfyUI\output`。不用时运行 `scripts/launch/Stop-ComfyUI.cmd`。

**默认步数仅用于测速，不代表正常画质。** Anima 28 步与 Krea 8 步版本放在 `workflows/full/`，量化版本的这两项长测尚未执行。

原有 `D:\AI\Start-ComfyUI.cmd` / `Stop-ComfyUI.cmd` 继续有效。项目启动脚本仍指向现有 `D:\AI` 安装，不会另装一份环境。

## 目录

```text
custom_nodes/                  本会话编写的 Krea 2 文本 GGUF 适配节点
scripts/
  launch/                      本机启动、停止脚本
  quantization/                Anima 2.9B → Q5_0 转换工具
  workflows/                   量化工作流构建脚本
  legacy/                      BF16 / FP8 历史工作流构建脚本
workflows/
  anima/                       当前 Anima UI 工作流
  krea2/                       当前 Krea UI 工作流
  api/                         ComfyUI /prompt 请求 JSON
  full/                        已准备、未长测的较高步数 UI 工作流
docs/
  environment.md               硬件、依赖、模型位置与来源
  guides/                      Q5 / Q2 使用说明原稿
  archive/                     早期 BF16 说明，仅作历史记录
examples/images/               三张本机实测图片，含工作流元数据
experiments/2026-10-13_14/      初始请求、运行结果、日志、模型头分析
references/workflows/          当时保存的官方工作流及节点参考
archive/
  session-scripts/              原始构建脚本，仅供追溯，不作为运行入口
  workflow-aliases/             会话中保留的旧文件名别名
generated/                     构建脚本输出，自动生成且不入 Git
```

## 已有实测，不重新跑图

| 配置 | 尺寸 / 步数 | 整次耗时 | 说明 |
| --- | --- | --- | --- |
| Anima 2.9B BF16，早期配置 | 512² / 28 | 26 分 28 秒 | 历史基线；测试受温度降频影响 |
| Anima 2.9B Q5_0 + FP16 计算 + CPU 文本 | 512² / 4 | 2 分 7 秒 | 采样约 25.21 秒/步；4 步画质粗糙 |
| Krea 2 Turbo Q2_K + Q4 文本 / CPU | 512² / 2 | 7 分 34 秒 | 采样约 5 分 45 秒；仍不适合快速交互 |

这些数据来自本会话历史运行，不是相同设置下仅改量化位数的严格对照。详情见 [实验记录](experiments/2026-10-13_14/README.md)。

## 工具使用

在项目目录运行以下命令，只生成 JSON，不提交生图任务、不改正在使用的工作流：

```powershell
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/workflows/build_anima_q5_workflow.py
& 'D:\AI\ComfyUI\.venv\Scripts\python.exe' scripts/workflows/build_krea_q2_workflow.py
```

输出分别在 `generated/anima/`、`generated/krea2/`。`scripts/legacy/` 仅用于重建历史 BF16 / FP8 配置，输出限定在 `generated/legacy/`。

`scripts/quantization/convert_anima_q5.py` 保留已使用的本机转换实现：源权重、目标权重与临时目录均在 `D:\AI`，输出已存在时会停止而不是覆盖。**现有 Q5 文件已经生成，无需再次转换。** 转换依赖现有 ComfyUI 虚拟环境，且需要原始 BF16 文件和额外临时空间。

`custom_nodes/krea2_text_gguf.py` 依赖已安装的 ComfyUI-GGUF 和 ComfyUI 原生 Krea 2 接口；仅支持文生图。当前运行环境中已安装同一节点，本次整理没有覆盖安装目录。

## 收纳范围与 Git 边界

- 原会话 `work/` 的 28 个文件、`outputs/` 的 12 个文件均按用途收纳；另收纳自编节点和两份 ComfyUI 日志快照。
- 原会话文件保留，以免已有下载链接失效；现有服务和工作流不迁移、不重启。
- `archive/session-scripts/` 保留原始构建代码；其中包含旧的绝对路径和写入行为，请使用 `scripts/` 下已整理的版本。
- 旧名称 `Anima_2.9B_6GB.json` / `Krea2_Turbo_6GB.json` 是最后状态的 Q5 / Q2 别名，**不是**最初 BF16 / FP8 工作流。真正历史请求在实验目录的 `baseline/`。
- 模型权重、ComfyUI 上游仓库、Python、虚拟环境、缓存都留在 `D:\AI`，不复制、不提交。模型头分析中的 1 MiB `.bin` 片段已收纳到本地项目，但同样被 Git 忽略；解析后的 JSON 已入库。
- 本仓库不自动下载模型、清理旧权重、修改驱动或改变电源/风扇设置。

第三方模型、软件及参考工作流的来源见 [环境与来源](docs/environment.md)，各自沿用原发布方的许可。
