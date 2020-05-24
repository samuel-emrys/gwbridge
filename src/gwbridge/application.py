import requests
import os
import datetime
import pypandoc
import mimetypes
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs
import json
import shutil
from gwbridge import ROOT_DIR
from gwbridge import METADATA_FILE
from gwbridge import CONFIG_FILE
from bs4 import BeautifulSoup


def publish(**kwargs):

    config = parse_args(**kwargs)

    oauth = OAuth1(
        client_key=config.get("client_key", None),
        client_secret=config.get("client_secret", None),
        resource_owner_key=config.get("resource_owner_key", None),
        resource_owner_secret=config.get("resource_owner_secret", None),
    )

    with open(config.get("file"), "r") as f:
        data = f.read()

    with open(METADATA_FILE, "r") as f:
        metadata = json.loads(f.read())

    if not metadata.get("id", None):
        url = construct_url(**{**config, **metadata})
        metadata["id"] = create_blank_post(url, oauth)

        # Update the repository metadata file with new post ID. This change
        # will need to be committed back to the repository for persistence.
        with open(METADATA_FILE, "w") as f:
            f.write(json.dumps(metadata))

    if metadata.get("id", None):
        document = parse_document(data, config, metadata, oauth)
        payload = {
            "date": datetime.datetime.now(),
            **document,
            **metadata,
        }
        url = construct_url(**{**config, **metadata})
        response = requests.post(url, data=payload, auth=oauth)

    return response.status_code


def create_blank_post(url, oauth):

    payload = {
        "date": datetime.datetime.now(),
        "slug": "",
        "status": "draft",
        "title": "placeholder",
        "content": "placeholder",
        "author": 1,
        "excerpt": None,
        "featured_media": None,
        "comment_status": "open",
        "ping_status": "closed",
        "format": "standard",
        "meta": None,
        "sticky": None,
        "template": None,
        "categories": None,
        "tags": None,
    }

    response = requests.post(url, data=payload, auth=oauth)

    return json.loads(response.text).get("id", None)


def parse_document(data, config, metadata, oauth):
    html = pypandoc.convert_text(data, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)

    media_url = construct_url(**config, endpoint="media")
    img_map = get_image_replacement_map(soup, media_url, metadata.get("id"), oauth)
    img_map = upload_images(img_map, media_url, oauth)

    replace_image_links(soup, img_map)

    content = soup.prettify(formatter="html5")
    document = {"title": title, "content": content}

    return document


def get_image_replacement_map(soup, media_url, post_id, oauth):
    """Create a dictionary associating the current image file path with the URL
    to replace it with, using the filename it will be uploaded as, as the key
    """
    images_in_doc = [x["src"] for x in soup.find_all("img")]
    images_existing = get_existing_images(media_url, oauth)
    image_map = {}

    for img in images_in_doc:
        target_filename = "{}-{}".format(post_id, os.path.basename(img))
        image_map[target_filename] = {
            "local_path": img,
            "target_path": images_existing.get(target_filename, None),
        }

    return image_map


def upload_images(img_map, media_url, oauth):

    for filename, img in img_map.items():
        if img.get("target_path") is None:
            with open(img.get("local_path"), "rb") as f:
                data = f.read()

            headers = {
                "Content-Type": mimetypes.guess_type(img.get("local_path"))[0],
                "Content-Disposition": "attachment; filename={}".format(filename),
            }
            response = requests.post(media_url, data=data, headers=headers, auth=oauth,)
            new_src = json.loads(response.text).get("guid").get("rendered")
            img_map[filename]["target_path"] = new_src

    return img_map


def get_existing_images(media_url, oauth):

    response = requests.get(media_url, auth=oauth)
    images = json.loads(response.text)
    image_urls = {
        os.path.basename(x.get("guid", {}).get("rendered")): x.get("guid", {}).get(
            "rendered"
        )
        for x in images
    }
    return image_urls


def extract_title(soup):

    title = soup.h1.string
    soup.h1.extract()

    return title


