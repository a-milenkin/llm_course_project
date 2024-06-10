FROM python:3.11-slim-buster

RUN export LC_ALL=C.UTF-8 && export LANG=C.UTF-8

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN groupadd -g 1001 appgroup && useradd -m -u 1001 appuser
ENV PATH="${PATH}:/home/appuser/.local/bin"

RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    apt-get install -y ffmpeg libavcodec-extra libopus-dev && \
    python3 -m pip install --no-cache-dir -U setuptools pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src

USER root
RUN chown -R appuser:appgroup ./

USER appuser:appgroup


COPY requirements.txt constraints.txt ./
COPY config.yaml ./

RUN python3 -m pip install --no-cache-dir -r requirements.txt -c constraints.txt

CMD ["python", "-u", "/src/main.py"]