from __future__ import annotations

import os
import pathlib
from collections import Counter, defaultdict
from copy import deepcopy
from typing import List, Optional, Dict, Tuple, Union, Sequence

import albumentations as A
import numpy as np
from keras.datasets import cifar10, mnist

from .image import load_image


def one_hot(label: int, num_classes: int) -> np.ndarray:
    label_one_hot = np.zeros(num_classes)
    label_one_hot[label] = 1
    return label_one_hot


def stratified_sampling(
        labels: Sequence, sample_size: Union[int, float]
) -> List[int]:
    if isinstance(sample_size, float) and 0 < sample_size > 1:
        raise ValueError('sample_size must be between zero and one if float!')

    indices = defaultdict(list)
    for i, label in enumerate(labels):
        indices[label].append(i)

    counter = Counter(labels)

    sample_percentage = sample_size
    if isinstance(sample_size, int):
        sample_percentage /= len(labels)

    for label in counter:
        counter[label] *= sample_percentage
        counter[label] = int(np.ceil(counter[label]))

    if isinstance(sample_size, int):
        while sum(counter.values()) > sample_size:
            counter[max(counter, key=counter.get)] -= 1

    sample = []
    for label, index in indices.items():
        sample.extend(np.random.choice(index, size=counter[label], replace=False))
    return sample


class ImageDataset:
    def __init__(self, transform: Optional[A.BasicTransform] = None) -> None:
        self.transform = transform
        self._build_dataset()
        self._build_classes()

    def __len__(self) -> int:
        return len(self.data["label"])

    def __getitem__(self, index: int) -> Tuple[np.ndarray, np.ndarray]:
        if index >= len(self):
            raise IndexError("Index is out of range!")

        image = self.data["image"][index]
        label = self.data["label"][index]

        if isinstance(image, str):
            image = load_image(image)

        if isinstance(label, str):
            label = self.cls2idx[label]

        if self.transform is not None:
            image = self.transform(image=image)["image"]

        label = one_hot(label, self.num_classes)

        return image, label

    @property
    def num_classes(self) -> int:
        return len(self.classes)

    def _build_dataset(self) -> None:
        self.data = dict(defaultdict(list))

    def _build_classes(self) -> None:
        if isinstance(self.data["label"], np.ndarray):
            self.data["label"] = self.data["label"].flatten()
        self.classes = sorted(list(set(self.data["label"])))
        self.cls2idx = {v: k for k, v in enumerate(self.classes)}

    def class_distribution(self, normalize: Optional[bool] = True) -> Dict[str, int]:
        count = dict(Counter(self.data["label"]))
        if normalize:
            count = {c: n / len(self) for c, n in count.items()}
        return {c: count[c] for c in sorted(count)}

    def sample(self, sample_size: Union[int, float]) -> ImageDataset:
        dataset = deepcopy(self)
        index = stratified_sampling(self.data["label"], sample_size)
        for key, value in dataset.data.items():
            dataset.data[key] = value[index]
        return dataset


class ImageFolder(ImageDataset):
    def __init__(self, root: str, transform: Optional[A.BasicTransform] = None) -> None:
        self.root = root
        super().__init__(transform)

    def _build_dataset(self) -> None:
        self.data = defaultdict(list)
        for path_cls in pathlib.Path(self.root).glob("*"):
            for path_img in path_cls.glob("*"):
                self.data["image"].append(os.path.normpath(path_img))
                self.data["label"].append(os.path.basename(path_cls))


class MNIST(ImageDataset):
    def __init__(self, train: Optional[bool] = True, transform: Optional[A.BasicTransform] = None) -> None:
        self.train = train
        super().__init__(transform)

    def _build_dataset(self) -> None:
        subset = 0 if self.train else 1
        self.data = defaultdict(list)
        image, label = mnist.load_data()[subset]
        self.data["image"] = np.expand_dims(image, axis=-1)
        self.data["label"] = label


class CIFAR10(ImageDataset):
    def __init__(self, train: Optional[bool] = True, transform: Optional[A.BasicTransform] = None) -> None:
        self.train = train
        super().__init__(transform)

    def _build_dataset(self) -> None:
        subset = 0 if self.train else 1
        self.data = defaultdict(list)
        image, label = cifar10.load_data()[subset]
        self.data["image"] = image
        self.data["label"] = label
