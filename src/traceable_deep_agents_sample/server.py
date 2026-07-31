import uvicorn

from traceable_deep_agents_sample.config import Settings


def main() -> None:
    """Run the sample as an external Agent Server."""

    settings = Settings()
    uvicorn.run(
        "traceable_deep_agents_sample.api:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
    )


if __name__ == "__main__":
    main()

