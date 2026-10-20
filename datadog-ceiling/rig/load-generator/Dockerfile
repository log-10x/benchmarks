# Slim build of the demo's own load generator (src/load-generator at tag 3.1.0): the same
# base image, the same hash-pinned requirements and the same locustfile.py and people.json,
# without `playwright install --with-deps chromium`. The rig runs it with
# LOCUST_BROWSER_TRAFFIC_ENABLED=false, so the browser user is never started.
# Build context: the demo clone.
#   docker build -f <rig>/load-generator/Dockerfile -t rig/load-generator:3.1.0 <demo clone>

FROM docker.io/library/python:3.14.7-slim-bookworm@sha256:9ab8d9c8514b44f90cf0029dd42fdd7e9e211e639c8b995304cc04568dee900f AS base

FROM base AS builder
RUN apt-get -qq update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

COPY ./src/load-generator/requirements.txt .
RUN pip install --no-cache-dir --prefix="/reqs" --require-hashes -r requirements.txt

FROM base
WORKDIR /usr/src/app/
COPY --from=builder /reqs /usr/local
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers
COPY ./src/load-generator/locustfile.py .
COPY ./src/load-generator/people.json .
ENTRYPOINT ["locust", "--skip-log-setup"]
