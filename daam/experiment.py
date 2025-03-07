from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

import PIL.Image
import numpy as np
import torch

from .evaluate import load_mask


__all__ = ['GenerationExperiment', 'COCO80_LABELS', 'COCOSTUFF27_LABELS']


COCO80_LABELS: List[str] = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
    'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]


UNUSED_LABELS: List[str] = [f'__unused_{i}__' for i in range(1, 200)]


COCOSTUFF27_LABELS: List[str] = [
    'electronic', 'appliance', 'food', 'furniture', 'indoor', 'kitchen', 'accessory', 'animal', 'outdoor', 'person',
    'sports', 'vehicle', 'ceiling', 'floor', 'food', 'furniture', 'rawmaterial', 'textile', 'wall', 'window',
    'building', 'ground', 'plant', 'sky', 'solid', 'structural', 'water'
]


COCO80_TO_27 = {
    'bicycle': 'vehicle', 'car': 'vehicle', 'motorcycle': 'vehicle', 'airplane': 'vehicle', 'bus': 'vehicle',
    'train': 'vehicle', 'truck': 'vehicle', 'boat': 'vehicle', 'traffic light': 'accessory', 'fire hydrant': 'accessory',
    'stop sign': 'accessory', 'parking meter': 'accessory', 'bench': 'furniture', 'bird': 'animal', 'cat': 'animal',
    'dog': 'animal', 'horse': 'animal', 'sheep': 'animal', 'cow': 'animal', 'elephant': 'animal', 'bear': 'animal',
    'zebra': 'animal', 'giraffe': 'animal', 'backpack': 'accessory', 'umbrella': 'accessory', 'handbag': 'accessory',
    'tie': 'accessory', 'suitcase': 'accessory', 'frisbee': 'sports', 'skis': 'sports', 'snowboard': 'sports',
    'sports ball': 'sports', 'kite': 'sports', 'baseball bat': 'sports', 'baseball glove': 'sports',
    'skateboard': 'sports', 'surfboard': 'sports', 'tennis racket': 'sports', 'bottle': 'food', 'wine glass': 'food',
    'cup': 'food', 'fork': 'food', 'knife': 'food', 'spoon': 'food', 'bowl': 'food', 'banana': 'food', 'apple': 'food',
    'sandwich': 'food', 'orange': 'food', 'broccoli': 'food', 'carrot': 'food', 'hot dog': 'food', 'pizza': 'food',
    'donut': 'food', 'cake': 'food', 'chair': 'furniture', 'couch': 'furniture', 'potted plant': 'plant',
    'bed': 'furniture', 'dining table': 'furniture', 'toilet': 'furniture', 'tv': 'electronic', 'laptop': 'electronic',
    'mouse': 'electronic', 'remote': 'electronic', 'keyboard': 'electronic', 'cell phone': 'electronic',
    'microwave': 'appliance', 'oven': 'appliance', 'toaster': 'appliance', 'sink': 'appliance',
    'refrigerator': 'appliance', 'book': 'indoor', 'clock': 'indoor', 'vase': 'indoor', 'scissors': 'indoor',
    'teddy bear': 'indoor', 'hair drier': 'indoor', 'toothbrush': 'indoor'
}


def _add_mask(masks: Dict[str, torch.Tensor], word: str, mask: torch.Tensor, simplify80: bool = False) -> Dict[str, torch.Tensor]:
    if simplify80:
        word = COCO80_TO_27.get(word, word)

    if word in masks:
        masks[word] = masks[word.lower()] + mask
        masks[word].clamp_(0, 1)
    else:
        masks[word] = mask

    return masks


