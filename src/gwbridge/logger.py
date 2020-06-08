import os
import logging
from gwbridge import PROGRAM_NAME


def configure_logger():
    """ Initialises the program log for use

    :return: A handle to the program log
    :rtype: `logging.Logger`
    """

    program_log = logging.getLogger(PROGRAM_NAME)
    program_log.setLevel(1)

    # Create a log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Define log format
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s.%(module)s: %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Attach console handler to program logger
    program_log.addHandler(console_handler)

    return program_log


def adjust_handler_level(logger, handler, level):
    """Adjusts the logging level for the specified handler

    :param logger: The logger with a handler to be adjusted
    :type logger: `logging.Logger`
    :param handler: The type of handler to adjust. Examples include:
        - `logging.StreamHandler`
        - `logging.FileHandler`
    :type handler: class
    :param level: The logging level to set. Accepts raw integer values and class enums, i.e `logging.INFO`
    :type level: int
    :return: None
    :rtype None
    """

    updated = False
    for h in logger.handlers:
        if isinstance(h, handler):
            try:
                h.setLevel(level)
                updated = True
                logger.info(
                    "{} logging level changed to {}".format(
                        str(handler.__class__.__name__), str(level)
                    )
                )
            except AttributeError as e:
                logger.error("Unable to change logging level: {}".format(e))

    if not updated:
        logger.error(
            "Unable to change logging level: No {} handler is attached to logger".format(
                str(handler.__class__.__name__)
            )
        )


def remove_handler(logger, handler):
    """Removes all types of the specified handler from the specified logger

    :param logger: The logger with a handler to be removed
    :type logger: `logging.Logger`
    :param handler: The type of handler to be removed
    :type handler: `logging.Handler`
    :return: None
    :rtype: None
    """

    for h in logger.handlers:
        if isinstance(h, handler):
            logger.removeHandler(h)
