#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Download and patch NVIDIA Isaac SimReady 6.0 assets required by RoboVoLo.

Downloads 33 assets from the public NVIDIA Omniverse S3 bucket (or copies from a
local Isaac SimReady 6.0 download), then applies physics and material patches so
they work correctly in Isaac Sim simulation.

Requirements:
  - Python 3.9+
  - USD Python bindings (pip install usd-core, or use Isaac Sim's bundled Python)
    Required only for physics/material patches. Download works without it.

Usage:
  # Mode 1: Download from S3 (uses workspace_cache.json to locate assets)
  python download_simready_assets.py --agree-external-terms /path/to/RoboLab

  # Mode 2: Copy from local Isaac SimReady 6.0 download
  python download_simready_assets.py --agree-external-terms /path/to/RoboLab --source ~/isaac-simready-6.0

  # Re-run patches only (after download)
  python download_simready_assets.py --agree-external-terms /path/to/RoboLab --skip-download

Source: NVIDIA Isaac SimReady 6.0 (public, no authentication required)
  s3://omniverse-content-production/Assets/Isaac/6.0/Isaac/SimReady/
  Terms: NVIDIA Software License Agreement and Product Specific Terms for
  NVIDIA AI Products (including the NVIDIA Omniverse product specific terms)
  https://docs.omniverse.nvidia.com/ov/latest/common/NVIDIA_Omniverse_License_Agreement.html
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
RETAINED_TERMS = (
    SCRIPT_DIR / "LICENSES" / "LicenseRef-NVIDIA-SOFTWARE-LICENSE-AGREEMENT.txt",
    SCRIPT_DIR / "LICENSES" / "LicenseRef-NVIDIA-AI-PRODUCT-TERMS.txt",
)
OMNIVERSE_TERMS_URL = (
    "https://docs.omniverse.nvidia.com/ov/latest/common/"
    "NVIDIA_Omniverse_License_Agreement.html"
)
BUCKET_URL = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/"
S3_PREFIX = "Assets/Isaac/6.0/Isaac/SimReady/"
WORKSPACE_CACHE_URL = BUCKET_URL + urllib.parse.quote(
    S3_PREFIX + "workspace_cache.json", safe="/:"
)
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}

# Each asset: name -> (group, usd_stem_to_search_for)
# The usd_stem is the original SimReady filename (without extension) used to locate
# the asset folder either on S3 via workspace_cache.json or in a local download.
ASSETS: dict[str, tuple[str, str]] = {
    # Baskets
    "mini_plastic_basket": ("baskets", "sm_storage_basket_plastic_mini_a01_01"),
    "plastic_basket": ("baskets", "sm_misc_basket_plastic_a01_01"),
    # Boxes
    "open_cardboard_box": ("boxes_packaging", "sm_box_cardboard_open_a06_01"),
    "open_cardboard_box_002": ("boxes_packaging", "sm_box_cardboard_open_a05_01"),
    "open_cardboard_box_004": ("boxes_packaging", "sm_box_cardboard_open_a03_01"),
    # Dishware
    "bowl_002": ("dishware", "sm_kitchenware_bowl_s01_01"),
    "bowl_003": ("dishware", "sm_kitchenware_bowl_r01_01"),
    "bowl_005": ("dishware", "sm_kitchenware_bowl_p01_01"),
    "bowl_011": ("dishware", "sm_kitchenware_bowl_j01_01"),
    "bowl_015": ("dishware", "sm_kitchenware_bowl_f01_01"),
    "bowl_016": ("dishware", "sm_kitchenware_bowl_e01_01"),
    "bowl_019": ("dishware", "sm_kitchenware_bowl_b01_01"),
    "large_plastic_plate": ("dishware", "sm_dishware_plastic_bigPlate_a01_01"),
    # Food and drink
    "banana_2": ("food_and_drink", "sm_food_produce_banana_a01_01"),
    "beer_bottle_003": ("food_and_drink", "sm_food_beverage_beerBottle_o01_01"),
    "bitter_melon": ("food_and_drink", "sm_food_produce_bitterMelon_a01_01"),
    "coffee_cup_e01": ("food_and_drink", "sm_food_beverage_coffeeCup_e01_01"),
    "eggplant": ("food_and_drink", "sm_food_produce_eggplant_a01_01"),
    "lime": ("food_and_drink", "sm_food_produce_lime_a01_01"),
    "orange": ("food_and_drink", "sm_food_produce_orange_a01_01"),
    "soda_can_008": ("food_and_drink", "sm_food_beverage_can_g01_01"),
    # Kitchenware
    "cup_d01": ("kitchenware", "sm_kitchenware_cup_d01_01"),
    "cutting_board_b01": ("kitchenware", "sm_kitchenware_cuttingBoard_b01_01"),
    # Storage containers
    "beige_office_compost_can": ("storage_containers", "sm_trashCan_office_beige_a03_01"),
    "black_office_trash_can": ("storage_containers", "sm_trashCan_office_black_a03_01"),
    "green_crate": ("storage_containers", "sm_crate_green_a20_01"),
    "green_crate_002": ("storage_containers", "sm_crate_green_a02_01"),
    "green_recycle_container_004": ("storage_containers", "sm_container_recycle_green_a03_01"),
    "red_crate": ("storage_containers", "sm_crate_red_a19_01"),
    "white_crate": ("storage_containers", "sm_crate_white_a20_01"),
    "white_crate_002": ("storage_containers", "sm_crate_white_a14_01"),
    # Toys/recreation
    "golf_ball_002": ("toys_recreation", "sm_misc_golfBall_a02_01"),
    "ping_pong_paddle": ("toys_recreation", "sm_misc_toy_pongPaddle_bat_a01_01"),
}

