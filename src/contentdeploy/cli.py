import click
import contentdeploy.application


@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    pass


@click.group()
def config(**kwargs):
    pass


@config.command()
def get(**kwargs):
    pass


@config.command()
def set(**kwargs):
    pass


@cli.command()
@click.option("-f", "--file", type=str, help="The file to publish")
def publish(**kwargs):
    pass


@cli.command()
def init(**kwargs):
    pass


cli.add_command(config)


if __name__ == "__main__":
    cli()
