# Use the official Open WebUI image as the base
FROM ghcr.io/open-webui/open-webui:main

# Set environment variables for Hugging Face Spaces
ENV PORT=7860
ENV OPEN_WEBUI_PORT=7860
ENV HOME=/home/user
ENV DATA_DIR=/app/backend/data
ENV OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
# Note: Set WEBUI_SECRET_KEY and OPENAI_API_KEY in HF Space Secrets
ENV WEBUI_NAME="Cortextia AI"
ENV SCARF_NO_ANALYTICS=True
ENV DO_NOT_TRACK=True
ENV ANONYMIZED_TELEMETRY=False
ENV ENV=dev
ENV ENABLE_SIGNUP=False

# Port 7860 is the default for HF Spaces
EXPOSE 7860

# Fix permissions for data and static directories to allow UID 1000 (HF default user)
USER root
RUN mkdir -p $DATA_DIR && \
    chown -R 1000:1000 $DATA_DIR && \
    find $DATA_DIR -type d -exec chmod 770 {} + && \
    find $DATA_DIR -type f -exec chmod 660 {} + && \
    chown -R 1000:1000 /app/backend/open_webui/static && \
    find /app/backend/open_webui/static -type d -exec chmod 755 {} + && \
    find /app/backend/open_webui/static -type f -exec chmod 644 {} +

# Switch to root for installation
USER root

# Install supercronic for container-native scheduling
# Using a specific release version for stability
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=71b0d58cc53f6bd72cf2f293e09e294b79c666d8

RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" /usr/local/bin/supercronic \
    && ln -s "/usr/local/bin/supercronic" /usr/local/bin/supercronic-linux-amd64

# Copy only what the container needs (ROBUST FIX)
# This prevents Docker from attempting to include runtime caches like:
#   data/cache/embedding/.../snapshots/.../.gitattributes
COPY owui_index_generator/ /app/backend/data/owui_index_generator/
COPY cron/ /app/backend/data/cron/
COPY sync_index.py /app/backend/data/sync_index.py
COPY generate_index.py /app/backend/data/generate_index.py

# Fix permissions for project files and preserve executables for scripts
RUN chown -R 1000:1000 /app/backend/data && \
    find /app/backend/data -type d -exec chmod 770 {} + && \
    find /app/backend/data -type f -exec chmod 660 {} + && \
    find /app/backend/data -type f -name "*.sh" -exec chmod 770 {} + && \
    find /app/backend/data -type f -name "*.py" -exec chmod 770 {} +

# Add cron schedule and wrapper
COPY cron/sync-index.cron /etc/cron.d/sync-index.cron
COPY entrypoint-with-cron.sh /entrypoint-with-cron.sh
RUN chmod +x /entrypoint-with-cron.sh \
    && chown -R 1000:1000 /etc/cron.d/sync-index.cron

# Switch back to the non-root user (UID 1000)
USER 1000

# Replace CMD to include scheduler, then start Open WebUI
CMD ["/entrypoint-with-cron.sh"]
