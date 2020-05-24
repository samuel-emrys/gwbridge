import pytest
import json
import os
import pypandoc
from bs4 import BeautifulSoup
from mock import patch, mock_open
from gwbridge import application


@pytest.fixture(scope="module")
def mock_md_file():
    mock_response_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "resources/mock_markdown_file.md"
    )
    with open(mock_response_file, "r") as f:
        mock_response = f.read()

    yield mock_response


@pytest.fixture(scope="module")
def mock_blank_post_response():
    mock_response_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "resources/mock_blank_post.json"
    )
    with open(mock_response_file, "r") as f:
        mock_response = f.read()

    yield mock_response


@pytest.fixture(scope="module")
def mock_md_conversion_result():
    mock_response_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources/mock_md_conversion_result.html",
    )
    with open(mock_response_file, "r") as f:
        mock_response = f.read()

    yield mock_response


@pytest.fixture(scope="module")
def mock_upload_image_response():
    mock_response_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources/mock_upload_image_response.json",
    )
    with open(mock_response_file, "r") as f:
        mock_response = f.read()

    yield mock_response


@pytest.fixture(scope="module")
def mock_get_existing_images_response():
    mock_response_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resources/mock_get_existing_images_response.json",
    )
    with open(mock_response_file, "r") as f:
        mock_response = f.read()

    yield mock_response


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


def test_parse_document(mock_md_file, mock_md_conversion_result):

    config = {
        "base_url": "https://www.example.com/wp-json",
        "api_version": "wp/v2",
    }

    metadata = {
        "id": "",
        "slug": "",
        "status": "draft",
        "author": 1,
        "excerpt": "",
        "featured_media": "",
        "comment_status": "open",
        "ping_status": "closed",
        "format": "standard",
        "meta": "",
        "sticky": "",
        "template": "",
        "categories": "",
        "tags": "",
    }

    payload = application.parse_document(mock_md_file, config, metadata, None)

    assert payload.get("title") == "This is the heading of the post"
    assert payload.get("content") == mock_md_conversion_result


def test_create_blank_post(requests_mock, mock_blank_post_response):

    url = "https://www.example.com/wp-json/wp/v2/posts"
    oauth = None
    requests_mock.post(url, text=mock_blank_post_response)
    post_id = application.create_blank_post(url, oauth)

    assert post_id == 254


def test_get_image_replacement_map(
    requests_mock, mock_md_file, mock_get_existing_images_response
):
    media_url = "https://www.example.com/wp-json/wp/v2/media"
    requests_mock.get(media_url, text=mock_get_existing_images_response)
    html = pypandoc.convert_text(mock_md_file, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")
    post_id = 251

    image_map = application.get_image_replacement_map(soup, media_url, post_id, None)
    image_map_comparison = {
        "251-test.png": {"local_path": "img/test.png", "target_path": None},
        "251-another_image.jpg": {
            "local_path": "img/another_image.jpg",
            "target_path": None,
        },
    }

    assert image_map is not None
    assert image_map == image_map_comparison


@patch(
    "builtins.open", new_callable=mock_open, read_data="",
)
def test_upload_images(mock_file, requests_mock, mock_upload_image_response):

    media_url = "https://www.example.com/wp-json/wp/v2/media"

    requests_mock.post(media_url, text=mock_upload_image_response)
    img_map = {
        "249-test1.png": {
            "local_path": "img/test1.png",
            "target_path": "https://www.example.com/2020/05/24/249-test1.png",
        },
        "250-test2.jpg": {"local_path": "img/test2.jpg", "target_path": None},
    }

    img_map = application.upload_images(img_map, media_url, oauth=None)

    assert (
        img_map.get("249-test1.png").get("target_path")
        == "https://www.example.com/2020/05/24/249-test1.png"
    )
    assert img_map.get("250-test2.jpg").get("target_path") is not None


def test_get_existing_images(requests_mock, mock_get_existing_images_response):

    media_url = "https://www.example.com/wp-json/wp/v2/media"
    requests_mock.get(media_url, text=mock_get_existing_images_response)
    image_urls = application.get_existing_images(media_url, None)

    assert "test.png" in image_urls.keys()
    assert "reverse-proxy.png" in image_urls.keys()
    assert (
        image_urls.get("test.png", None)
        == "https://www.example.com/wp-content/uploads/2020/05/test.png"
    )
    assert (
        image_urls.get("reverse-proxy.png")
        == "https://www.example.com/wp-content/uploads/2020/01/reverse-proxy.png"
    )


def test_extract_title(mock_md_file):
    html = pypandoc.convert_text(mock_md_file, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")
    title = application.extract_title(soup)

    assert title == "This is the heading of the post"
    assert soup is not None
    assert soup.h1 is None


def test_replace_image_links(mock_md_file):
    html = pypandoc.convert_text(mock_md_file, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")
    img_map = {
        "249-test.png": {
            "local_path": "img/test.png",
            "target_path": "https://www.example.com/2020/05/24/249-test.png",
        },
        "249-another_image.jpg": {
            "local_path": "img/another_image.jpg",
            "target_path": "https://www.example.com/2020/05/24/249-another_image.jpg",
        },
    }

    application.replace_image_links(soup, img_map)

    images = [x["src"] for x in soup.find_all("img")]

    assert len(images) == 2
    assert images[0] == "https://www.example.com/2020/05/24/249-test.png"
    assert images[1] == "https://www.example.com/2020/05/24/249-another_image.jpg"


def test_construct_url():
    base_url = "https://www.example.com/wp-json"
    api_version = "wp/v2"
    endpoint = "posts"

    url = application.construct_url(base_url, api_version, endpoint)
    assert url == "https://www.example.com/wp-json/wp/v2/posts"

    url = application.construct_url(base_url, api_version, endpoint, 2)
    assert url == "https://www.example.com/wp-json/wp/v2/posts/2"

    endpoint = "media"
    url = application.construct_url(base_url, api_version, endpoint)
    assert url == "https://www.example.com/wp-json/wp/v2/media"

    url = application.construct_url(base_url, api_version, endpoint, 2)
    assert url == "https://www.example.com/wp-json/wp/v2/media/2"
