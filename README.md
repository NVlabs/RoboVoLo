# RoboVoLo

RoboVoLo is the benchmark task pack for [VoLo: A Physical Orchestrator for Open-Vocabulary Long-Horizon Manipulation](https://chicychen.github.io/VoLo/). It contains 126 RoboLab tasks, 123 USD scenes, benchmark images, and three custom object-asset families.

This repository holds the **benchmark tasks and assets**. The VoLo orchestrator code — the VLM-driven proxy that runs and evaluates policies on these tasks — lives in the companion repository [**VoLoAgent**](https://github.com/NVlabs/VoLoAgent).

**License overview:** Code, tasks, scenes, benchmark images, and NVIDIA-authored assets in this repository are licensed under the [Apache License 2.0](LICENSE) unless otherwise noted. Redistributed third-party textures retain their asset-specific CC0-1.0 terms; see [ASSET_LICENSES.md](ASSET_LICENSES.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Required external assets are not distributed with this repository and must be obtained separately under their own terms.

## What this repository contains

- task definitions and metadata in `tasks/`, `tasks.json`, and `pack.json`;
- released benchmark scenes in `scenes/` and their images in `images/`;
- redistributable art-shape, chemistry-cube, and math-cube assets in `assets/objects/`;
- installers for adding the benchmark to a RoboLab checkout; and
- a downloader for required NVIDIA Isaac SimReady 6.0 assets that are **not** included in this repository.

The scenes also reference assets shipped by [RoboLab v0.3.0](https://github.com/NVlabs/RoboLab/tree/v0.3.0). Those RoboLab payloads are not duplicated here.

## Installation

### 1. Install RoboLab v0.3.0

Clone the required release, then follow RoboLab's environment installation instructions:

```bash
git clone --branch v0.3.0 --depth 1 https://github.com/NVlabs/RoboLab.git
```

RoboLab v0.3.0 natively discovers the `robovolo` content pack and includes the grouped task predicates required by RoboVoLo. The RoboVoLo installer validates these APIs before changing the RoboLab checkout.

### 2. Clone RoboVoLo and obtain its Git LFS objects

```bash
git lfs install
git clone https://github.com/NVlabs/RoboVoLo.git
cd RoboVoLo
git lfs pull
```

### 3. Install the RoboVoLo utility requirements

Install the Python dependencies in the same environment you will use to run the download and installation scripts:

```bash
python -m pip install -r requirements.txt
```

This installs the USD Python bindings required to patch the SimReady assets correctly.

### 4. Download required SimReady dependencies into RoboLab

Review the [external materials notice](#external-materials-notice), the retained [NVIDIA Software License Agreement](LICENSES/LicenseRef-NVIDIA-SOFTWARE-LICENSE-AGREEMENT.txt), and the retained [Product Specific Terms for NVIDIA AI Products](LICENSES/LicenseRef-NVIDIA-AI-PRODUCT-TERMS.txt), then run:

```bash
python download_simready_assets.py \
  --agree-external-terms \
  /path/to/RoboLab
```

The script prints the source, terms, and complete asset list before downloading.

### 5. Install the RoboVoLo pack into RoboLab

The installer accepts the local RoboLab checkout as its positional argument and installs the custom assets, tasks, and scenes:

```bash
python install.py /path/to/RoboLab
```

The installer requires a fresh installation and stops without changing the checkout if any RoboVoLo-managed destination already exists. Run `python install.py --help` for usage details.

## External materials notice

NOTICE AND DISCLAIMER: This software automatically retrieves, accesses or interacts with external materials.
Those retrieved materials are not distributed with this software and are governed solely by separate terms, conditions and licenses.
You are solely responsible for finding, reviewing and complying with all applicable terms, conditions, and licenses, and for verifying the security, integrity and suitability of any retrieved materials for your specific use case.
This software is provided "AS IS", without warranty of any kind.
The author makes no representations or warranties regarding any retrieved materials, and assumes no liability for any losses, damages, liabilities or legal consequences from your use or inability to use this software or any retrieved materials.
Use this software and the retrieved materials at your own risk.

### Required external assets

The downloader retrieves the 33 required NVIDIA Isaac SimReady 6.0 asset families listed in `download_simready_assets.py` from NVIDIA's public Omniverse content bucket. These payloads are not present in Git or Git LFS. They are governed by the retained [NVIDIA Software License Agreement](LICENSES/LicenseRef-NVIDIA-SOFTWARE-LICENSE-AGREEMENT.txt), the retained [Product Specific Terms for NVIDIA AI Products](LICENSES/LicenseRef-NVIDIA-AI-PRODUCT-TERMS.txt), which incorporate the NVIDIA Omniverse product specific terms, and any applicable asset-specific terms. See the [current Omniverse licensing page](https://docs.omniverse.nvidia.com/ov/latest/common/NVIDIA_Omniverse_License_Agreement.html) for the official online source.

## Repository structure

- `tasks/` — benchmark task definitions
- `scenes/` — benchmark USD scene compositions
- `images/` — benchmark scene renders
- `assets/objects/` — included custom object assets and CC0 textures
- `install.py` — installs included assets, tasks, and scenes into RoboLab
- `download_simready_assets.py` — explicitly invoked external-material downloader
- `requirements.txt` — Python requirements for the download and installation utilities
- `LICENSES/` — retained third-party and external-material license terms
- `ASSET_LICENSES.md` — path-level asset license manifest
- `THIRD_PARTY_NOTICES.md` — third-party sources and notices

## Related Projects

- [**VoLoAgent**](https://github.com/NVlabs/VoLoAgent) — the VoLo orchestrator: a
  VLM-driven proxy that runs and evaluates policies on the RoboVoLo benchmark.
- [**SpaceTools**](https://spacetools.github.io/) (CVPR 2026) — Tool-Augmented
  Spatial Reasoning via Double Interactive RL, which equips VLMs with vision and
  robotic tools for spatial reasoning and real-world manipulation.

## Citation

Paper: [arXiv:2606.07723](https://arxiv.org/abs/2606.07723)

Project website: <https://chicychen.github.io/VoLo/>

```bibtex
@article{chen2026volo,
    title         = {VoLo: A Physical Orchestrator for Open-Vocabulary Long-Horizon Manipulation},
    author        = {Chen, Siyi and Hadfield, Hugo and Zook, Alex and Uy, Mikaela Angelina and
                     Song, Chan Hee and Coumans, Erwin and Yang, Xuning and Ladhak, Faisal and
                     Qu, Qing and Birchfield, Stan and Tremblay, Jonathan and Blukis, Valts},
    journal       = {arXiv preprint arXiv:2606.07723},
    year          = {2026},
    eprint        = {2606.07723},
    archivePrefix = {arXiv},
    primaryClass  = {cs.RO},
    url           = {https://arxiv.org/abs/2606.07723}
}
```

## Contributing

External contributions are accepted under the Developer Certificate of Origin. Every contribution must be signed off; see [CONTRIBUTING.md](CONTRIBUTING.md).
