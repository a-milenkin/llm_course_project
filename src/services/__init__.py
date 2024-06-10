from dataclasses import dataclass


@dataclass
class Services:
    pass


async def setup_services(app):
    app.Services = Services(
    )
