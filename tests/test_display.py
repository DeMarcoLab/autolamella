import pytest

import autolamella.data
import autolamella.display


@pytest.mark.mpl_image_compare(tolerance=3.1)
def test_quick_plot():
    image = autolamella.data.mock_adorned_image()
    fig, ax = autolamella.display.quick_plot(image)
    return fig
