import click
import gwbridge.application


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(
        ["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        case_sensitive=False,
    ),
    default="INFO",
    show_default=True,
    help="The level of logging to use",
)
@click.option(
    "-v", "verbosity", count=True, help="Increase the verbosity of the output"
)
@click.option("-q", "verbosity", flag_value=0, help="Suppress all output")
@click.pass_context
def cli(ctx, **kwargs):
    ctx.obj = kwargs


@cli.command()
@click.option("-f", "--file", type=str, help="The file to publish")
@click.option("--client-key", type=str, help="The client key")
@click.option("--client-secret", type=str, help="The client secret")
@click.option("--resource-owner-key", type=str, help="The resource owner key")
@click.option("--resource-owner-secret", type=str, help="The resource owner secret")
@click.option("--base-url", type=str, help="The URL to make API calls against")
@click.option("--api-version", type=str, help="The version of the site's API to use")
@click.pass_context
def publish(ctx, **kwargs):
    gwbridge.application.publish(ctx, **kwargs)


@cli.command()
@click.option("--client-key", type=str, help="The client key")
@click.option("--client-secret", type=str, help="The client secret")
@click.option("--base-url", type=str, help="The URL to make API calls against")
@click.option("--api-version", type=str, help="The version of the site's API to use")
@click.pass_context
def authenticate(ctx, **kwargs):
    gwbridge.application.authenticate(ctx, **kwargs)


@cli.command()
@click.pass_context
def init(ctx, **kwargs):
    gwbridge.application.init(ctx, **kwargs)


if __name__ == "__main__":
    cli()