# Directories/files to exclude when copying source assets
EXCLUDE_DIRS = {".thumbs", "web", "__pycache__"}
EXCLUDE_SUFFIXES = {".wrapp"}

# ─── Physics Patch Data ───────────────────────────────────────────────────────
# Assets needing PhysicsRigidBodyAPI + PhysicsMassAPI on the wrapper root.
# (mass_kg, (com_x, com_y, com_z), (inertia_x, inertia_y, inertia_z))

PHYSICS_PATCHES: dict[str, tuple[float, tuple, tuple]] = {
    "banana_2": (0.12, (0.0034, 0.0002, 0.0190), (0.0000246, 0.0000073, 0.0000246)),
    "beer_bottle_003": (0.18, (0.0001, -0.0001, 0.1073), (0.000396, 0.000396, 0.0000145)),
    "bitter_melon": (0.1462, (-0.0018, 0.0000, 0.0210), (0.0000595, 0.0000101, 0.0000595)),
    "coffee_cup_e01": (0.02, (0.0002, 0.0002, 0.0508), (0.0000135, 0.0000135, 0.0000049)),
    "eggplant": (0.2222, (-0.0011, 0.0000, 0.0336), (0.000101, 0.0000175, 0.000101)),
    "golf_ball_002": (0.05, (0.0, 0.0, 0.0214), (0.00000457, 0.00000457, 0.00000457)),
    "large_plastic_plate": (0.35, (0.0, 0.0, 0.0108), (0.000143, 0.000143, 0.000284)),
    "lime": (0.07, (0.0001, 0.0001, 0.0244), (0.00000773, 0.00000663, 0.00000663)),
    "orange": (0.16, (-0.0001, 0.0001, 0.0360), (0.0000168, 0.0000168, 0.0000168)),
    "soda_can_008": (0.02, (-0.0020, 0.0013, 0.0632), (0.0000296, 0.0000296, 0.0000103)),
    "beige_office_compost_can": (2.10, (0.0, 0.0, 0.25), (0.0598, 0.0598, 0.0322)),
    "black_office_trash_can": (2.10, (0.0, 0.0, 0.25), (0.0598, 0.0598, 0.0322)),
    "green_recycle_container_004": (3.0, (0.0, 0.0, 0.22), (0.0877, 0.0877, 0.0638)),
    "red_crate": (1.9329532, (0.0, 0.0, 0.050629046), (0.027610082, 0.059879806, 0.084268756)),
    "plastic_basket": (0.25, (-4.0978193e-8, 0, 0.05721845), (0.0011429344, 0.0011429344, 0.0017402103)),
    "open_cardboard_box": (0.6, (0.00012210011, 0.0006406605, 0.15118958), (0.017337184, 0.023236616, 0.031430487)),
    "open_cardboard_box_002": (0.6, (0.000025227666, -0.00019934773, 0.15118958), (0.01733739, 0.023554392, 0.031748466)),
    "open_cardboard_box_004": (0.6, (-8.940697e-8, -0.000008314848, 0.15118958), (0.017338438, 0.023834376, 0.0320295)),
    "bowl_002": (0.25, (7.450581e-9, -3.7252903e-9, 0.0256452), (0.0005579018, 0.0005579018, 0.0010089311)),
    "bowl_003": (0.25, (0, 0, 0.032691568), (0.00056785956, 0.00056785956, 0.0009575968)),
    "bowl_005": (0.25, (0, 0, 0.025401138), (0.00054771395, 0.00054771395, 0.0009879012)),
    "bowl_011": (0.25, (7.450581e-9, 2.9802322e-8, 0.03504303), (0.0011095385, 0.0011095385, 0.0020149103)),
    "bowl_015": (0.25, (0, 0, 0.04472042), (0.0018676425, 0.0018676425, 0.0034082255)),
    "bowl_016": (0.25, (6.3329935e-8, -1.3038516e-8, 0.024920996), (0.00020668996, 0.00020668996, 0.00031059203)),
    "bowl_019": (0.25, (0, 0, 0.030000582), (0.00054249883, 0.00054249883, 0.0009349977)),
    "cup_d01": (0.12800087, (0, 0, 0.040001474), (0.00013653519, 0.00013653519, 0.00013653426)),
    "cutting_board_b01": (0.2, (-0.0028566443, -2.2351742e-8, 0.19000158), (0.0032133332, 0.0024109322, 0.00081093225)),
    "green_crate": (1.8195432, (0, 0, 0.045744225), (0.026923396, 0.05796802, 0.08241622)),
    "green_crate_002": (3.5, (0, 0, 0.12145165), (0.066256985, 0.12597324, 0.15853259)),
    "white_crate": (1.8195432, (0, 0, 0.045175362), (0.026923396, 0.05796802, 0.08241622)),
    "white_crate_002": (2.8979747, (0, 0, 0.0749562), (0.04440983, 0.092789315, 0.1263454)),
    "ping_pong_paddle": (0.14903648, (-0.022133246, 0, 0.015563821), (0.00030054428, 0.00086315494, 0.0011396316)),
}