@dataclass
class GenerationExperiment:
    """Class to hold experiment parameters. Pickleable."""
    id: str
    image: PIL.Image.Image
    global_heat_map: torch.Tensor
    seed: int
    prompt: str

    path: Optional[Path] = None
    truth_masks: Optional[Dict[str, torch.Tensor]] = None
    prediction_masks: Optional[Dict[str, torch.Tensor]] = None
    annotations: Optional[Dict[str, Any]] = None

    def save(self, path: str = None):
        if path is None:
            path = self.path
        else:
            path = Path(path) / self.id

        path.mkdir(parents=True, exist_ok=True)
        torch.save(self, path / 'generation.pt')
        self.image.save(path / 'output.png')

        with (path / 'prompt.txt').open('w') as f:
            f.write(self.prompt)

        with (path / 'seed.txt').open('w') as f:
            f.write(str(self.seed))

        if self.truth_masks is not None:
            for name, mask in self.truth_masks.items():
                im = PIL.Image.fromarray((mask * 255).unsqueeze(-1).expand(-1, -1, 4).byte().numpy())
                im.save(path / f'{name.lower()}.gt.png')

        self.save_annotations()

    def save_annotations(self, path: Path = None):
        if path is None:
            path = self.path

        if self.annotations is not None:
            with (path / 'annotations.json').open('w') as f:
                json.dump(self.annotations, f)

    def _load_truth_masks(self, simplify80: bool = False) -> Dict[str, torch.Tensor]:
        masks = {}

        for mask_path in self.path.glob('*.gt.png'):
            word = mask_path.name.split('.gt.png')[0].lower()
            mask = load_mask(str(mask_path))
            _add_mask(masks, word, mask, simplify80)

        return masks

    def _load_pred_masks(self, pred_prefix, composite=False, simplify80=False, vocab=None):
        # type: (str, bool, bool, List[str] | None) -> Dict[str, torch.Tensor]
        masks = {}

        if vocab is None:
            vocab = UNUSED_LABELS

        if composite:
            im = PIL.Image.open(self.path / f'composite.{pred_prefix}.pred.png')
            im = np.array(im)

            for mask_idx in np.unique(im):
                mask = torch.from_numpy((im == mask_idx).astype(np.float32))
                _add_mask(masks, vocab[mask_idx], mask, simplify80)
        else:
            for mask_path in self.path.glob(f'*.{pred_prefix}.pred.png'):
                mask = load_mask(str(mask_path))
                word = mask_path.name.split(f'.{pred_prefix}.pred')[0].lower()
                _add_mask(masks, word, mask, simplify80)

        return masks

    def save_prediction_mask(self, mask: torch.Tensor, word: str, name: str):
        im = PIL.Image.fromarray((mask * 255).unsqueeze(-1).expand(-1, -1, 4).byte().numpy())
        im.save(self.path / f'{word.lower()}.{name}.pred.png')

    @staticmethod
    def contains_truth_mask(path: str | Path, prompt_id: str = None) -> bool:
        if prompt_id is None:
            return any(Path(path).glob('*.gt.png'))
        else:
            return any((Path(path) / prompt_id).glob('*.gt.png'))

    @staticmethod
    def has_annotations(path: str | Path) -> bool:
        return Path(path).joinpath('annotations.json').exists()

    @staticmethod
    def has_experiment(path: str | Path, prompt_id: str) -> bool:
        return (Path(path) / prompt_id / 'generation.pt').exists()

    def _try_load_annotations(self):
        if not (self.path / 'annotations.json').exists():
            return None

        return json.load((self.path / 'annotations.json').open())

    def annotate(self, key: str, value: Any) -> 'GenerationExperiment':
        if self.annotations is None:
            self.annotations = {}

        self.annotations[key] = value

        return self

    @classmethod
    def load(cls, path, pred_prefix='daam', composite=False, simplify80=False, vocab=None):
        # type: (str, str, bool, bool, List[str] | None) -> GenerationExperiment
        path = Path(path)
        exp = torch.load(path / 'generation.pt')
        exp.path = path
        exp.truth_masks = exp._load_truth_masks(simplify80=simplify80)
        exp.prediction_masks = exp._load_pred_masks(pred_prefix, composite=composite, simplify80=simplify80, vocab=vocab)
        exp.annotations = exp._try_load_annotations()

        return exp
