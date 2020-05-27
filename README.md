# GitHub Wordpress Bridge

gwbridge is a program that manages the continuous deployment of content written on GitHub to a WordPress blog.

## External Dependencies

- Pandoc

See [Installing pandoc](https://pandoc.org/installing.html) for instructions on installing this for your target platform.

## Installation

`gwbridge` is available for installation using `pip` or `pipx` as follows:

```bash
$ pipx install git+https://github.com/samuel-emrys/gwbridge.git
```

```bash
$ pip install git+https://github.com/samuel-emrys/gwbridge.git
```

Of these, the `pipx` method is recommended. This will make the command available in the global environment whilst maintaining a virtual environment for the required python dependencies. See the [`pipx` documentation](https://github.com/pipxproject/pipx) for installation instructions.

## Usage

`gwbridge` has three functions:
1. Initialisation of a repository
2. Obtaining authentication keys
3. Publishing a post to a wordpress blog

### Initialisation

Navigate to your repository and initialise it as follows:

```bash
$ gwbridge init
Enter the base URL of the wordpress blog to update (required): https://www.example.com/wp-json
Enter the version of the WPI you wish to use [wp/v2]:
Enter the name of the file to publish [README.md]:
Configuration file created at .deploy/config.json
Metadata file created at .deploy/metadata.json
```

This configures the file `README.md` to be pushed as a new blog post to the Wordpress site https://www.example.com. As mentioned, this will create a configuration file in `.deploy/config.json`, and initialise a file containing the post metadata in `.deploy/metadata.json`. Edit these files as you desire to configure the way your post is created. The available fields are detailed in the [Wordpress REST API Documentation](https://developer.wordpress.org/rest-api/reference/posts/).

### Authentication

Authentication requires the Wordpress server to have the [WordPress REST API - OAuth 1.0a Server](https://wordpress.org/plugins/rest-api-oauth1/) plugin installed. Once installed, navigate to Users > Applications and Edit the application you've created. This page has two credential fields, `Client Key`, and `Client Secret`. You'll need to use these values to generate the appropriate authentication keys to allow `gwbridge` to create a post on your site. If you've already initialised a repository, you can run:

```bash
$ gwbridge authenticate --client-key $WP_CLIENT_KEY --client-secret $WP_CLIENT_SECRET
```

Otherwise, you'll need to pass the `--base-url` and `--api-version` flags to indicate the site you want to authenticate to:

```bash
$ gwbridge authenticate --client-key $WP_CLIENT_KEY --client-secret $WP_CLIENT_SECRET --base-url https://www.example.com/wp-json --api-version wp/v2
```

Navigate to the prompted link, and sign in to your desired Wordpress account. It must have the `Editor` role or higher, however, so that it can create and update posts. This will present you with a token. Copy and paste the token to the command prompt. Pressing `Enter` will then provide you with `Resource Owner Key` and `Resource Owner Secret` credentials. These will be used to publish your post.

### Publish

To publish, make sure you have your desired values in `.deploy/metadata`, and then execute the following command:

```bash
$ gwbridge publish --client-key $WP_CLIENT_KEY --client-secret $WP_CLIENT_SECRET --resource-owner-key $WP_RESOURCE_OWNER_KEY --resource-owner-secret $WP_RESOURCE_OWNER_SECRET
```

NOTE: The post `title` and `content` fields will be automatically populated from the markdown file and shouldn't be populated in the metadata configuration. For new posts, the `id` field should be left blank. This will be automatically updated after the post is first published to Wordpress to the new post id.
