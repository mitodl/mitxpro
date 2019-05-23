"""Tests for environment variable parsing functions"""
import pytest

from mitxpro import envs


FAKE_ENVIRONS = {
    "true": "True",
    "false": "False",
    "positive": "123",
    "negative": "-456",
    "zero": "0",
    "float": "1.1",
    "expression": "123-456",
    "none": "None",
    "string": "a b c d e f g",
    "list_of_int": "[3,4,5]",
    "list_of_str": '["x", "y", \'z\']',
}


@pytest.fixture(autouse=True)
def clean_env(mocker):
    """Clean the configured environment variables before a test"""
    mocker.patch.dict("os.environ", FAKE_ENVIRONS, clear=True)
    envs.env.reload()


def test_get_any():
    """
    get_any should parse an environment variable into a bool, int, or a string
    """
    expected = {
        "true": True,
        "false": False,
        "positive": 123,
        "negative": -456,
        "zero": 0,
        "float": "1.1",
        "expression": "123-456",
        "none": "None",
        "string": "a b c d e f g",
        "list_of_int": "[3,4,5]",
        "list_of_str": '["x", "y", \'z\']',
    }
    for key, value in expected.items():
        assert envs.get_any(key, "default") == value
    assert envs.get_any("missing", "default") == "default"


def test_get_string():
    """
    get_string should get the string from the environment variable
    """
    for key, value in FAKE_ENVIRONS.items():
        assert envs.get_string(key, "default") == value
    assert envs.get_string("missing", "default") == "default"


def test_get_int():
    """
    get_int should get the int from the environment variable, or raise an exception if it's not parseable as an int
    """
    assert envs.get_int("positive", 1234) == 123
    assert envs.get_int("negative", 1234) == -456
    assert envs.get_int("zero", 1234) == 0

    for key, value in FAKE_ENVIRONS.items():
        if key not in ("positive", "negative", "zero"):
            with pytest.raises(envs.EnvironmentVariableParseException) as ex:
                envs.get_int(key, 1234)
            assert ex.value.args[
                0
            ] == "Expected value in {key}={value} to be an int".format(
                key=key, value=value
            )

    assert envs.get_int("missing", 1_234_567_890) == 1_234_567_890


def test_get_bool():
    """
    get_bool should get the bool from the environment variable, or raise an exception if it's not parseable as a bool
    """
    assert envs.get_bool("true", 1234) is True
    assert envs.get_bool("false", 1234) is False

    for key, value in FAKE_ENVIRONS.items():
        if key not in ("true", "false"):
            with pytest.raises(envs.EnvironmentVariableParseException) as ex:
                envs.get_bool(key, 1234)
            assert ex.value.args[
                0
            ] == "Expected value in {key}={value} to be a boolean".format(
                key=key, value=value
            )

    assert envs.get_bool("missing_true", True) is True
    assert envs.get_bool("missing_false", False) is False
