import importlib.util
import os
import sys

from asg_runtime.utils import get_logger

logger = get_logger("load_functions")


def load_user_functions(folder_path=None):
    """
    Load all functions from Python scripts in a user-provided folder.

    Args:
        folder_path (str): Path to the folder containing Python scripts.

    Returns:
        dict: A dictionary of function names and their callable objects.
    """
    logger.debug(f"load_user_functions enter, folder_path={folder_path}")

    if folder_path is None or not os.path.isdir(folder_path):
        raise ValueError(f"The provided path '{folder_path}' is not a valid directory.")

    sys.path.append(folder_path)
    user_functions = {}
    # Iterate over all Python files in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".py"):
            module_name = file_name[:-3]  # Remove the .py extension
            module_path = os.path.join(folder_path, file_name)
            logger.debug(f"trying to load module {module_name} from {module_path}")
            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                logger.debug(f"spec={spec}")
                module = importlib.util.module_from_spec(spec)
                logger.debug(f"module={module}")
                spec.loader.exec_module(module)
            except Exception as e:
                logger.debug(f"failed to load module {module_name} from {module_path}: {e}")
                pass

            # Get all callable functions from the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and not attr_name.startswith("_"):
                    logger.debug(f"adding {attr_name} to user_functions")
                    user_functions[attr_name] = attr

    logger.debug(f"load_user_functions exit with, {len(user_functions)} functions loaded")
    return user_functions
