FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
