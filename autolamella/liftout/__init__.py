try:
    import importlib.metadata
    __version__ = importlib.metadata.version('liftout')
except ModuleNotFoundError:
    __version__ = "unknown"
