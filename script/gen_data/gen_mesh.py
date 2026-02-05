import os
import copy
import json
import argparse
import subprocess
import multiprocessing
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import torch
import taichi as ti
import numpy as np

from garmentds.genmesh.template import garment_dict
from garmentds.genmesh.cfg import generate_cfg
import garmentds.common.utils as utils

mesh_size = "tiny"
# device_memory_GB = 4
skip_check_self_intersection = False

@dataclass
class Cfg:
    cudas: list[int] = field(default_factory=lambda: list(range(0, 8)))
    num_workers: int = 3
    job_ids: list[int] = field(default_factory=lambda: list(range(1000)))
    category: str = "tshirt_sp"
    out_dir: str = f"data/mesh/{category}"

    def get_output_obj_dir(self, i: int):
        return f"{self.out_dir}/{i}"
    
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subprocess", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--category", type=str, default="tshirt_sp")
    parser.add_argument("--mesh_size", type=str, default="tiny")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--num_to_generate", type=int, default=1)
    args = parser.parse_args()
    return args

def run_job(args):
    utils.seed_all(args.seed)
    ti.init(
        arch=ti.cuda, debug=False, random_seed=args.seed, 
        advanced_optimization=True, fast_math=False, offline_cache=True, 
    )

    output_dir = args.output_dir
    garment_name = args.category
    
    while True:
        # generate mesh of random config
        garment = garment_dict[garment_name](**generate_cfg(garment_name, method="random").asdict())
        mesh, info = garment.triangulation(skip_check_self_intersection=skip_check_self_intersection)

        if info["success"]:
            os.makedirs(output_dir, exist_ok=True)
            garment.quick_export(os.path.join(output_dir, "mesh.obj"))
            break
    
class Main:
    def __init__(self, cfg: Cfg):
        self.cfg = copy.deepcopy(cfg)
        self.job_queue: multiprocessing.Queue[Optional[int]] = multiprocessing.Queue(maxsize=8)
    
    def worker(self, worker_id: int):
        os.environ["CUDA_VISIBLE_DEVICES"] = f"{self.cfg.cudas[worker_id % len(self.cfg.cudas)]}"
        while True:
            try:
                job_id = self.job_queue.get(timeout=1)
            except multiprocessing.queues.Empty:
                print(f"[ INFO ] process {os.getpid()}: no hanging jobs, exiting..")
                job_id = None
            if job_id is None:
                break
            seed = job_id
            attemp_cnt = 0
            while True:
                output_obj_dir = self.cfg.get_output_obj_dir(job_id)
                os.makedirs(output_obj_dir, exist_ok=True)
                cmd = (
                    f"python {__file__} --subprocess " + 
                    f"--seed {seed} " + 
                    f"--output_dir {output_obj_dir} " +
                    f"--category {self.cfg.category}"
                )
                with open(os.path.join(output_obj_dir, f"out_{os.getpid()}_{attemp_cnt}.log"), "w") as f:
                    ret = subprocess.run(cmd, shell=True, stdout=f, stderr=f)
                    f.flush()
                print(f"[ INFO ] process {os.getpid()}: finished job {job_id} returncode:{ret.returncode}")
                if ret.returncode == 0:
                    break
                else:
                    seed = np.random.randint(0, 2**31)
                attemp_cnt += 1

    def run(self):
        # init mp
        process_list: list[multiprocessing.Process] = []
        for i in range(self.cfg.num_workers):
            p = multiprocessing.Process(target=self.worker, args=(i,), daemon=True)
            process_list.append(p)
            p.start()

        # append jobs
        for i in self.cfg.job_ids:
            self.job_queue.put(i)

        for p in process_list:
            p.join()
        
        # output
        def generate_success(job_id: int):
            return (Path(self.cfg.get_output_obj_dir(job_id)) / "mesh.obj").exists()
        
        with open(Path(self.cfg.out_dir) / "meta.json", "w") as f:
            success_subdir = [i for i in self.cfg.job_ids if generate_success(i)]
            num_success = len(success_subdir)
            json.dump(dict(
                num_success = num_success,
                success_subdir = success_subdir,
                mesh_size = mesh_size,
            ), f, indent=4)


def main():
    args = get_args()
    global mesh_size
    mesh_size = args.mesh_size

    if args.subprocess:
        run_job(args)
    else:
        cfg = Cfg()
        if os.environ.get("CUDA_VISIBLE_DEVICES") is not None:
            cfg.cudas = [int(i) for i in os.environ["CUDA_VISIBLE_DEVICES"].split(',')]
        else:
            cfg.cudas = list(range(torch.cuda.device_count()))
        
        if args.output_dir is None:
            cfg.out_dir = os.path.join("data/mesh", args.category)
        else:
            cfg.out_dir = args.output_dir

        cfg.category = args.category
        cfg.job_ids = [args.start_idx + i for i in range(args.num_to_generate)]
        
        Main(cfg).run()


if __name__ == '__main__':
    main()