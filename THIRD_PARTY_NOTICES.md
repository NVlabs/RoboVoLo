# Third-Party Notices

RoboVoLo code and NVIDIA-authored assets are licensed under Apache-2.0. The following separately licensed material is redistributed by, referenced by, or retrieved for this repository.

## ambientCG textures (redistributed)

The texture sets below are provided by ambientCG under the Creative Commons CC0 1.0 Universal dedication. Attribution is not required by CC0, but source information is recorded for provenance.

Upstream: <https://ambientcg.com/>

License: CC0 1.0 Universal; a copy is provided at `LICENSES/CC0-1.0.txt`. Canonical URL: <https://creativecommons.org/publicdomain/zero/1.0/>

Copyright/creator: ambientCG contributors

| Component | Repository path | Upstream source | Modified by NVIDIA? |
|---|---|---|---|
| Plastic007 | `assets/objects/art_shapes/textures/Plastic007*` | <https://ambientcg.com/view?id=Plastic007> | No source-map modification identified. |
| Plastic008 | `assets/objects/art_shapes/textures/Plastic008*` | <https://ambientcg.com/view?id=Plastic008> | No source-map modification identified. |
| Plastic011 | `assets/objects/art_shapes/textures/Plastic011*` | <https://ambientcg.com/view?id=Plastic011> | No source-map modification identified. |
| Plastic013A | `assets/objects/art_shapes/textures/Plastic013A*` | <https://ambientcg.com/view?id=Plastic013A> | No source-map modification identified. |
| Plastic014A | `assets/objects/art_shapes/textures/Plastic014A*` | <https://ambientcg.com/view?id=Plastic014A> | No source-map modification identified. |
| Plastic015A | `assets/objects/art_shapes/textures/Plastic015A*` | <https://ambientcg.com/view?id=Plastic015A> | No source-map modification identified. |
| Plastic016A | `assets/objects/art_shapes/textures/Plastic016A*` | <https://ambientcg.com/view?id=Plastic016A> | No source-map modification identified. |
| Plastic017A | `assets/objects/art_shapes/textures/Plastic017A*` | <https://ambientcg.com/view?id=Plastic017A> | No source-map modification identified. |
| Porcelain001 | `assets/objects/chemistry_cubes/textures/Porcelain001*` | <https://ambientcg.com/view?id=Porcelain001> | NVIDIA created category-tinted color variants from the source texture. |
| Wood095 | `assets/objects/math_wood_cubes/textures/Wood095*` | <https://ambientcg.com/view?id=Wood095> | No source-map modification identified. |

## NVIDIA Isaac SimReady 6.0 (not redistributed)

`download_simready_assets.py` retrieves the 33 required asset families enumerated in that script from NVIDIA's public Omniverse content bucket under the `Assets/Isaac/6.0/Isaac/SimReady/` prefix. The retrieved files are **not distributed with this repository**.

- Source catalog: <https://omniverse-content-production.s3-us-west-2.amazonaws.com/>
- Governing terms: the [NVIDIA Software License Agreement](LICENSES/LicenseRef-NVIDIA-SOFTWARE-LICENSE-AGREEMENT.txt) and [Product Specific Terms for NVIDIA AI Products](LICENSES/LicenseRef-NVIDIA-AI-PRODUCT-TERMS.txt), which incorporate the NVIDIA Omniverse product specific terms. Official sources are linked in `ASSET_LICENSES.md`.
- Local modifications: the downloader writes RoboLab wrapper layers, normalizes referenced paths, and applies documented physics and material adjustments.

Users must review and accept the external terms explicitly before acquisition. The NVIDIA and third-party notices contained in downloaded source files must be retained.

## RoboLab runtime dependencies (not redistributed here)

RoboVoLo scenes reference fixtures and object datasets supplied by RoboLab, including RoboLab's `basic`, `fixtures`, `fruits_veggies`, `handal`, `hope`, `hot3d`, `objaverse`, `vomp`, and `ycb` asset directories. These payloads are not redistributed by this repository.

- Component: NVIDIA RoboLab v0.3.0
- Source: <https://github.com/NVlabs/RoboLab/tree/v0.3.0>
- Required tag: `v0.3.0`
- Licenses and attributions: see the license and third-party notices shipped in that tagged RoboLab release.

RoboVoLo also depends on the software environment required by RoboLab, including Isaac Lab, Isaac Sim, PyTorch, and their transitive dependencies. Their code is not vendored here and remains governed by the respective upstream terms.
