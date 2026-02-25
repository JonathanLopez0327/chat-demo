from src.graph.builder import agent

__all__ = ["agent"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.whatsapp.webhook:app", host="0.0.0.0", port=8000, reload=True
    )