def replace_image_links(soup, img_map):

    for filename, img in img_map.items():
        matches = soup.find_all(src=img.get("local_path"))
        for match in matches:
            match["src"] = img.get("target_path")


def parse_args(**kwargs):

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.loads(f.read())
    else:
        config = {}

    for key, value in kwargs.items():
        if value:
            config[key] = value

    return config


def construct_url(base_url, api_version, endpoint, post_id=None):

    if not post_id:
        url = "{}/{}/{}".format(base_url, api_version, endpoint)
    else:
        url = "{}/{}/{}/{}".format(base_url, api_version, endpoint, post_id)
    return url


def authenticate(**kwargs):

    authentication_urls = discover_auth_endpoints(**kwargs)
    oauth = OAuth1(
        client_key=kwargs["client_key"], client_secret=kwargs["client_secret"],
    )
    r = requests.post(url=authentication_urls.get("request"), auth=oauth)
    credentials = parse_qs(r.content.decode("utf-8"))
    resource_owner_key = credentials.get("oauth_token")[0]
    resource_owner_secret = credentials.get("oauth_token_secret")[0]

    print(
        "Authenticate at the following URL to obtain a verification token: {}?oauth_token={}".format(
            authentication_urls.get("authorize"), resource_owner_key
        )
    )
    verifier = input("Enter the verification token: ")

    oauth = OAuth1(
        client_key=kwargs["client_key"],
        client_secret=kwargs["client_secret"],
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )

    r = requests.post(url=authentication_urls.get("access"), auth=oauth)
    credentials = parse_qs(r.content.decode("utf-8"))
    resource_owner_key = credentials.get("oauth_token")[0]
    resource_owner_secret = credentials.get("oauth_token_secret")[0]

    print("{:25}{}".format("Client key", kwargs["client_key"]))
    print("{:25}{}".format("Client secret", kwargs["client_secret"]))
    print("{:25}{}".format("Resource owner key", resource_owner_key))
    print("{:25}{}".format("Resource owner secret", resource_owner_secret))


def discover_auth_endpoints(**kwargs):
    r = requests.get(kwargs.get("base_url"))
    response = json.loads(r.content.decode("utf-8"))

    urls = {
        "request": response.get("authentication", {})
        .get("oauth1", {})
        .get("request", None),
        "authorize": response.get("authentication", {})
        .get("oauth1", {})
        .get("authorize", None),
        "access": response.get("authentication", {})
        .get("oauth1", {})
        .get("access", None),
    }

    return urls


def init(**kwargs):
    default_config_dir = os.path.join(ROOT_DIR, "config")
    deploy_dir = ".deploy"

    try:
        os.makedirs(deploy_dir, exist_ok=False)
    except FileExistsError:
        rewrite = (
            input(
                "This project has already been initialised! Reset your configuration and start again? (y/[n]): "
            )
            or "n"
        )
        if rewrite.lower() in {"n", "no"}:
            exit(0)

    with open(os.path.join(default_config_dir, "config-default.json"), "r") as f:
        config = json.loads(f.read())

    # Prompt user to update configuration settings
    while not config.get("base_url", None):
        config["base_url"] = input(
            "Enter the base URL of the wordpress blog to update (required): "
        )
        if not config.get("base_url"):
            print("You must enter a base URL.")

    config["api_version"] = input(
        "Enter the version of the WPI you wish to use [{}]: ".format(
            config.get("api_version")
        )
    ) or config.get("api_version")

    config["file"] = input(
        "Enter the name of the file to publish [{}]: ".format(config.get("file"))
    ) or config.get("file")

    # Write the updated configuration to the local repository
    with open(os.path.join(deploy_dir, "config.json"), "w") as f:
        f.write(json.dumps(config, indent=4))

    print(
        "Configuration file created at {}".format(
            os.path.join(deploy_dir, "config.json")
        )
    )
    shutil.copy(
        os.path.join(default_config_dir, "metadata-default.json"),
        os.path.join(deploy_dir, "metadata.json"),
    )
    print(
        "Metadata file created at {}".format(os.path.join(deploy_dir, "metadata.json"))
    )
