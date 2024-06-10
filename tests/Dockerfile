FROM whisper-bot-tg_bot

# RUN apt-get update && \
#       apt-get -y install sudo

ENV PYTHONPATH=/src
ENV APP_CONFIG /src/config.yaml
WORKDIR /tests

COPY requirements-test.txt ./

RUN python3 -m pip install -U --no-cache-dir -r requirements-test.txt

USER appuser:appgroup

CMD ["pytest", "."]

