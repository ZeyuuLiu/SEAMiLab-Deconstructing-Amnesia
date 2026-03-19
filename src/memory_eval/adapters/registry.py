from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Dict

from memory_eval.adapters.o_mem_adapter import OMemAdapter, OMemAdapterConfig


AdapterBuilder = Callable[[Dict[str, Any]], Any]


def _build_o_mem(raw: Dict[str, Any]) -> OMemAdapter:
    cfg = OMemAdapterConfig(**raw)
    return OMemAdapter(config=cfg)


# One memory system = one dedicated adapter implementation module.
# 一套记忆系统 = 一份独立适配器实现模块。
_ADAPTER_BUILDERS: Dict[str, AdapterBuilder] = {
    "o_mem": _build_o_mem,
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
    """
    Build a lightweight adapter manifest for audit/report.
    构建适配器运行清单，用于审计与可追溯。
    """
    out: Dict[str, Any] = {"adapter_class": adapter.__class__.__name__}
    cfg = getattr(adapter, "config", None)
    if cfg is not None:
        if is_dataclass(cfg):
            out["adapter_config"] = asdict(cfg)
        elif isinstance(cfg, dict):
            out["adapter_config"] = dict(cfg)
        else:
            out["adapter_config"] = {"repr": repr(cfg)}
    return out
