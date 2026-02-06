import os
import numpy as np

from garmentds.gentexture.simEnv import SimEnv

def make_data(
    category: str,
    start_idx: int,
    num_to_generate: int,
    cloth_input_dir: str,
    cloth_output_dir: str,
    texture_type: str,
    sim_cfg: dict,
    deform_cfg: dict,
    **kwargs
):
    """
    Make training data for keypoint detection.
    
    Parameters:
        - category: category of cloth. Can be tshirt, tshirt_sp, trousers, vest_close or hooded_close
        - start_idx: start naming index in output directory
        - num_to_generate: number of data to generate
        - cloth_input_dir: directory of cloth meshes
            - the input directory should be structered as follows:

                -- cloth_input_dir
                    -- 0
                        -- mesh.obj
                        -- other_files... (like material_0.png)
                    -- 1
                        -- mesh.obj
                        -- other_files...
                    -- ...
            
        - cloth_output_dir: directory of output data
        - texture_type: can be synthetic, polyhaven or text2tex
        - sim_cfg: configuration for simulation environment
        - deform_cfg: configuration for deformation
    """

    # initialize
    sim = SimEnv(**sim_cfg)
    base_dir = os.environ["FOLDNET_BASE_DIR"]

    # get all cloth meshes
    if not os.path.exists(cloth_input_dir):
        raise ValueError(f"{cloth_input_dir} does not exist.")
    all_clothes = [d for d in os.listdir(cloth_input_dir) if 
                   os.path.isdir(os.path.join(cloth_input_dir, d)) and 
                   os.path.isfile(os.path.join(cloth_input_dir, d, "mesh.obj"))]
    
    # set output directory
    if cloth_output_dir is None or not os.path.exists(cloth_output_dir):
        cloth_output_dir = os.path.join(base_dir, f"data/train/{category}/{texture_type}")

    # generate training data
    for i in range(num_to_generate):
        output_path = os.path.join(cloth_output_dir, str(i+start_idx))
        os.makedirs(output_path, exist_ok=True)

        # select cloth mesh
        random_idx = np.random.choice(all_clothes)
        cloth_path = os.path.join(cloth_input_dir, random_idx)

        # deform cloth
        print("[ INFO ] start deforming cloth...")
        sim.set_scene(category, os.path.join(cloth_path, "mesh.obj"))
        sim.deform_cloth(output_dir=output_path, **deform_cfg)
        print(f"[ INFO ] cloth deformed successfully, output path is {output_path}")

        while True:
            # get rgb, mask and keypoints_2D
            print("[ INFO ] start rendering...")
            script = os.path.join(base_dir, "src/garmentds/gentexture/utils/blender_script.py")
            cloth_use_polyhaven_textures = False
            if texture_type == "polyhaven":
                cloth_use_polyhaven_textures = True
            sim.render(script, output_path, need_mask=True, need_keypoints_2D=True,
                       cloth_use_polyhaven_textures=cloth_use_polyhaven_textures)
            if sanity_check(output_path):
                break

        # touch a new file named "completed.txt" so Dataloader can find it
        with open(os.path.join(output_path, "completed.txt"), "w") as f:
            pass

    print("[ INFO ] Data generated successfully, exit...")

def sanity_check(dir:str):
    """
        Check if the output directory contains all necessary files.
    """
    if not os.path.isdir(dir):
        print(f"{dir} is not a directory.")
    elif not os.path.isfile(os.path.join(dir, "mesh_rendered.png")):
        print(f"{os.path.join(dir, 'mesh_rendered.png')} does not exist.")
    elif not os.path.isfile(os.path.join(dir, "mask.png")):
        print(f"{os.path.join(dir,'mask.png')} does not exist.")
    elif not os.path.isfile(os.path.join(dir, "keypoints_2D.npy")):
        print(f"{os.path.join(dir, 'keypoints_2D.npy')} does not exist.")
    elif not os.path.isfile(os.path.join(dir, "keypoints_3D.npy")):
        print(f"{os.path.join(dir, 'keypoints_3D.npy')} does not exist.")
    else:
        return True
      
    return False