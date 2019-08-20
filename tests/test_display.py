import pytest
import matplotlib.pyplot as plt

import lamella.data
import lamella.display


@pytest.mark.mpl_image_compare
def test_quick_plot():
    image = lamella.data.mock_adorned_image()
    fig, ax = lamella.display.quick_plot(image)
    return fig
