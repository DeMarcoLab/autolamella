import os
import pickle

import skimage.io

import fibsem.conversions
from fibsem.mocktypes import MockAdornedImage

data_dir = os.path.abspath(os.path.dirname(__file__))

__all__ = ['adorned_image',
           'data_dir',
           'embryo',
           'embryo_adorned',
           'embryo_mask',
           'embryo_mask_adorned',
           'load_image',
           ]


def autoscript_image():
    """
    Also see: mock_adorned_image
    """
    filename = os.path.join(data_dir, 'autoscript.png')
    img = skimage.io.imread(filename)
    return img


def adorned_image():
    """Open example AdornedImage from Autoscript offline."""
    import fibsem.autoscript
    mic = fibsem.autoscript.initialize("localhost")
    img = mic.imaging.get_image()
    return img


def embryo():
    """Load the embryo.png file."""
    filename = os.path.join(data_dir, 'embryo.png')
    img = skimage.io.imread(filename)
    return img


def embryo_adorned():
    """Load the embryo.png file as an AdornedImage, pixel size 1e-6 m."""
    img = fibsem.conversions._convert_to_adornedimage(
        fibsem.data.embryo(), pixelsize_x=1e-6, pixelsize_y=1e-6)
    return img


def embryo_mask():
    """Load the embryo_mask.png file."""
    filename = os.path.join(data_dir, 'embryo_mask.png')
    img = skimage.io.imread(filename)
    return img


def embryo_mask_adorned():
    """Load the embryo_mask.png file as an AdornedImage, pixel size 1e-6 m."""
    img = fibsem.conversions._convert_to_adornedimage(
        fibsem.data.embryo_mask(), pixelsize_x=1e-6, pixelsize_y=1e-6)
    return img


def load_image(filename):
    """Open example image from filename."""
    if filename.endswith('pkl'):
        with open(filename, 'rb') as f:
            image = pickle.load(f)
    else:
        image = skimage.io.imread(filename)
    return image


def mock_adorned_image():
    img = autoscript_image()
    return MockAdornedImage(image=img)
