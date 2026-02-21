# Use the official Open WebUI image as the base
FROM ghcr.io/open-webui/open-webui:main

# Set environment variables for Hugging Face Spaces
ENV PORT=7860
ENV OPEN_WEBUI_PORT=7860
ENV HOME=/home/user
ENV DATA_DIR=/app/backend/data
ENV OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
# Note: It's better to set the real key in HF Secrets
ENV WEBUI_SECRET_KEY="cortext_secret_key_123"
ENV WEBUI_NAME="Cortextia AI"
ENV SCARF_NO_ANALYTICS=True
ENV DO_NOT_TRACK=True
ENV ANONYMIZED_TELEMETRY=False

# Port 7860 is the default for HF Spaces
EXPOSE 7860

# Fix permissions for the data directory to allow UID 1000 (HF default user)
USER root
RUN mkdir -p $DATA_DIR && \
    chown -R 1000:1000 $DATA_DIR && \
    chmod -R 777 $DATA_DIR

# Switch to the non-root user (UID 1000)
USER 1000

# The base image already defines an entrypoint and CMD to start the WebUI
