import requests
import os
import datetime
import pypandoc
import mimetypes
import json
import shutil
import logging
import textwrap
from bs4 import BeautifulSoup
from urllib.parse import parse_qs
from requests_oauthlib import OAuth1
from gwbridge import ROOT_DIR
from gwbridge import CONFIG_FILE
from gwbridge import METADATA_FILE
from gwbridge import logger
from gwbridge import program_log


def publish(ctx, **kwargs):
    """Publish a markdown file to a wordpress blog
    """

    # Set logging verbosity
    if ctx.obj.get("verbosity") or ctx.obj.get("verbosity") == 0:
        # Default console verbosity will be INFO level logging
        if ctx.obj.get("verbosity") == 0:
            logger.remove_handler(program_log, logging.StreamHandler)
        else:
            logger.adjust_handler_level(
                program_log, logging.StreamHandler, logging.DEBUG
            )

    program_log.debug("Context values: {}".format(str(ctx.obj)))

    # Consolidate cli args with config file
    config = parse_args(**kwargs)

    program_log.debug("Config: {}".format(str(config)))

    oauth = OAuth1(
        client_key=config.get("client_key", None),
        client_secret=config.get("client_secret", None),
        resource_owner_key=config.get("resource_owner_key", None),
        resource_owner_secret=config.get("resource_owner_secret", None),
        signature_type="auth_header",
    )
    program_log.debug("OAuth object built")

    program_log.debug("Reading data from {}".format(config.get("file")))
    # Read markdown file contents
    with open(config.get("file"), "r") as f:
        data = f.read()

    program_log.debug("Loading metadata")
    with open(METADATA_FILE, "r") as f:
        metadata = json.loads(f.read())

    if not metadata.get("id", None):
        program_log.info("No Post ID found. Creating a new post.")
        url = construct_url(
            base_url=config.get("base_url"),
            api_version=config.get("api_version"),
            endpoint="posts",
        )
        program_log.debug("Constructing URL for /posts endpoint: {}".format(url))

        # Create a blank post to obtain a post id
        metadata["id"] = create_blank_post(url, oauth)
        program_log.debug("New post id: {}".format(str(metadata.get("id"))))

        # Update the repository metadata file with new post ID. This change
        # will need to be committed back to the repository for persistence.
        program_log.debug("Updating local metadata file with new post id")
        with open(METADATA_FILE, "w") as f:
            f.write(json.dumps(metadata, indent=4))

    if metadata.get("id", None):
        program_log.info("Publishing content")

        # Transform content into a form appropriate for wordpress
        document = parse_document(data, config, metadata, oauth)
        payload = {
            "date": None,
            **document,
            **metadata,
        }
        program_log.debug("Payload: \n{}".format(payload))
        url = construct_url(
            base_url=config.get("base_url"),
            api_version=config.get("api_version"),
            endpoint="posts",
            post_id=metadata.get("id"),
        )
        program_log.debug("Constructed URL for post update: {}".format(url))

        # Manually set the header to ensure that the body of the request is not used to sign it
        headers = {"Content-Type": "application/json"}
        # Push new blog content
        response = requests.post(
            url, data=json.dumps(payload), headers=headers, auth=oauth
        )
        program_log.debug(
            textwrap.dedent(
                """
            ---------------- request ----------------
            {req.method} {req.url}
            {reqhdrs}

            {req.body}
            ---------------- response ----------------
            {res.status_code} {res.reason} {res.url}
            {reshdrs}

            {res.text}

        """
            ).format(
                req=response.request,
                res=response,
                reqhdrs=format_headers(response.request.headers),
                reshdrs=format_headers(response.headers),
            )
        )

        # If blog successfully published
        if response.status_code == 200:
            response_dict = json.loads(response.text)

            # Update relevant metadata from response
            with open(METADATA_FILE, "w") as f:
                f.write(json.dumps(metadata, indent=4))

            program_log.info(
                "Post successfully published, and is available at {}".format(
                    response_dict.get("guid").get("rendered")
                )
            )
        else:
            program_log.error(
                "Something went wrong. The server returned status code: {}: {}".format(
                    response.status_code, response.text
                )
            )
            program_log.debug(
                textwrap.dedent(
                    """
                ---------------- request ----------------
                {req.method} {req.url}
                {reqhdrs}

                {req.body}
                ---------------- response ----------------
                {res.status_code} {res.reason} {res.url}
                {reshdrs}

                {res.text}

            """
                ).format(
                    req=response.request,
                    res=response,
                    reqhdrs=format_headers(response.request.headers),
                    reshdrs=format_headers(response.headers),
                )
            )
    else:
        program_log.error("Something went wrong. Content not updated")

    return response.status_code


