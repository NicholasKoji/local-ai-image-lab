"""Krea 2 text-to-image adapter for Qwen3-VL-4B text-only GGUF.

Uses ComfyUI's native Krea tokenizer, 12 hidden-state taps and conditioning
format. The generic GGUF loader otherwise detects a text-only VL file as
plain Qwen3 and selects the wrong conditioning model. No vision weights or
dummy vision tensors are needed for text-to-image.
"""
import importlib
import logging

import torch
import folder_paths
import nodes
import comfy.sd
from comfy import model_management, sd1_clip
from comfy.supported_models_base import ClipTarget
from comfy.text_encoders import krea2, qwen3vl


class TextOnlyQwen3VL4B(qwen3vl.Qwen3VL):
    model_type = "qwen3vl_4b"

    def __init__(self, config_dict, dtype, device, operations):
        torch.nn.Module.__init__(self)
        config = qwen3vl.QWEN3VL_CONFIGS[self.model_type](**config_dict)
        self.num_layers = config.num_hidden_layers
        self.model = qwen3vl.Llama2_(config, device=device, dtype=dtype, ops=operations)
        self.dtype = dtype

    def preprocess_embed(self, embed, device):
        raise ValueError("This lightweight Krea loader supports text prompts only, not image embeddings.")


class TextOnlyKreaClip(sd1_clip.SDClipModel):
    def __init__(self, device="cpu", dtype=None, model_options={}):
        super().__init__(
            device=device, layer=krea2.KREA2_TAP_LAYERS, layer_idx=None,
            textmodel_json_config={}, dtype=dtype, special_tokens={"pad": 151643},
            layer_norm_hidden_state=False, model_class=TextOnlyQwen3VL4B,
            enable_attention_masks=True, return_attention_masks=True,
            model_options=model_options,
        )


class CheckedKreaTextModel(krea2.Krea2TEModel):
    def load_sd(self, sd):
        missing, unexpected = super().load_sd(sd)
        if missing or unexpected:
            raise ValueError(f"Qwen3-VL-4B text weight mismatch: missing={missing}, unexpected={unexpected}")
        logging.info("Krea2 text GGUF: all text weights loaded; native 12-layer conditioning enabled.")
        return missing, unexpected

    def encode_token_weights(self, token_weight_pairs, template_end=-1):
        out, pooled, extra = super().encode_token_weights(token_weight_pairs, template_end)
        if out.shape[-1] != 30720 or not torch.isfinite(out).all().item():
            raise ValueError(f"Invalid Krea2 conditioning: shape={tuple(out.shape)}; expected finite 12 x 2560 features.")
        logging.info("Krea2 Q4 text conditioning verified: shape=%s, finite=True", tuple(out.shape))
        return out, pooled, extra


class Krea2TextGGUFLoader:
    @classmethod
    def INPUT_TYPES(cls):
        names = [n for n in nodes.NODE_CLASS_MAPPINGS["CLIPLoaderGGUF"].get_filename_list()
                 if n.lower().endswith(".gguf")]
        return {"required": {"clip_name": (names,), "device": (["cpu", "cuda"],)}}

    RETURN_TYPES = ("CLIP",)
    FUNCTION = "load_clip"
    CATEGORY = "loaders/Krea2"
    DESCRIPTION = "Qwen3-VL-4B GGUF, native Krea2 12-layer text conditioning. Text-to-image only. Requires ComfyUI-GGUF."

    def load_clip(self, clip_name, device="cpu"):
        gguf_class = nodes.NODE_CLASS_MAPPINGS["CLIPLoaderGGUF"]
        gguf_nodes = importlib.import_module(gguf_class.__module__)
        path = folder_paths.get_full_path_or_raise("text_encoders", clip_name)
        sd = gguf_nodes.gguf_clip_loader(path)
        if tuple(sd["model.embed_tokens.weight"].shape) != (151936, 2560):
            raise ValueError("Select the Qwen3-VL-4B GGUF text encoder.")
        operations = gguf_nodes.GGMLOps
        if device == "cpu":
            # AVX2 CPUs handle float32 dequantization much better than float16.
            class CpuTextOps(gguf_nodes.GGMLOps):
                class Linear(gguf_nodes.GGMLOps.Linear):
                    dequant_dtype = torch.float32
            operations = CpuTextOps
        target = ClipTarget(krea2.Krea2Tokenizer, CheckedKreaTextModel)
        clip = comfy.sd.CLIP(
            target, embedding_directory=folder_paths.get_folder_paths("embeddings"),
            state_dict=[sd], disable_dynamic=True,
            model_options={
                "custom_operations": operations,
                "initial_device": model_management.text_encoder_offload_device(),
                "load_device": torch.device(device),
                "dtype": torch.float16,
                "qwen3vl_4b_class": TextOnlyKreaClip,
            },
        )
        clip.patcher = gguf_nodes.GGUFModelPatcher.clone(clip.patcher)
        return (clip,)


NODE_CLASS_MAPPINGS = {"Krea2TextGGUFLoader": Krea2TextGGUFLoader}
NODE_DISPLAY_NAME_MAPPINGS = {"Krea2TextGGUFLoader": "Krea 2 Text Encoder (GGUF, text only)"}
