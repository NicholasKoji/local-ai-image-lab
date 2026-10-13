"""Opt-in sampler instrumentation; loaded only by the separate benchmark server."""
import collections
import importlib
import json
import os
from pathlib import Path
import time

import nodes
import torch


class LabProfileKSampler(nodes.KSampler):
    CATEGORY = "lab/benchmark"

    def sample(self, *args, **kwargs):
        output = Path(os.environ["LAB_RESULT_DIR"])
        output.mkdir(parents=True, exist_ok=True)
        enabled = os.environ.get("LAB_PROFILE", "0") == "1"
        gguf = importlib.import_module(nodes.NODE_CLASS_MAPPINGS["UnetLoaderGGUF"].__module__)
        ops = importlib.import_module(gguf.GGMLOps.__module__)
        original_dequant = ops.dequantize_tensor
        original_linear = torch.nn.functional.linear
        original_prepare = ops.GGMLLayer.cast_bias_weight
        original_attention = torch.nn.functional.scaled_dot_product_attention
        timings = collections.defaultdict(list)
        linear_shapes = collections.Counter()

        def measure(name, function):
            def wrapped(*a, **kw):
                before = torch.cuda.Event(enable_timing=True)
                after = torch.cuda.Event(enable_timing=True)
                before.record()
                result = function(*a, **kw)
                after.record()
                timings[name].append((before, after))
                if name == "linear" and a:
                    linear_shapes[(str(a[0].dtype), str(a[1].dtype), tuple(a[0].shape), tuple(a[1].shape))] += 1
                return result
            return wrapped
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        if enabled:
            ops.dequantize_tensor = measure("gguf_dequantize", original_dequant)
            ops.GGMLLayer.cast_bias_weight = measure("weight_prepare_including_dequantize", original_prepare)
            torch.nn.functional.linear = measure("linear", original_linear)
            torch.nn.functional.scaled_dot_product_attention = measure("attention", original_attention)
        try:
            result = super().sample(*args, **kwargs)
            torch.cuda.synchronize()
        finally:
            ops.dequantize_tensor = original_dequant
            torch.nn.functional.linear = original_linear
            ops.GGMLLayer.cast_bias_weight = original_prepare
            torch.nn.functional.scaled_dot_product_attention = original_attention
        report = {
            "profile_enabled": enabled,
            "sampler_wall_seconds_including_model_preparation": time.perf_counter() - start,
            "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
            "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20,
            "torch": torch.__version__, "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(),
            "note": "CUDA-event instrumentation: elapsed stream durations include host launch gaps; nested scopes overlap. Weight preparation includes dequantization, casts, copies and patches, not pure PCIe transfer time. Instrumented run is not an uninstrumented speed benchmark.",
        }
        if enabled:
            report["timing_method"] = "cuda_events"
            report["operators"] = [{"name":name, "count":len(pairs),
                "elapsed_ms":sum(a.elapsed_time(b) for a,b in pairs)} for name,pairs in timings.items()]
            report["linear_shapes_and_dtypes"] = [{"input_dtype":k[0], "weight_dtype":k[1],
                "input_shape":k[2], "weight_shape":k[3], "count":v} for k,v in linear_shapes.items()]
        (output / "sampler.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return result


NODE_CLASS_MAPPINGS = {"LabProfileKSampler": LabProfileKSampler}