# ─── Material Patch Data ──────────────────────────────────────────────────────
# Shader property overrides for eval rendering visibility.

MATERIAL_PATCHES: dict[str, dict[str, float]] = {
    "soda_can_008": {
        "metallic": 0.30,
        "roughness": 0.38,
        "specular": 0.45,
        "clearcoat": 0.0,
        "clearcoatRoughness": 0.12,
    },
    "beer_bottle_003": {
        "opacity": 1.0,
        "metallic": 0.0,
        "roughness": 0.25,
        "specular": 0.6,
    },
}

# ─── S3 Utilities ─────────────────────────────────────────────────────────────


def fetch_asset_index() -> dict[str, str]:
    """Return ``{usd_stem: current_s3_folder}`` from workspace_cache.json.

    ``manifest.csv`` contains legacy catalog paths (for example
    ``Residential/Furnishing/Kitchen/Kitchenware/...``) that no longer match
    the folders published in this S3 snapshot.  ``workspace_cache.json`` is
    generated from the current workspace and contains the canonical entry USD
    path for every asset, so use it as the source of truth.
    """
    print("  Fetching workspace_cache.json from S3...")
    try:
        with urllib.request.urlopen(WORKSPACE_CACHE_URL, timeout=60) as r:
            cache = json.load(r)
    except Exception as e:
        print(f"  ERROR: Could not fetch workspace_cache.json: {e}")
        return {}

    if not isinstance(cache, dict):
        print("  ERROR: workspace_cache.json is not a JSON object")
        return {}

    candidates: dict[str, list[str]] = {}
    for path in cache:
        if not isinstance(path, str) or not path.startswith("SimReady/"):
            continue
        rel = path.removeprefix("SimReady/")
        folder, sep, filename = rel.rpartition("/")
        if not sep or not filename.lower().endswith((".usd", ".usda", ".usdc")):
            continue
        stem = filename.rsplit(".", 1)[0].lower()
        candidates.setdefault(stem, []).append(folder)

    mapping: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}
    for stem, folders in candidates.items():
        unique = sorted(set(folders))
        if len(unique) == 1:
            mapping[stem] = unique[0]
        else:
            duplicates[stem] = unique

    if duplicates:
        print(
            f"  WARNING: Ignoring {len(duplicates)} ambiguous USD stems in "
            "workspace_cache.json"
        )
    print(f"  Workspace index loaded: {len(mapping)} unambiguous entries")
    return mapping


