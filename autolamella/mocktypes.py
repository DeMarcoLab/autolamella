class MockPixelSize:
    """Pixel size mock object, has attributes x and y.

    Parameters
    ----------
    x : float, optional.
        Pixel size in x dimension, in meters.
    y : float, optional.
        Pixel size in y dimension, in meters.

    """

    def __init__(self, x=None, y=None):
        if x is None:
            self.x = 6.5104167e-09  # pixel size in meters
        else:
            self.x = x
        if y is None:
            self.y = 6.5104167e-09  # pixel size in meters
        else:
            self.y = y

    def set_pixelsize(self, x, y):
        self.x = x
        self.y = y


class MockAdornedImage:
    """AdornedImage mock object, with attributes for data and pixel size.

    Attributes
    ----------
    image_data : numpy array
        Equivalent to image.data on a real AdornedImage type.
    pixelsize_x : float, optional.
        Pixel size in x dimension, in meters.
    pixelsize_y : float, optional.
        Pixel size in y dimension, in meters.
    """

    def __init__(self, image, pixelsize_x=None, pixelsize_y=None):
        self.data = image
        self.metadata = MockMetadata()
        if pixelsize_x is None:
            self.metadata.binary_result.pixel_size.x = 9.765625e-09  # meters
        else:
            self.metadata.binary_result.pixel_size.x = pixelsize_x
        if pixelsize_y is None:
            self.metadata.binary_result.pixel_size.y = 9.765625e-09  # meters
        else:
            self.metadata.binary_result.pixel_size.y = pixelsize_y

    def set_pixelsize(self, x, y):
        self.metadata.binary_result.pixel_size.x = x
        self.metadata.binary_result.pixel_size.y = y

    def set_imagedata(self, image):
        self.data = image


class MockMetadata:
    """Mock metadata subclass."""

    def __init__(self):
        self.binary_result = MockBinaryResult()


class MockBinaryResult:
    """Mock binary_result subclass."""

    def __init__(self):
        self.pixel_size = MockPixelSize()


class MockStagePosition:
    """Mock stage position.

    ```
    >>> from autoscript_sdb_microscope_client import SdbMicroscopeClient
    >>> microscope = SdbMicroscopeClient().connect("localhost")
    >>> microscope.specimen.stage.current_position
    StagePosition(x=0,y=0,z=0,t=0,r=0)
    ```
    """

    def __init__(self, x=0, y=0, z=0, t=0, r=0):
        self.x = x
        self.y = y
        self.z = z
        self.t = t
        self.r = r
