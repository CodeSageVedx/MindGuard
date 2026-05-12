import uvicorn
from fastapi import FastAPI
from src.config import settings
from src.api import routes


app = FastAPI(title="MindGuard AI Service")

@app.get("/")
async def root():
    return {"message": "Welcome to MindGuardAI API"}

app.include_router(routes.router, prefix=settings.API_V1_STR)

def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        workers=1
    )

if __name__ == "__main__":
    main()