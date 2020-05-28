import click
import gwbridge.application


@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    pass


@cli.command()
@click.option("-f", "--file", type=str, help="The file to publish")
@click.option("--client-key", type=str, help="The client key")
@click.option("--client-secret", type=str, help="The client secret")
@click.option("--resource-owner-key", type=str, help="The resource owner key")
@click.option("--resource-owner-secret", type=str, help="The resource owner secret")
@click.option("--base-url", type=str, help="The URL to make API calls against")
@click.option("--api-version", type=str, help="The version of the site's API to use")
def publish(**kwargs):
    gwbridge.application.publish(**kwargs)


@cli.command()
@click.option("--client-key", type=str, help="The client key")
@click.option("--client-secret", type=str, help="The client secret")
@click.option("--base-url", type=str, help="The URL to make API calls against")
@click.option("--api-version", type=str, help="The version of the site's API to use")
def authenticate(**kwargs):
    gwbridge.application.authenticate(**kwargs)


@cli.command()
def init(**kwargs):
    gwbridge.application.init(**kwargs)


if __name__ == "__main__":
    cli()
