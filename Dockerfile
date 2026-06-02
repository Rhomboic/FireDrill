# FireDrill job image — runs ONE (scenario × model) job and exits.
#
# Bundles the gym + agent + eval + runner and every scenario. SCENARIO and MODEL
# are injected at runtime (so one image serves the whole matrix), API keys come
# from the environment / Secrets Manager. Python + Node cover the python, node,
# and sql scenarios; the React/Playwright UI scenarios use a separate image.

FROM python:3.12-slim

# Node.js 22 for the node/JS/SQL scenarios' own test runners.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get purge -y gnupg && apt-get autoremove -y \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/firedrill

# Python deps first (cached layer).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The gym and everything that drives it, plus all scenarios.
COPY gym/ gym/
COPY agent/ agent/
COPY eval/ eval/
COPY runner/ runner/
COPY scenarios/ scenarios/

RUN mkdir -p results

# Runtime config: SCENARIO + MODEL (+ S3_BUCKET, MAX_STEPS) from the environment;
# ANTHROPIC_API_KEY / OPENAI_API_KEY injected at run time.
ENTRYPOINT ["python3", "runner/run_job.py"]
