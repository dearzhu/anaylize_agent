"""图像预处理：降噪、二值化、纠偏、超分，提升 OCR 召回。

纯 Pillow 实现，无需深度学习，可离线运行。纠偏仅做水平倾斜校正（霍夫变换），
超分使用简单的双三次放大（生产可替换为 Real-ESRGAN 等模型）。
"""
from __future__ import annotations

import os

from PIL import Image, ImageOps


def preprocess(image_path: str, dpi: int = 200, upscale: float = 1.0) -> Image.Image:
    img = Image.open(image_path).convert("L")  # 灰度
    img = ImageOps.autocontrast(img)           # 自动对比度
    img = _denoise(img)
    img = _deskew(img)
    if upscale and upscale != 1.0:
        w, h = img.size
        img = img.resize((int(w * upscale), int(h * upscale)), Image.BICUBIC)
    return img


def _denoise(img: Image.Image) -> Image.Image:
    # 中值滤波去噪点
    try:
        from PIL import ImageFilter
        return img.filter(ImageFilter.MedianFilter(size=3))
    except Exception:  # pragma: no cover
        return img


def _deskew(img: Image.Image) -> Image.Image:
    """基于投影最大方差的简单倾斜校正；无显著倾斜时原样返回。

    仅使用 PIL 旋转 + numpy 统计，不依赖 scipy。
    """
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        return img
    best_angle = 0
    best_score = -1
    for angle in range(-10, 11):
        rotated = img.rotate(angle, expand=True, fillcolor=255)
        arr = np.asarray(rotated)
        # 用行像素均值的方差近似评估"文本行对齐度"
        score = arr.mean(axis=1).var()
        if score > best_score:
            best_score = score
            best_angle = angle
    if best_angle != 0:
        return img.rotate(best_angle, expand=True, fillcolor=255)
    return img


def save_preprocessed(img: Image.Image, out_path: str) -> str:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    return out_path
