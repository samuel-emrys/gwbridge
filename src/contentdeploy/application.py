import requests

# import pypandoc
import datetime
from requests_oauthlib import OAuth1
from urllib.parse import parse_qs
import json


def publish(**kwargs):

    oauth = OAuth1(
        client_key=kwargs["client_key"],
        client_secret=kwargs["client_secret"],
        resource_owner_key=kwargs["resource_owner_key"],
        resource_owner_secret=kwargs["resource_owner_secret"],
    )

    if kwargs.get("convert", None):
        pass
        # filename = kwargs.get("file", "").split(".")[0]
        # target_filename = filename + ".html"
        # content = pypandoc.convert_file(kwargs.get("file", ""), 'html', outputfile=target_filename)
    else:
        with open(kwargs["file"], "r") as f:
            content = f.read()

    with open(".metadata.json", "r") as f:
        metadata = json.loads(f.read())

    payload = {
        "date": datetime.datetime.now(),
        "content": content,
        **metadata,
    }

    url = construct_url(**kwargs)
    response = requests.post(url, data=payload, auth=oauth)

    return response.status_code


def construct_url(**kwargs):
    url = "{}/{}/{}".format(
        kwargs.get("base_url"), kwargs.get("api_version"), kwargs.get("endpoint")
    )
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
        resource_owner_Secret=resource_owner_secret,
        verifier=verifier,
    )

    r = requests.post(url=authentication_urls.get("access"), auth=oauth)
    credentials = parse_qs(r.content.decode("utf-8"))
    resource_owner_key = credentials.get("oauth_token")[0]
    resource_owner_secret = credentials.get("oauth_token_secret")[0]

    print("{:25}{}".format("Client key", kwargs["client_key"]))
    print("{:25}{}".format("Client secret", kwargs["client_key"]))
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
