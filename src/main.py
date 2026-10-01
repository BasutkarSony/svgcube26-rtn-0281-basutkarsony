from fastapi import FastAPI
from src.models.api import ReturnsAgentRequest, ReturnsAgentResponse
from src.agent.returns_agent import ReturnsAgent
from src.agent.gemini_provider import GeminiVisionProvider


app = FastAPI(title="Returns Manager Agent")


agent = ReturnsAgent(provider=GeminiVisionProvider())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/agent", response_model=ReturnsAgentResponse)
async def process_return(request: ReturnsAgentRequest):
    evidence = agent.analyze(request)

    return ReturnsAgentResponse(
        success=True,
        evidence=evidence,
    )

