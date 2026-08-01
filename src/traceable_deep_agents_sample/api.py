from fastapi import FastAPI, HTTPException, status

from traceable_deep_agents_sample.config import Settings
from traceable_deep_agents_sample.runtime_adapter import TraceableRuntimeAdapter
from traceable_deep_agents_sample.runtime_adapter import MANIFEST_VERSION
from traceable_deep_agents_sample.runtime_contract import (
    RuntimeAgentListResponse,
    RuntimePublicAgent,
    RuntimeRunCreateRequest,
    RuntimeRunResponse,
    RuntimeTraceResponse,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an external Agent Server compatible with traceable-agent-runtime.

    This app is intentionally thin: the tracing contract lives in
    `TraceableRuntimeAdapter`, while FastAPI only exposes the HTTP boundary that
    another runtime or UI can call.
    """

    settings = settings or Settings()
    adapter = TraceableRuntimeAdapter(settings=settings)
    app = FastAPI(title="Traceable Deep Agents Sample", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/agents", response_model=RuntimeAgentListResponse)
    def list_agents() -> RuntimeAgentListResponse:
        return RuntimeAgentListResponse(
            agents=[
                RuntimePublicAgent(
                    id=settings.agent_id,
                    agent_id=settings.agent_id,
                    name=settings.agent_name,
                    description="Tech Radar analyst external Agent Server.",
                    manifest_version=MANIFEST_VERSION,
                    tools=["search_tech_news", "get_tech_news_article", "get_latest_tech_news"],
                )
            ]
        )

    @app.post("/v1/runs", response_model=RuntimeRunResponse, status_code=status.HTTP_201_CREATED)
    def create_run(payload: RuntimeRunCreateRequest) -> RuntimeRunResponse:
        # Keep request/response shape aligned with traceable-agent-runtime so
        # integration can start as a proxy before becoming a native runtime tool.
        return adapter.run(payload)

    @app.get("/v1/runs/{run_id}/trace", response_model=RuntimeTraceResponse)
    def get_trace(run_id: str) -> RuntimeTraceResponse:
        trace = adapter.get_trace(run_id)
        if trace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
        return trace

    return app


app = create_app()
