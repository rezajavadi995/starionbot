FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md /app/
COPY bot /app/bot
COPY games /app/games
COPY admin_tools /app/admin_tools
RUN pip install --no-cache-dir .
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8000"]
