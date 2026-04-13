from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in dev for convenience
ALLOWED_HOSTS = ["*"]

# Show SQL queries in dev shell
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
