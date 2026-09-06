# Litmus — container image.
#
# Built for Hugging Face Spaces (Docker SDK), which serves on port 7860 and
# gives 16 GB of RAM on its free CPU tier. The same image runs anywhere that
# takes a Dockerfile; only the port differs.

FROM python:3.11-slim

# libGL and libglib are needed by opencv, which mtcnn pulls in for face
# detection. ffmpeg backs librosa's audio decoding. Without these the image
# builds fine and then fails at the first request, which is the worst place to
# find out.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Spaces runs the container as uid 1000. Model downloads, the HF cache and any
# temporary file must be writable by that user, so the whole app directory is
# owned by it rather than by root.
RUN useradd -m -u 1000 litmus
USER litmus
ENV HOME=/home/litmus \
    PATH=/home/litmus/.local/bin:$PATH \
    HF_HOME=/home/litmus/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /home/litmus/app

# Dependencies first, so a source change does not reinstall torch every build.
COPY --chown=litmus:litmus requirements.txt ./
COPY --chown=litmus:litmus backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=litmus:litmus . .

# Pre-download the four public checkpoints into the image. Left to the first
# request this is ~1.9 GB fetched while someone waits, and again after every
# restart. The script never fails the build; models still load on demand.
RUN python scripts/precache_models.py

EXPOSE 7860

# One worker, always. Sessions live in process memory, so a challenge minted by
# one worker is invisible to another and LiveChallenge fails about half the time.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1", "--app-dir", "backend"]
