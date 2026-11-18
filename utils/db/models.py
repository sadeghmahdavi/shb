from dataclasses import dataclass


@dataclass(frozen=True)
class Application:
    """One row of the applications table: the monitored app both services crawl and analyze from."""

    id: int
    title: str
    package_name: str