def _include_s3_object(relative_path: str) -> bool:
    """Keep files needed to load the asset; omit previews and web exports."""
    parts = relative_path.split("/")
    if any(part in EXCLUDE_DIRS for part in parts):
        return False
    if any(relative_path.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return False
    # SimReady 6.0 currently publishes duplicate `Textures/` and `textures/`
    # trees. The current USD layers refer to the capitalized `Textures/` tree,
    # so retain that one and avoid downloading duplicate texture payloads.
    if parts and parts[0] == "textures":
        return False
    return True


def localize_s3_path(relative_path: str) -> str:
    """Map the published S3 layout to the pack's normalized local layout."""
    if relative_path.startswith("Textures/"):
        return "textures/" + relative_path.removeprefix("Textures/")
    return relative_path


def s3_list_folder(s3_folder: str) -> list[tuple[str, int]]:
    """List runtime files in an S3 asset folder as ``(key, size)`` pairs."""
    prefix = S3_PREFIX + s3_folder.strip("/") + "/"
    out: list[tuple[str, int]] = []
    token: str | None = None
    while True:
        params: dict[str, str] = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        url = BUCKET_URL + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
        root = ET.fromstring(data)
        for c in root.findall("s:Contents", NS):
            key = c.find("s:Key", NS).text or ""
            size = int(c.find("s:Size", NS).text or "0")
            # Relative to the asset folder
            rel = key[len(prefix):]
            if not rel or not _include_s3_object(rel):
                continue
            out.append((key, size))
        trunc = (root.find("s:IsTruncated", NS).text or "false").lower() == "true"
        if not trunc:
            break
        token_el = root.find("s:NextContinuationToken", NS)
        token = token_el.text if token_el is not None else None
        if not token:
            break
    return out


def download_s3_file(key: str, size: int, local_path: Path, retries: int = 4) -> str:
    """Download one S3 object. Returns 'downloaded', 'skipped', or 'error: ...'."""
    if local_path.exists() and local_path.stat().st_size == size:
        return "skipped"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = local_path.with_suffix(local_path.suffix + ".part")
    url = BUCKET_URL + urllib.parse.quote(key, safe="/")
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                while chunk := r.read(1024 * 1024):
                    f.write(chunk)
            if tmp.stat().st_size != size:
                raise IOError(f"Size mismatch: {tmp.stat().st_size} vs {size}")
            os.replace(tmp, local_path)
            return "downloaded"
        except Exception as e:
            tmp.unlink(missing_ok=True)
            if attempt == retries:
                return f"error: {e}"
            time.sleep(min(30, 2 ** attempt))
    return "error: exhausted retries"


# ─── Local Source Copy ────────────────────────────────────────────────────────


def find_in_local_source(source_root: Path, usd_stem: str) -> Path | None:
    """Find an asset folder in a local SimReady download by USD filename."""
    # Search for the USD file anywhere in the source tree
    for p in source_root.rglob(usd_stem + ".usd"):
        return p.parent
    for p in source_root.rglob(usd_stem + ".usda"):
        return p.parent
    return None


def copy_local_asset(src_dir: Path, dest_dir: Path) -> None:
    """Copy asset files from a local SimReady source, filtering out thumbnails/web."""
    source_dest = dest_dir / "source"
    if source_dest.exists():
        shutil.rmtree(source_dest)
    source_dest.mkdir(parents=True, exist_ok=True)

    for item in src_dir.iterdir():
        if item.name in EXCLUDE_DIRS or item.suffix in EXCLUDE_SUFFIXES:
            continue
        if item.name.startswith("."):
            # Keep .simready_publish.json but skip .wrapp etc.
            if item.suffix == ".json":
                shutil.copy2(item, source_dest / item.name)
            continue
        if item.is_dir():
            if item.name in ("payloads", "materials", "textures"):
                shutil.copytree(item, source_dest / item.name,
                                ignore=shutil.ignore_patterns(*EXCLUDE_DIRS, "*.wrapp"))
        elif item.is_file():
            if item.suffix in (".usd", ".usda", ".json"):
                shutil.copy2(item, source_dest / item.name)


# ─── Patching ─────────────────────────────────────────────────────────────────


def write_wrapper(asset_dir: Path, name: str) -> None:
    """Write the wrapper USDA that references source payloads and adds physics."""
    source = asset_dir / "source"
    refs = []
    if (source / "payloads" / "base.usda").exists():
        refs.append("@source/payloads/base.usda@</RootNode>")
    physics_dir = source / "payloads" / "Physics"
    if (physics_dir / "physics.usda").exists():
        refs.append("@source/payloads/Physics/physics.usda@</RootNode>")
    if (physics_dir / "physx.usda").exists():
        refs.append("@source/payloads/Physics/physx.usda@</RootNode>")
    if not refs:
        for f in source.iterdir():
            if f.suffix in (".usd", ".usda") and f.is_file() and not f.name.startswith("."):
                refs.append(f"@source/{f.name}@</RootNode>")
                break

    physics_patch = PHYSICS_PATCHES.get(name)
    api_line = ""
    physics_props = ""
    if physics_patch:
        mass, com, inertia = physics_patch
        api_line = '\n    prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]'
        physics_props = f"""
    point3f physics:centerOfMass = ({com[0]}, {com[1]}, {com[2]})
    float3 physics:diagonalInertia = ({inertia[0]}, {inertia[1]}, {inertia[2]})
    float physics:mass = {mass}
    quatf physics:principalAxes = (1, 0, 0, 0)
    bool physics:rigidBodyEnabled = 1"""

    wrapper = asset_dir / f"{name}.usda"
    wrapper.write_text(f"""#usda 1.0
(
    defaultPrim = "{name}"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "{name}" ({api_line}
    prepend references = [{", ".join(refs)}]
)
{{{physics_props}
    custom string class = "prop"
    custom string dataset = "simready"
}}
""", encoding="utf-8")


def patch_texture_paths(asset_dir: Path) -> None:
    """Fix absolute/Windows texture paths to be relative."""
    source_dir = asset_dir / "source"
    if not source_dir.exists():
        return
    for p in source_dir.rglob("*.usda"):
        try:
            text = p.read_text(errors="replace")
        except Exception:
            continue
        old = text
        text = text.replace("\\", "/")
        # Normalize both old absolute paths and the current capitalized S3
        # texture tree into the lowercase layout used by the generated pack.
        text = re.sub(r"@[^@]*?/[Tt]extures/([^@/]+)@", r"@../textures/\1@", text)
        text = re.sub(r"@\.\./Textures/([^@/]+)@", r"@../textures/\1@", text)
        text = re.sub(r"@C:/[^@]*?/materials/([^@]+)@", r"@../materials/\1@", text)
        # Some payloads expect OmniPBR.mdl beside materials.usda while S3
        # publishes it under source_assets/.
        text = text.replace("@OmniPBR.mdl@", "@../source_assets/OmniPBR.mdl@")
        if text != old:
            p.write_text(text, encoding="utf-8")


def patch_nested_rigid_bodies(asset_dir: Path, name: str) -> None:
    """Disable nested rigid body APIs in source payloads."""
    if name not in PHYSICS_PATCHES:
        return
    from pxr import Usd, UsdPhysics

    payloads = asset_dir / "source" / "payloads"
    candidates = [
        payloads / "base.usda",
        payloads / "instances.usda",
        payloads / "Physics" / "physics.usda",
        payloads / "Physics" / "physx.usda",
    ]
    for source_layer in candidates:
        if not source_layer.exists():
            continue
        stage = Usd.Stage.Open(str(source_layer))
        if not stage:
            continue

        changed = False
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.RigidBodyAPI):
                prim.RemoveAPI(UsdPhysics.RigidBodyAPI)
                changed = True
            if prim.HasAPI(UsdPhysics.MassAPI):
                prim.RemoveAPI(UsdPhysics.MassAPI)
                changed = True
                for attr_name in ("physics:mass", "physics:centerOfMass", "physics:diagonalInertia"):
                    attr = prim.GetAttribute(attr_name)
                    if attr and attr.IsAuthored():
                        attr.Clear()
        if changed:
            stage.GetRootLayer().Save()


