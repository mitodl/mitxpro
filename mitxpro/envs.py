"""Functions reading and parsing environment variables"""
import json
import os
from collections import namedtuple
from datetime import timedelta
from functools import wraps

from celery.schedules import schedule
from django.core.exceptions import ImproperlyConfigured


class EnvironmentVariableParseException(ImproperlyConfigured):
    """Environment variable was not parsed correctly"""


EnvVariable = namedtuple(
    "EnvVariable",
    [
        "name",
        "default",
        "description",
        "required",
        "dev_only",
        "value",
        "write_app_json",
    ],
)


def var_parser(parser_func):
    """
    Decorator to create a var parser func

    Args:
        parser_func (callable):
            a function that takes one argument which will be the raw value and
            returns a parsed value or raises an error
    """

    # pylint: disable=too-many-arguments
    @wraps(parser_func)
    def wrapper(
        self,
        name,
        default,
        description=None,
        required=False,
        dev_only=False,
        write_app_json=True,
    ):
        """
        Get an environment variable

        Args:
            name (str): An environment variable name
            default (str): The default value to use if the environment variable doesn't exist.
            description (str): The description of how this variable is used
            required (bool): Whether this variable is required at runtime
            dev_only (bool): Whether this variable is only applicable in dev environments
            write_app_json (bool): Whether this variable is written to app.json

        Raises:
            ValueError:
                If the environment variable args are incorrect

        Returns:
            any:
                The raw environment variable value
        """
        configured_envs = self._configured_vars  # pylint: disable=protected-access
        environ = self._env  # pylint: disable=protected-access

        if name in configured_envs:
            raise ValueError(f"Environment variable '{name}' was used more than once")

        value = environ.get(name, default)

        # attempt to parse the value before we store it in configured_envs
        # this ensures that get_any works since we don't store the various parse attempts until one succeeds
        value = parser_func(name, value, default)

        configured_envs[name] = EnvVariable(
            name, default, description, required, dev_only, value, write_app_json
        )

        return value

    return wrapper


def parse_bool(name, value, default):  # pylint: disable=unused-argument
    """
    Attempts to parse a bool

    Arguments:
        value (str or bool):
            the value as either an unparsed string or a bool in case of a default value

    Raises:
        EnvironmentVariableParseException:
            raised if the value wasn't parsable

    Returns:
        bool:
            parsed value
    """

    if isinstance(value, bool):
        return value

    parsed_value = value.lower()
    if parsed_value == "true":
        return True
    elif parsed_value == "false":
        return False

    raise EnvironmentVariableParseException(
        "Expected value in {name}={value} to be a boolean".format(
            name=name, value=value
        )
    )


def parse_int(name, value, default):
    """
    Attempts to parse a int

    Arguments:
        value (str or int):
            the value as either an unparsed string or an int in case of a default value

    Raises:
        EnvironmentVariableParseException:
            raised if the value wasn't parsable

    Returns:
        int:
            parsed value
    """

    if isinstance(value, int) or (value is None and default is None):
        return value

    try:
        parsed_value = int(value)
    except ValueError as ex:
        raise EnvironmentVariableParseException(
            "Expected value in {name}={value} to be an int".format(
                name=name, value=value
            )
        ) from ex

    return parsed_value


def parse_str(name, value, default):  # pylint: disable=unused-argument
    """
    Parses a str (identity function)

    Arguments:
        value (str):
            the value as either a str

    Returns:
        str:
            parsed value
    """
    return value


def parse_any(name, value, default):
    """
    Attempts to parse an environment variable as a bool, int, or a string

    Arguments:
        value (bool or int or str):
            the value as either an unparsed string or a default value

    Raises:
        EnvironmentVariableParseException:
            raised if the value wasn't parsable at all

    Returns:
        int or bool or str:
            the environment variable value parsed as a bool, int, or a string
    """
    # attempt to parse the var in this order of parsers
    for parser in [parse_bool, parse_int, parse_str]:
        try:
            return parser(name, value, default)
        except EnvironmentVariableParseException:
            continue


class EnvParser:
    """Stateful tracker for environment variable parsing"""

    def __init__(self):
        self.reload()

    def reload(self):
        """Reloads the environment"""
        self._env = dict(os.environ)
        self._configured_vars = {}

    def validate(self):
        """
        Validates the current configuration

        Raises:
            ImproperlyConfigured:
                If any settings are missing
        """
        missing_settings = []

        for env_var in self._configured_vars.values():
            if env_var.required and env_var.value in (None, ""):
                missing_settings.append(env_var.name)

        if missing_settings:
            raise ImproperlyConfigured(
                "The following settings are missing: {}".format(
                    ", ".join(missing_settings)
                )
            )

    def list_environment_vars(self):
        """
        Get the list of EnvVariables

        Returns:
            list of EnvVariable:
                the list of available env vars
        """
        return self._configured_vars.values()

    get_string = var_parser(parse_str)
    get_bool = var_parser(parse_bool)
    get_int = var_parser(parse_int)
    get_any = var_parser(parse_any)


env = EnvParser()

# methods below are our exported module interface
get_string = env.get_string
get_int = env.get_int
get_bool = env.get_bool
get_any = env.get_any
validate = env.validate
list_environment_vars = env.list_environment_vars


def generate_app_json():
    """
    Generate a new app.json data structure in-memory using app.base.json and settings.py

    Returns:
        dict:
            object that can be serialized to JSON for app.json
    """
    with open("app.base.json") as app_template_json:
        config = json.load(app_template_json)

    for env_var in list_environment_vars():
        if env_var.dev_only or not env_var.write_app_json:
            continue

        if env_var.name not in config["env"]:
            config["env"][env_var.name] = {}

        config["env"][env_var.name].update(
            {"description": env_var.description, "required": env_var.required}
        )

    return config


class OffsettingSchedule(schedule):
    """
    Specialized celery schedule class that allows for easy definition of an offset time for a
    scheduled task (e.g.: the task should run every 30, but it should start after a 15 second offset)

    Inspired by this SO answer: https://stackoverflow.com/a/41700962
    """

    def __init__(self, run_every=None, offset=None):
        self._run_every = run_every
        self._offset = offset
        self._apply_offset = offset is not None
        super().__init__(run_every=self._run_every + (offset or timedelta(seconds=0)))

    def is_due(self, last_run_at):
        retval = super().is_due(last_run_at)
        if self._apply_offset is not None and retval.is_due:
            self._apply_offset = False
            self.run_every = self._run_every
            retval = super().is_due(last_run_at)
        return retval

    def __reduce__(self):
        return self.__class__, (self._run_every, self._offset)
