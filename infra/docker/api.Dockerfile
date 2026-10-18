FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -c requirements-ci.txt -e ".[dev]"
CMD ["python", "-m", "app.run"]