def patch_materials(asset_dir: Path, name: str) -> None:
    """Override material shader properties for eval rendering."""
    mat_patch = MATERIAL_PATCHES.get(name)
    if not mat_patch:
        return
    from pxr import Sdf, Usd, UsdShade

    materials = asset_dir / "source" / "payloads" / "materials.usda"
    if not materials.exists():
        return
    stage = Usd.Stage.Open(str(materials))
    if not stage:
        return

    changed = False
    for prim in stage.Traverse():
        if prim.GetTypeName() != "Shader":
            continue
        id_attr = prim.GetAttribute("info:id")
        if not id_attr or id_attr.Get() != "UsdPreviewSurface":
            continue
        shader = UsdShade.Shader(prim)
        for prop_name, value in mat_patch.items():
            inp = shader.GetInput(prop_name)
            if not inp:
                inp = shader.CreateInput(prop_name, Sdf.ValueTypeNames.Float)
            inp.ClearSources()
            inp.Set(float(value))
            changed = True
    if changed:
        stage.GetRootLayer().Save()


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Download and patch NVIDIA SimReady assets for RoboVoLo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "robolab",
        type=Path,
        help="path to a RoboLab v0.3.0 checkout",
    )
    ap.add_argument(
        "--agree-external-terms",
        action="store_true",
        help="confirm that you reviewed and agree to the external material terms",
    )
    ap.add_argument("--source", type=Path, default=None,
                    help="Path to local Isaac SimReady 6.0 download (skips S3 download)")
    ap.add_argument("--workers", type=int, default=6,
                    help="Parallel download threads (default: 6)")
    ap.add_argument("--skip-download", action="store_true",
                    help="Skip download phase, only apply patches")
    args = ap.parse_args()

    print("External materials notice:")
    print("  This tool retrieves NVIDIA Isaac SimReady 6.0 materials.")
    print("  Those materials are not distributed with RoboVoLo.")
    print(f"  Source: {BUCKET_URL}{S3_PREFIX}")
    print("  Retained terms:")
    for terms_path in RETAINED_TERMS:
        print(f"    - {terms_path}")
    print(f"  Official source: {OMNIVERSE_TERMS_URL}")
    print(f"  The {len(ASSETS)} requested asset families are:")
    for name in ASSETS:
        print(f"    - {name}")
    print()
    missing_terms = [path for path in RETAINED_TERMS if not path.is_file()]
    if missing_terms:
        print("ERROR: Retained external terms are missing:", file=sys.stderr)
        for path in missing_terms:
            print(f"  {path}", file=sys.stderr)
        return 2
    if not args.agree_external_terms:
        print(
            "ERROR: Review the retained external terms, then re-run with "
            "--agree-external-terms to confirm acceptance.",
            file=sys.stderr,
        )
        return 2

    robolab: Path = args.robolab.expanduser().resolve()
    if not (robolab / "assets" / "objects").is_dir() or not (robolab / "robolab").is_dir():
        print(
            f"ERROR: {robolab} does not look like a RoboLab checkout "
            "(expected assets/objects/ and robolab/).",
            file=sys.stderr,
        )
        return 2
    dest = robolab / "assets" / "objects" / "simready"
    dest.mkdir(parents=True, exist_ok=True)
    terms_dest = dest / "LICENSES"
    terms_dest.mkdir(parents=True, exist_ok=True)
    for terms_path in RETAINED_TERMS:
        shutil.copy2(terms_path, terms_dest / terms_path.name)

    print("━" * 60)
    print("  SimReady Asset Downloader + Patcher")
    print("  Source: NVIDIA Isaac SimReady 6.0")
    print(f"  Dest:   {dest}")
    print(f"  Assets: {len(ASSETS)}")
    print("━" * 60)
    print()

    # ── Phase 1: Acquire source files ─────────────────────────
    if not args.skip_download:
        if args.source:
            # Mode 2: local copy
            source_root = args.source.expanduser().resolve()
            print(f"PHASE 1: Copying from local source: {source_root}")
            print()
            if not source_root.exists():
                print(f"ERROR: Source directory does not exist: {source_root}")
                return 1
            errors = 0
            for i, (name, (group, usd_stem)) in enumerate(ASSETS.items(), 1):
                asset_dir = dest / group / name
                src = find_in_local_source(source_root, usd_stem)
                if src:
                    copy_local_asset(src, asset_dir)
                    print(f"  [{i}/{len(ASSETS)}] ✓ {name}")
                else:
                    print(f"  [{i}/{len(ASSETS)}] ✗ {name} (not found: {usd_stem})")
                    errors += 1
            print(f"\nCopy complete. {len(ASSETS) - errors} succeeded, {errors} not found.")
            if errors:
                print("ERROR: One or more required assets were not found.")
                return 1
        else:
            # Mode 1: S3 download
            print("PHASE 1: Downloading from S3")
            print()
            asset_index = fetch_asset_index()
            print()
            if not asset_index:
                print("ERROR: Could not build the SimReady S3 asset index.")
                return 1
            errors = 0
            for i, (name, (group, usd_stem)) in enumerate(ASSETS.items(), 1):
                # Resolve the current S3 folder by the stable entry-USD stem.
                s3_folder = asset_index.get(usd_stem.lower())
                if not s3_folder:
                    print(
                        f"  [{i}/{len(ASSETS)}] ✗ {name} "
                        f"(not in workspace index: {usd_stem})"
                    )
                    errors += 1
                    continue

                asset_dir = dest / group / name
                source_dir = asset_dir / "source"
                print(f"  [{i}/{len(ASSETS)}] {name} <- {s3_folder}")

                objects = s3_list_folder(s3_folder)
                if not objects:
                    print("    ERROR: No files found at S3 path")
                    errors += 1
                    continue

                dl_count = 0
                skip_count = 0
                err_count = 0
                with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
                    futures = {}
                    for key, size in objects:
                        rel = key[len(S3_PREFIX + s3_folder + "/"):]
                        local_rel = localize_s3_path(rel)
                        local_path = source_dir / local_rel
                        futures[ex.submit(download_s3_file, key, size, local_path)] = local_rel
                    for fut in cf.as_completed(futures):
                        status = fut.result()
                        if status == "downloaded":
                            dl_count += 1
                        elif status == "skipped":
                            skip_count += 1
                        else:
                            err_count += 1
                            print(f"    {status}: {futures[fut]}")
                total = dl_count + skip_count + err_count
                print(f"    {total} files ({dl_count} new, {skip_count} cached, {err_count} errors)")
                if err_count:
                    errors += 1
            print(f"\nDownload complete. Errors: {errors}")
            if errors:
                print("ERROR: One or more required assets could not be downloaded.")
                return 1
        print()

    # ── Phase 2: Write wrappers ───────────────────────────────
    print("PHASE 2: Writing wrapper USDs + fixing texture paths")
    for name, (group, _) in ASSETS.items():
        asset_dir = dest / group / name
        if not (asset_dir / "source").exists():
            continue
        write_wrapper(asset_dir, name)
        patch_texture_paths(asset_dir)
    print("  Done.\n")

    # ── Phase 3: Physics patches ──────────────────────────────
    print("PHASE 3: Patching physics (disabling nested rigid bodies)")
    try:
        from pxr import Usd  # noqa: F401
        has_pxr = True
    except ImportError:
        has_pxr = False

    if not has_pxr:
        print("  WARNING: 'pxr' (USD Python) not available.")
        print("  Skipping physics + material patches.")
        print("  Install with: pip install usd-core")
        print("  Or run with Isaac Sim's Python.")
    else:
        for name in PHYSICS_PATCHES:
            group = ASSETS[name][0]
            asset_dir = dest / group / name
            if not (asset_dir / "source").exists():
                continue
            patch_nested_rigid_bodies(asset_dir, name)
            print(f"  ✓ {name}")
        print()

        # ── Phase 4: Material patches ─────────────────────────
        print("PHASE 4: Patching materials for eval rendering")
        for name in MATERIAL_PATCHES:
            group = ASSETS[name][0]
            asset_dir = dest / group / name
            if not (asset_dir / "source").exists():
                continue
            patch_materials(asset_dir, name)
            print(f"  ✓ {name}")
    print()

    # ── Summary ───────────────────────────────────────────────
    present = sum(1 for n, (g, _) in ASSETS.items() if (dest / g / n / f"{n}.usda").exists())
    print("━" * 60)
    print(f"  COMPLETE: {present}/{len(ASSETS)} assets ready")
    print(f"  Location: {dest}")
    print("━" * 60)
    if present != len(ASSETS):
        print("ERROR: Asset set is incomplete.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
