from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from memory_eval.adapters.membox_adapter import MemboxAdapter, MemboxAdapterConfig
from memory_eval.adapters.o_mem_adapter import OMemAdapter, OMemAdapterConfig


AdapterBuilder = Callable[[Dict[str, Any]], Any]


def _redact_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("api_key", "apikey", "token", "secret", "password")):
                out[key] = "***REDACTED***" if value else value
            else:
                out[key] = _redact_secrets(value)
        return out
    if isinstance(obj, list):
        return [_redact_secrets(x) for x in obj]
    return obj


def _build_membox(raw: Dict[str, Any]) -> MemboxAdapter:
    cfg = MemboxAdapterConfig(**raw)
    return MemboxAdapter(config=cfg)


def _build_membox_stable_eval(raw: Dict[str, Any]) -> MemboxAdapter:
    cfg_raw = dict(raw)
    if not cfg_raw.get("membox_root"):
        cfg_raw["membox_root"] = str(Path(__file__).resolve().parents[3] / "system" / "Membox_stableEval")
    cfg = MemboxAdapterConfig(**cfg_raw)
    return MemboxAdapter(config=cfg)


def _build_o_mem(raw: Dict[str, Any]) -> OMemAdapter:
    cfg = OMemAdapterConfig(**raw)
    return OMemAdapter(config=cfg)


def _build_o_mem_stable_eval(raw: Dict[str, Any]) -> OMemAdapter:
    cfg_raw = dict(raw)
    if not cfg_raw.get("omem_root"):
        cfg_raw["omem_root"] = str(Path(__file__).resolve().parents[3] / "system" / "O-Mem-StableEval")
    cfg = OMemAdapterConfig(**cfg_raw)
    return OMemAdapter(config=cfg)


# One memory system = one dedicated adapter implementation module.
# 一套记忆系统 = 一份独立适配器实现模块。
_ADAPTER_BUILDERS: Dict[str, AdapterBuilder] = {
    "membox": _build_membox,
    "membox_stable_eval": _build_membox_stable_eval,
    "membox:stable_eval": _build_membox_stable_eval,
    "o_mem": _build_o_mem,
    "o_mem_stable_eval": _build_o_mem_stable_eval,
    "o_mem:stable_eval": _build_o_mem_stable_eval,
    "omem": _build_o_mem,
    "omem:stable_eval": _build_o_mem_stable_eval,
}


def list_supported_memory_systems() -> Dict[str, str]:
    return {k: "registered" for k in sorted(_ADAPTER_BUILDERS.keys())}


def create_adapter_by_system(memory_system: str, config: Dict[str, Any] | None = None) -> Any:
    key = str(memory_system or "").strip().lower()
    if key not in _ADAPTER_BUILDERS:
        supported = ", ".join(sorted(_ADAPTER_BUILDERS.keys())) or "(none)"
        raise ValueError(f"unsupported memory system: {memory_system}. supported: {supported}")
    cfg = dict(config or {})
    return _ADAPTER_BUILDERS[key](cfg)


def export_adapter_runtime_manifest(adapter: Any) -> Dict[str, Any]:
    if hasattr(adapter, "runtime_manifest") and callable(getattr(adapter, "runtime_manifest")):
        out = dict(adapter.runtime_manifest())
        out["adapter_class"] = adapter.__class__.__name__
    else:
        out = {"adapter_class": adapter.__class__.__name__}
    cfg = getattr(adapter, "config", None)
    if cfg is not None:
        if is_dataclass(cfg):
            out["adapter_config"] = _redact_secrets(asdict(cfg))
        elif isinstance(cfg, dict):
            out["adapter_config"] = _redact_secrets(dict(cfg))
        else:
            out["adapter_config"] = {"repr": repr(cfg)}
    return out
