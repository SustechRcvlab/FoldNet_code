# Codebase of FoldNet
This repository is the official implementation of [FoldNet](https://pku-epic.github.io/FoldNet/).

## Install

1. Download the repository
```bash
git clone https://github.com/chen01yx/FoldNet_code.git --recurse-submodules
cd FoldNet_code
git submodule update --init --recursive
```

2. Create Conda environment
```bash
conda create -n FoldNet python=3.9.20
pip install -e . --use-pep517
sh setup.sh
sudo apt install ffmpeg
```

3. Install Blender
- Download [blender](https://www.blender.org/download/release/Blender4.2/blender-4.2.9-linux-x64.tar.xz)
- Append the following code to ~/.zshrc or ~/.bashrc
    ```bash
    export BLENDER_PATH="/your/path/to/blender-4.2.9-linux-x64"
    export PATH="$BLENDER_PATH:$PATH"
    alias blender_python="$BLENDER_PATH/4.2/python/bin/python3.11"
    ```
- Install packages for blender's python
    ```bash
    cd external/batch_urdf && blender_python -m pip install -e . && cd ../..
    cd external/bpycv && blender_python -m pip install -e . && cd ../..
    blender_python -m pip install psutil
    sudo apt install libsm6
    ```
- Test blender
    ```bash
    blender src/garmentds/foldenv/scene.blend --python src/garmentds/foldenv/blender_script.py --background -- --run_test
    ```
- Download blender asset
    ```bash
    blender src/garmentds/foldenv/scene.blend --python src/garmentds/foldenv/blender_script.py --background -- --run_init
    ```

4. Build PyFlex
We provide compiled pyflex for python 3.9. Please refer to src/pyflex/libs/how_to_run_without_docker.md for more details.
- Append the following code to ~/.zshrc or ~/.bashrc
    ```bash
    export PYFLEX_PATH=/your/path/to/FoldNet_code/src/pyflex
    export PYTHONPATH="$PYFLEX_PATH/libs":$PYTHONPATH
    export LD_LIBRARY_PATH="$PYFLEX_PATH/libs":$LD_LIBRARY_PATH
    ```
- Install
    ```bash
    sudo apt install libasound2
    sudo apt install libegl1
    ```
- Test
    ```python
    import pyflex
    pyflex.init(True, False, 0, 0, 0)
    ```
5. Full test
    ```bash
    CUDA_VISIBLE_DEVICES=0 python run/fold_multi_cat.py env.cloth_obj_path=asset/garment_example/0/mesh.obj env.render_process_num=1 '+env.init_cloth_vel_range=[1.,2.]'
    ```

## Asset Synthesis

1. Generate Mesh
```bash
python script/gen_data/gen_mesh.py --category tshirt_sp --num_to_generate 10 
```

2. Generate Textures
```bash
python script/gen_data/gen_texture.py --category tshirt_sp --num_to_generate 10 
```

3. Generate textured clothes
```bash
python run/generate_cloth.py garment.category=tshirt_sp garment.num_to_generate=1
```

## Keypoints Detection

1. Generate Training Data

    Textured clothes assets should be generated first using the previous step. Then run the following command (which will deform the clothes, render the RGB and mask, and save the keypoints) to generate training data for keypoints detection.

```bash
python run/generate_training_data.py garment.category=tshirt_sp garment.num_to_generate=1 garment.cloth_input_dir="$PWD/asset/garment_example"
```

2. Train Keypoints Detection Model

- First, download the "FreeMono" font (requested for visualization):

```bash
sudo apt update
sudo apt install fonts-freefont-ttf
```

- Then, start training by running the following command (make sure you have generated training data before running this command):

```bash
python run/run_keypoints_learn.py train.category=tshirt_sp train.path.data_paths="['$PWD/data/train/tshirt_sp/synthetic']"
```


