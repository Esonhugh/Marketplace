from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("detective-plugin")
except PackageNotFoundError:
    __version__ = "0.4.0"
