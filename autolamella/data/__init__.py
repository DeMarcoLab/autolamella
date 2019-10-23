import os
import pickle

import skimage.io

import autolamella.data.mocktypes

data_dir = os.path.abspath(os.path.dirname(__file__))

__all__ = ["adorned_image", "data_dir", "load_image"]


def autoscript_image():
    """Demo image. Also see: mock_adorned_image"""
    filename = os.path.join(data_dir, "autoscript.png")
    image = skimage.io.imread(filename)
    return image


def adorned_image():
    """Open example AdornedImage from Autoscript offline."""
    import autolamella.autoscript

    miccroscope = autolamella.autoscript.initialize("localhost")
    image = miccroscope.imaging.get_image()
    return image


def load_image(filename):
    """Open example image from filename."""
    if filename.endswith("pkl"):
        with open(filename, "rb") as f:
            image = pickle.load(f)
    else:
        image = skimage.io.imread(filename)
    return image


def mock_adorned_image():
    image = autoscript_image()
    return autolamella.data.mocktypes.MockAdornedImage(image=image)
