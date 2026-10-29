FROM node:22-bookworm-slim AS frontend
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
WORKDIR /app
COPY requirements.txt requirements-ui.txt ./
# Install separately: the UI upgrades the shared typing dependency.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-ui.txt
COPY . .
COPY --from=frontend /build/web/dist ./web/dist
EXPOSE 8765
# A single worker owns the workflow state, rate limiter and snapshots.
CMD ["uvicorn", "visual_api:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
