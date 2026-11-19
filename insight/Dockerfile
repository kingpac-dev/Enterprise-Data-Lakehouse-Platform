# UAT reference base. Rebuild and scan in CI; promote the derived image by digest.
FROM apache/superset:6.1.0@sha256:16b50bbef6648912a79e3293d418fefa743ce555d36c5af6b85d859119ed7f88

USER root
COPY insight/requirements.txt /tmp/kingpac-requirements.txt
RUN uv pip install --no-cache-dir -r /tmp/kingpac-requirements.txt
RUN uv pip check
COPY --chown=superset:superset insight/ /app/kingpac/
ENV SUPERSET_CONFIG_PATH=/app/kingpac/superset_config.py
USER superset
