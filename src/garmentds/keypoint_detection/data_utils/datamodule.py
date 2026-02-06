import os
import copy
from typing import List
from multiprocessing import Manager
from dataclasses import dataclass

import tqdm
import omegaconf
import PIL.Image as Image
import numpy as np
from torch.utils.data import Dataset, DataLoader
import lightning.pytorch as pl

import garmentds.keypoint_detection.utils.learn_utils as learn_utils

@dataclass
class KeypointsDataDict:
    rgb_path: str
    mask_path: str
    keypoints_path: str

class KeypointsDataset(Dataset):
    def __init__(
        self,
        data_list: List[KeypointsDataDict],
        data_index_table: np.ndarray, 
        ds_cfg: omegaconf.DictConfig,
        name="none",
    ) -> None:
        super().__init__()

        if name == "train":
            self._data_index_table = np.array(data_index_table)
        elif name == "valid" or name == "test":
            self._data_index_table = data_index_table.copy()
        else:
            raise ValueError(name)
        self._name = name

        self._data_list = Manager().list(data_list)
        self._ds_cfg = copy.deepcopy(ds_cfg)

        self._size = int(len(self._data_index_table))
        self._dtype = getattr(np, self._ds_cfg.dtype)

    def __len__(self):
        return self._size
    
    def __getitem__(self, index: int):
        # extract data
        data: KeypointsDataDict = self._data_list[self._data_index_table[index]]
        
        #rgb_raw: np.ndarray = np.array(Image.open(data.rgb_path))[...,:3].transpose(2, 0, 1).astype(self._dtype)
        #keypoints_raw: np.ndarray = np.expand_dims(np.load(data.keypoints_path), -2).astype(self._dtype)
        #mask_raw: np.ndarray = np.array(Image.open(data.mask_path))[...,:3].transpose(2, 0, 1).astype(self._dtype)

        rgb_raw: Image.Image = Image.open(data.rgb_path)
        mask_raw: Image.Image = Image.open(data.mask_path)
        keypoints_raw: np.ndarray = np.load(data.keypoints_path)

        cfg_aug = self._ds_cfg.aug
        if self._name == "train":
            rgb_aug, mask_aug, keypoints_aug = learn_utils.data_augmentation(rgb_raw.copy(), mask_raw.copy(), 
                                                    keypoints_raw.copy(), is_training=True, cfg_aug=cfg_aug)
            rgb_tf, mask_tf, keypoints_tf = learn_utils.rotate_and_translate(rgb_aug, mask_aug, keypoints_aug)
        elif self._name == "valid" or self._name == "test":
            rgb_aug, mask_aug, keypoints_aug = learn_utils.data_augmentation(rgb_raw.copy(), mask_raw.copy(), 
                                                    keypoints_raw.copy(), is_training=False, cfg_aug=cfg_aug)
            rgb_tf, mask_tf, keypoints_tf = rgb_aug, mask_aug, keypoints_aug
        else:
            raise ValueError(self._name)

        rgb = rgb_tf.transpose(2, 0, 1).astype(self._dtype)
        mask = mask_tf.transpose(2, 0, 1).astype(self._dtype)
        keypoints = np.expand_dims(keypoints_tf, -2).astype(self._dtype)

        return dict(
            weight=1.0, 
            rgb=rgb,
            mask=mask,
            keypoints=keypoints,

            rgb_raw=np.array(rgb_raw)[...,:3].transpose(2, 0, 1).astype(self._dtype),
            mask_raw=np.array(mask_raw)[...,:3].transpose(2, 0, 1).astype(self._dtype),
            keypoints_raw=keypoints_raw,
            rgb_path=data.rgb_path,
        )


class KeypointsDataModule(pl.LightningDataModule):
    def __init__(self, data_path: List[str], cfg_data: omegaconf.DictConfig):
        super().__init__()

        valid_size_raw: float = cfg_data.common.valid_size
        #make_cfg: omegaconf.DictConfig = cfg_data.make
        ds_cfg: omegaconf.DictConfig = cfg_data.dataset
        self.cfg_data = cfg_data

        pattern = "^completed.txt$"
        df = learn_utils.DataForest(data_path, [pattern])
        node_n_raw = df.get_forest_size(pattern)

        all_data_list: List[KeypointsDataDict] = []

        print("scanning all trajectories ...")
        for idx in tqdm.tqdm(range(node_n_raw)):
            base_dir = os.path.dirname(df.get_item(pattern, idx).file_path)
            #misc_path = os.path.join(base_dir, "misc.json")
            #with open(misc_path, "r") as f_obj:
            #    misc_info: dict = json.load(f_obj)

            rgb_path = os.path.join(base_dir, "mesh_rendered.png")
            mask_path = os.path.join(base_dir, "mask.png")
            keypoints_path = os.path.join(base_dir, "keypoints_2D.npy")
            #coverage = misc_info["coverage"]

            # assemble data
            all_data_list.append(KeypointsDataDict(
                rgb_path=rgb_path,
                mask_path=mask_path,
                keypoints_path=keypoints_path,
                #coverage=coverage,
            ))        

        total_size = len(all_data_list)
        valid_size = learn_utils.parse_size(valid_size_raw, total_size)
        path_idx_permutated = np.random.permutation(total_size)

        #def get_rank(x: np.ndarray): return np.searchsorted(np.sort(x), x, side="right")
        #all_rank = get_rank(np.array([x.coverage for x in all_data_list]))
        #is_keep = ((all_rank / len(all_data_list)) ** float(make_cfg.coverage_weight_exp)) >= np.random.rand(len(all_data_list))
        #is_keep = np.ones(is_keep.shape, dtype = is_keep.dtype)

        self.trds = KeypointsDataset(all_data_list, path_idx_permutated[valid_size:], ds_cfg, name="train")
        self.vlds = KeypointsDataset(all_data_list, path_idx_permutated[:valid_size], ds_cfg, name="valid")
        self.tsds = KeypointsDataset(all_data_list, path_idx_permutated, ds_cfg, name="test")

    def train_dataloader(self):
        if self.trds is None:
            return None

        trdl = DataLoader(
            self.trds, 
            batch_size=self.cfg_data.common.batch_size, 
            num_workers=self.cfg_data.common.num_workers, 
            drop_last=self.cfg_data.common.drop_last, 
            shuffle=True,
        )

        return trdl

    def val_dataloader(self):
        if self.vlds is None:
            return None

        vldl = DataLoader(
            self.vlds, 
            batch_size=self.cfg_data.common.batch_size, 
            num_workers=self.cfg_data.common.num_workers, 
            drop_last=self.cfg_data.common.drop_last, 
            shuffle=False,
        )

        return vldl

    def test_dataloader(self):
        if self.tsds is None:
            return None
        
        tsdl = DataLoader(
            self.tsds, 
            batch_size=self.cfg_data.common.batch_size, 
            num_workers=self.cfg_data.common.num_workers, 
            drop_last=self.cfg_data.common.drop_last, 
            shuffle=False,
        )

        return tsdl

    