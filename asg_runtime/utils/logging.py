import logging

from rich.logging import RichHandler

from ..models import LogFlavors, LoggingSettings

DEFAULT_LOGGER = "asg_runtime"


def get_logger(name: str = DEFAULT_LOGGER) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = True  # Allow messages to propagate to app root logger
    return logger


def setup_logging(settings: LoggingSettings | None = None, name: str | None = DEFAULT_LOGGER):

    if not settings:
        settings = LoggingSettings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handlers = get_flavored_handlers(settings.logging_flavor)
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    return


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
