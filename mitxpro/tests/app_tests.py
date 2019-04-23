"""Application level tests"""
import json


def test_app_json_valid():
    """Verify app.json is parsable and has some necessary keys"""
    with open("app.json") as f:
        config = json.load(f)

    assert isinstance(config, dict)

    for required_key in ["addons", "buildpacks", "env"]:
        assert required_key in config
