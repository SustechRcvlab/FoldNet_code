# Codebase of FoldNet
This repository is the official implementation of [FoldNet](https://pku-epic.github.io/FoldNet/).

## install

1. Download the repository
```
git clone https://github.com/chen01yx/FoldNet_code.git --recurse-submodules
cd FoldNet_code
git submodule update --init --recursive
```

2. Create Conda environment
```
conda create -n FoldNet python=3.9.20
pip install -e . --use-pep517
sh setup.sh
sudo apt install ffmpeg
```

3. Install Blender
- Download [blender](https://www.blender.org/download/release/Blender4.2/blender-4.2.9-linux-x64.tar.xz)
- Append the following code to ~/.zshrc or ~/.bashrc
    ```
    export BLENDER_PATH="/your/path/to/blender-4.2.9-linux-x64"
    export PATH="$BLENDER_PATH:$PATH"
    alias blender_python="$BLENDER_PATH/4.2/python/bin/python3.11"
    ```
- Install packages for blender's python
    ```
    cd external/batch_urdf && blender_python -m pip install -e . && cd ../..
    cd external/bpycv && blender_python -m pip install -e . && cd ../..
    blender_python -m pip install psutil
    sudo apt install libsm6
    ```
- Test blender
    ```
    blender src/garmentds/foldenv/scene.blend --python src/garmentds/foldenv/blender_script.py --background -- --run_test
    ```
- Download blender asset
    ```
    blender src/garmentds/foldenv/scene.blend --python src/garmentds/foldenv/blender_script.py --background -- --run_init
    ```

4. Build PyFlex
We provide compiled pyflex for python 3.9. Please refer to src/pyflex/libs/how_to_run_without_docker.md for more details.
- Append the following code to ~/.zshrc or ~/.bashrc
    ```
    export PYFLEX_PATH=/your/path/to/FoldNet_code/src/pyflex
    export PYTHONPATH="$PYFLEX_PATH/libs":$PYTHONPATH
    export LD_LIBRARY_PATH="$PYFLEX_PATH/libs":$LD_LIBRARY_PATH
    ```
- Install
    ```
    sudo apt install libasound2
    sudo apt install libegl1
    ```
- Test
    ```
    import pyflex
    pyflex.init(True, False, 0, 0, 0)
    ```
5. Full test
    ```
    CUDA_VISIBLE_DEVICES=0 python run/fold_multi_cat.py env.cloth_obj_path=asset/garment_example/mesh.obj env.render_process_num=1 '+env.init_cloth_vel_range=[1.,2.]'
    ```

## simulation environment
Please refer to src/garmentds/foldenv/simenv_readme.md for more details.

## mesh synthesis
Coming soon.