def create_blank_post(url, oauth):
    """ Create a blank post on the wordpress blog. This is executed to obtain
    a post id with which images can be uploaded, and the post can be update
    with correct content
    """

    payload = {
        "date": datetime.datetime.now(),
        "status": "draft",
        "title": "placeholder",
        "content": "placeholder",
        "author": 1,
        "comment_status": "open",
        "ping_status": "closed",
        "format": "standard",
    }

    response = requests.post(url, data=payload, auth=oauth)

    program_log.debug(
        textwrap.dedent(
            """
        ---------------- request ----------------
        {req.method} {req.url}
        {reqhdrs}

        {req.body}
        ---------------- response ----------------
        {res.status_code} {res.reason} {res.url}
        {reshdrs}

        {res.text}

    """
        ).format(
            req=response.request,
            res=response,
            reqhdrs=format_headers(response.request.headers),
            reshdrs=format_headers(response.headers),
        )
    )

    return json.loads(response.text).get("id", None)


def parse_document(data, config, metadata, oauth):
    """Prepare the document to be published on Wordpress. This involves
    extracting the title, uploading the relevant images, and changing
    the links to these images to match those on the Wordpress site
    """
    program_log.debug("Converting content to html")
    html = pypandoc.convert_text(data, "html", format="md")
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    program_log.debug("Extracted content title: {}".format(title))

    media_url = construct_url(
        base_url=config.get("base_url"),
        api_version=config.get("api_version"),
        endpoint="media",
    )
    program_log.debug("Constructed URL for media update: {}".format(media_url))
    img_map = get_image_replacement_map(soup, media_url, metadata.get("id"), oauth)
    img_map = upload_images(img_map, media_url, oauth)
    program_log.debug("Updating content with new image links")
    replace_image_links(soup, img_map)
    content = soup.encode(formatter="html5").lstrip()

    document = {"title": title, "content": content.decode("utf-8")}
    return document


def get_image_replacement_map(soup, media_url, post_id, oauth):
    """Create a dictionary associating the current image file path with the URL
    to replace it with, using the filename it will be uploaded as, as the key
    """
    images_in_doc = [x["src"] for x in soup.find_all("img")]
    program_log.debug("Local image links: {}".format(images_in_doc))
    images_existing = get_existing_images(media_url, oauth)
    image_map = {}

    program_log.debug("Constructing map of local links to remote links")
    for img in images_in_doc:
        target_filename = "{}-{}".format(post_id, os.path.basename(img))
        image_map[target_filename] = {
            "local_path": img,
            "target_path": images_existing.get(target_filename, None),
        }
    program_log.debug("Extracted image map: {}".format(image_map))

    return image_map


def upload_images(img_map, media_url, oauth):
    """Upload images in the blog post to the Wordpress server
    """

    for filename, img in img_map.items():
        if img.get("target_path") is None:

            # Read local image data in
            with open(img.get("local_path"), "rb") as f:
                data = f.read()

            headers = {
                "Content-Type": mimetypes.guess_type(img.get("local_path"))[0],
                "Content-Disposition": "attachment; filename={}".format(filename),
            }
            # Upload image data with filename as specified in header
            response = requests.post(media_url, data=data, headers=headers, auth=oauth,)

            # Record the resulting URL from the image upload
            new_src = json.loads(response.text).get("guid").get("rendered")
            img_map[filename]["target_path"] = new_src
    program_log.debug("Updated image map after upload: {}".format(img_map))

    return img_map


def get_existing_images(media_url, oauth):
    """Obtain a dictionary of all images currently uploaded to the Wordpress
    server to work out what isn't already there and needs to be uploaded
    """

    program_log.debug("Obtaining existing image URLs")
    response = requests.get(media_url, auth=oauth)
    program_log.debug("Request URL: {}".format(response.url))
    program_log.debug("Response status code: {}".format(response.status_code))
    program_log.debug("Response content: {}".format(response.text))
    images = json.loads(response.text)
    image_urls = {
        os.path.basename(x.get("guid", {}).get("rendered")): x.get("guid", {}).get(
            "rendered"
        )
        for x in images
    }
    program_log.debug("Existing images on remote: {}".format(image_urls))
    return image_urls


