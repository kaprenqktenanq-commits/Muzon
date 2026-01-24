import shutil
from ..logging import LOGGER


def git():
    if shutil.which("git"):
        LOGGER(__name__).info("Git Client Found [VPS DEPLOYER]")
    else:
        LOGGER(__name__).warning("Git Client Not Found")