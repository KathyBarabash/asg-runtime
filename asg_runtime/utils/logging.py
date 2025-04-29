import logging
import os

from rich.logging import RichHandler

from ..models import LogFlavors, LoggingSettings

DEFAULT_LOGGER = "asg_runtime"
_LOGGING_INITIALIZED = False

def setup_logging(settings: LoggingSettings | None = None, name: str | None = DEFAULT_LOGGER):
    """
    Smart setup for logging.
    - If settings are given: honor them.
    - If no settings and running inside pytest or ASG_DEV_LOGGING=true: setup DEV logging.
    - Else: setup safe production logging.
    """
    
    global _LOGGING_INITIALIZED
    # print(f"setup_logging enter for settings={settings}, _LOGGING_INITIALIZED={_LOGGING_INITIALIZED}")
    if _LOGGING_INITIALIZED:
        return

    dev_mode = (
        "PYTEST_CURRENT_TEST" in os.environ
        or os.getenv("ASG_DEV", "").lower() == "true"
    )

    if not settings:
        if dev_mode:
            # Dev or test mode
            settings = LoggingSettings(
                log_level="DEBUG",
                logging_flavor=LogFlavors.rich,
            )
        else:
            # Normal production mode
            settings = LoggingSettings(
                log_level="INFO",
                logging_flavor=LogFlavors.plain,
            )

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handlers = get_flavored_handlers(settings.logging_flavor)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    _LOGGING_INITIALIZED = True

def get_logger(name: str = DEFAULT_LOGGER) -> logging.Logger:
    if name is None:
        # Dynamically infer the caller's module name
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        name = module.__name__ if module else DEFAULT_LOGGER
        
    logger = logging.getLogger(name)
    logger.propagate = True
    return logger

# ------------ private stuff -------------------------

def get_flavored_handlers(flavor):
    handlers = []

    if flavor == LogFlavors.rich:
        handlers.append(RichHandler(rich_tracebacks=True))

    elif flavor == LogFlavors.json:
        handlers.append(get_json_handler())

    elif flavor == LogFlavors.plain:
        handlers.append(get_colored_handler())

    else:
        # should never be here, but just in case
        raise Exception(f"Logging flavor {flavor} is not supported")

    return handlers


def get_colored_handler():
    try:
        from colorama import Fore, Style
        from colorama import init as colorama_init

        colorama_init(autoreset=True)
    except ImportError:
        Fore = Style = type("", (), {"RED": "", "GREEN": "", "BLUE": "", "RESET_ALL": ""})()

    LOG_COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    class ColorFormatter(logging.Formatter):
        def format(self, record):
            color = LOG_COLORS.get(record.levelno, "")
            reset = Style.RESET_ALL
            record.levelname = f"{color}{record.levelname}{reset}"
            record.msg = f"{color}{record.msg}{reset}"
            return super().format(record)

    handler = logging.StreamHandler()
    formatter = ColorFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    return handler


def get_json_handler():
    try:
        from pythonjsonlogger import jsonlogger  # Lazy import
    except ImportError:
        raise ImportError("The 'python-json-logger' package is required for JSON logging format.")

    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter())
    return handler