def extract_title(soup):
    """ Determine the title of the blog post, and remove it from the body of
    the content
    """

    title = soup.h1.string
    soup.h1.extract()

    return title


def replace_image_links(soup, img_map):
    """Replace all links to images within a blog post with the new link
    of the uploaded image
    """

    for filename, img in img_map.items():
        matches = soup.find_all(src=img.get("local_path"))
        for match in matches:
            match["src"] = img.get("target_path")


def parse_args(**kwargs):
    """Merge the input arguments with the parameters in the configuration file
    if the project has been initialised. This prioritises the arguments passed
    from the command line over those in the configuration file.
    """

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
    """Constructs a URL based on various parameters the Wordpress API takes
    """

    if not post_id:
        url = "{}/{}/{}".format(base_url, api_version, endpoint)
    else:
        url = "{}/{}/{}/{}".format(base_url, api_version, endpoint, post_id)
    return url


def authenticate(ctx, **kwargs):
    """Obtain the credentials necessary to interact with a Wordpress server using OAuth1.0
    Workflow based on examples available at: https://requests-oauthlib.readthedocs.io/en/latest/oauth1_workflow.html
    """

    # 0. Load client_key and client_secret from input arguments
    config = parse_args(**kwargs)
    authentication_urls = discover_auth_endpoints(**config)

    # 1. Obtain request token to identify client in the next step
    oauth = OAuth1(
        client_key=config.get("client_key"), client_secret=config.get("client_secret"),
    )
    r = requests.post(url=authentication_urls.get("request"), auth=oauth)
    credentials = parse_qs(r.content.decode("utf-8"))
    resource_owner_key = credentials.get("oauth_token")[0]
    resource_owner_secret = credentials.get("oauth_token_secret")[0]

    # 2. Obtain authorization from the user (resource owner) to access their
    # blog by redirecting them to a verification URL
    print(
        "Authenticate at the following URL to obtain a verification token: {}?oauth_token={}".format(
            authentication_urls.get("authorize"), resource_owner_key
        )
    )
    verifier = input("Enter the verification token: ")

    # 3. Use the verification token to obtain an access token from the OAuth
    # server.

    oauth = OAuth1(
        client_key=config.get("client_key"),
        client_secret=config.get("client_secret"),
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )

    r = requests.post(url=authentication_urls.get("access"), auth=oauth)
    credentials = parse_qs(r.content.decode("utf-8"))
    resource_owner_key = credentials.get("oauth_token")[0]
    resource_owner_secret = credentials.get("oauth_token_secret")[0]

    # 4. These credentials don't expire, and can now be used to access the
    # protected resources of the Wordpress server. These should be used as
    # environment variables for the CI/CD tool.

    print("{:25}{}".format("Client key", config.get("client_key")))
    print("{:25}{}".format("Client secret", config.get("client_secret")))
    print("{:25}{}".format("Resource owner key", resource_owner_key))
    print("{:25}{}".format("Resource owner secret", resource_owner_secret))


def discover_auth_endpoints(**kwargs):
    """Identify the OAuth1.0 endpoints, required to follow the authorization flow
    """
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


def init(ctx, **kwargs):
    """Initialise a directory as a project. This creates a `.deploy` folder
    containing configuration files for the site, and post metadata.
    """

    default_config_dir = os.path.join(ROOT_DIR, "config")
    deploy_dir = ".deploy"

    try:
        # Create a `.deploy` directory in the project root
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

    program_log.info(
        "Configuration file created at {}".format(
            os.path.join(deploy_dir, "config.json")
        )
    )
    shutil.copy(
        os.path.join(default_config_dir, "metadata-default.json"),
        os.path.join(deploy_dir, "metadata.json"),
    )
    program_log.info(
        "Metadata file created at {}".format(os.path.join(deploy_dir, "metadata.json"))
    )


def format_headers(headers):
    return "\n".join(f"{k}: {v}" for k, v in headers.items())
