"""
Plugin Auto-Discovery System

Automatically discovers and loads translation provider plugins from:
1. Built-in providers in subtitle_translator.providers package
2. User-provided plugins from external directories
"""

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def discover_plugins(package_name: str = "subtitle_translator.providers") -> List[str]:
    """
    Auto-discover and import all plugin modules from package

    Recursively walks through the package directory and imports all
    Python modules. Plugins register themselves via decorators on import.

    Args:
        package_name: Dotted package name to search for plugins

    Returns:
        List of imported module names
    """
    discovered = []

    try:
        # Import the package
        package = importlib.import_module(package_name)

        # Get package path
        if hasattr(package, '__path__'):
            package_paths = package.__path__
        else:
            # Single module, not a package
            return [package_name]

        # Walk through all subdirectories and modules
        for importer, modname, ispkg in pkgutil.walk_packages(
            path=package_paths,
            prefix=f"{package_name}."
        ):
            try:
                # Import the module (triggers decorator registration)
                importlib.import_module(modname)
                discovered.append(modname)
                logger.debug(f"Discovered plugin module: {modname}")

            except Exception as e:
                # Log but don't fail if a plugin can't load
                logger.warning(f"Could not load plugin module '{modname}': {e}")

    except ImportError as e:
        logger.error(f"Could not import package '{package_name}': {e}")

    logger.info(f"Discovered {len(discovered)} plugin modules from {package_name}")
    return discovered


def load_user_plugins(plugins_dir: Path) -> List[str]:
    """
    Load user-provided plugins from external directory

    Args:
        plugins_dir: Directory containing user plugin files

    Returns:
        List of loaded module names
    """
    loaded = []

    if not plugins_dir.exists():
        logger.debug(f"User plugins directory does not exist: {plugins_dir}")
        return loaded

    # Add directory to Python path temporarily
    if str(plugins_dir) not in sys.path:
        sys.path.insert(0, str(plugins_dir))
        logger.debug(f"Added to sys.path: {plugins_dir}")

    # Find and import all .py files
    for plugin_file in plugins_dir.glob("*.py"):
        module_name = plugin_file.stem

        # Skip __init__ and private modules
        if module_name.startswith('_'):
            continue

        try:
            # Import the module (triggers decorator registration)
            importlib.import_module(module_name)
            loaded.append(module_name)
            logger.info(f"Loaded user plugin: {module_name}")

        except Exception as e:
            logger.error(f"Could not load user plugin '{module_name}': {e}")

    logger.info(f"Loaded {len(loaded)} user plugins from {plugins_dir}")
    return loaded


def load_all_plugins(user_plugins_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """
    Load all plugins: built-in and user-provided

    Args:
        user_plugins_dir: Optional directory for user plugins

    Returns:
        Dict with 'builtin' and 'user' plugin lists
    """
    result = {
        'builtin': [],
        'user': []
    }

    # Load built-in plugins
    try:
        result['builtin'] = discover_plugins("subtitle_translator.providers")
    except Exception as e:
        logger.warning(f"Could not load built-in plugins: {e}")

    # Load user plugins if directory provided
    if user_plugins_dir:
        result['user'] = load_user_plugins(user_plugins_dir)

    total_plugins = len(result['builtin']) + len(result['user'])
    logger.info(f"Plugin loading complete: {total_plugins} total plugins loaded")

    return result