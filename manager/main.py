from fastapi import FastAPI

app = FastAPI(title="trykuhn-vpn-manager")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
