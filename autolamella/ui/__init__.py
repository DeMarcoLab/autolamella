import logging

try:
    from autolamella.ui import utils
    from autolamella.ui.qt import AutoLamellaUI as AutoLamellaMainUI
except ImportError as e:
    logging.info(f"Error importing autolamella.ui: {e}, using dummy instead.")

    class AutoLamellaUI:
        pass
