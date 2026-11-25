"""Load the HA-independent modules without importing Home Assistant."""

import importlib.util
from pathlib import Path
import sys
import types

PKG = "status2udp_pure"
BASE = Path(__file__).resolve().parents[1] / "custom_components" / "status2udp"

pkg = types.ModuleType(PKG)
pkg.__path__ = [str(BASE)]
sys.modules[PKG] = pkg

for name in ("values", "loxone"):
    spec = importlib.util.spec_from_file_location(f"{PKG}.{name}", BASE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG}.{name}"] = module
    spec.loader.exec_module(module)
