import pytest
import json
from mock import patch, mock_open
from gwbridge import application


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data=json.dumps(
        {
            "base_url": "https://www.example.com/wp-json",
            "api_version": "wp/v2",
            "file": "README.md",
        }
    ),
)
@patch("os.path.exists")
def test_parse_args(mock_os, mock_file):
    """This test shows that parameters read from a file and passed as an
    argument will be aggregated together, and the command line arguments
    will take priority"
    """
    mock_os.return_value = True
    args = {
        "file": "test.md",
        "client_key": "wwww",
        "client_secret": "xxxx",
        "resource_owner_key": "yyyy",
        "resource_owner_secret": "zzzz",
    }

    config = application.parse_args(**args)
    print(config)

    assert config
    assert config.get("file") == "test.md"
    assert config.get("client_key") == "wwww"
    assert config.get("client_secret") == "xxxx"
    assert config.get("resource_owner_key") == "yyyy"
    assert config.get("resource_owner_secret") == "zzzz"
    assert config.get("base_url") == "https://www.example.com/wp-json"
    assert config.get("api_version") == "wp/v2"
