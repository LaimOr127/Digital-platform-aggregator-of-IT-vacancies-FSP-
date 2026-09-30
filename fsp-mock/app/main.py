"""Мок API ФСП. Структура данных (дисциплины, соревнования, результаты, роли, разряды)
будет наполнена в фазе 2; при появлении реальной спецификации мок приводится к ней."""

from fastapi import FastAPI

app = FastAPI(title="FSP mock", version="0.1.0", docs_url="/docs", redoc_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
