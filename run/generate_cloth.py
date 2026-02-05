import os
import sys
import pathlib

def setup_env_var():
    # determine base dir
    base_dir = os.path.abspath(__file__)
    base_dir = '/'.join(base_dir.split('/')[:-2])

    # pyflex
    if os.environ.get("FOLDNET_BASE_DIR") is None:
        os.environ["FOLDNET_BASE_DIR"] = base_dir
    os.environ["PYFLEX_PATH"] = os.path.join(base_dir, "src/pyflex/PyFlex")
    sys.path.append(os.path.join(base_dir, "src/pyflex/PyFlex/bindings/build"))

    # openai
    # if os.environ["OPENAI_API_KEY"] is None:
    #     os.environ["OPENAI_API_KEY"] = "your_api_key_here"
    # os.environ["http_proxy"] = "http://127.0.0.1:17891"
    # os.environ["https_proxy"] = "http://127.0.0.1:17891"

setup_env_var()

import hydra
import omegaconf
import taichi as ti

import garmentds.common.utils as utils
from garmentds.gentexture import factory

@hydra.main(config_path="../config/run", config_name=pathlib.Path(__file__).stem, version_base='1.3')
def main(cfg: omegaconf.DictConfig):
    # setup
    utils.init_omegaconf()
    omegaconf.OmegaConf.resolve(cfg)
    cfg = utils.resolve_overwrite(cfg)
    omegaconf.OmegaConf.save(cfg, os.path.join(os.getcwd(), ".hydra", "resolved.yaml"))

    ti_cfg = cfg["setup"]["taichi"]
    ti.init(
        arch=ti.cuda, debug=ti_cfg["debug"], random_seed=ti_cfg["seed"], 
        advanced_optimization=ti_cfg["advanced_optimization"], 
        fast_math=ti_cfg["fast_math"], offline_cache=ti_cfg["offline_cache"]
    )

    factory.make_cloth(**cfg["garment"])


if __name__ == "__main__":
    main()