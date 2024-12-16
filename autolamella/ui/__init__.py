import logging

try:
    from autolamella.ui import utils
    from autolamella.ui.qt import AutoLamellaUI
    from autolamella.ui.qt import AutoLiftoutUIv2
except ImportError as e:
    logging.info(f"Error importing autolamella.ui: {e}, using dummy instead.")

    class AutoLamellaUI:
        pass
