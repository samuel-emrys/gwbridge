import requests
import os
import datetime
import pypandoc
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

    document = parse_document(data)

    with open(METADATA_FILE, "r") as f:
        metadata = json.loads(f.read())

    payload = {
        "date": datetime.datetime.now(),
        **document,
        **metadata,
    }

    url = construct_url(**config)
    response = requests.post(url, data=payload, auth=oauth)

    return response.status_code


def parse_document(data):
    html = pypandoc.convert_text(data, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")

    document = extract_title(soup)

    return document


def extract_title(soup):

    title = soup.h1.string
    soup.h1.extract()
    content = soup.prettify(formatter="html5")

    return {"title": title, "content": content}


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


def construct_url(base_url, api_version):
    url = "{}/{}/{}".format(base_url, api_version, "posts")
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
