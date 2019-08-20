import matplotlib.pyplot as plt


def quick_plot(image):
    """Display image with matplotlib.pyplot

    Parameters
    ----------
    image : Adorned image or numpy array
        Input image.

    Returns
    -------
    fig, ax
        Matplotlib figure and axis objects.
    """
    fig, ax = plt.subplots(1)
    display_image = image.data
    height, width = display_image.shape
    try:
        pixelsize_x = image.metadata.binary_result.pixel_size.x
        pixelsize_y = image.metadata.binary_result.pixel_size.y
    except AttributeError:
        extent_kwargs = [-(width / 2), +(width / 2),
                         -(height / 2), +(height / 2)]
        ax.set_xlabel('Distance from origin (pixels)')
    else:
        extent_kwargs = [-(width / 2) * pixelsize_x,
                         +(width / 2) * pixelsize_x,
                         -(height / 2) * pixelsize_y,
                         +(height / 2) * pixelsize_y]
        ax.set_xlabel('Distance from origin (meters) \n'
                      '1 pixel = {} meters'.format(pixelsize_x))
    ax.set_xlim(extent_kwargs[0], extent_kwargs[1])
    ax.set_ylim(extent_kwargs[2], extent_kwargs[3])
    ax.imshow(display_image, cmap='gray', extent=extent_kwargs)
    return fig, ax
