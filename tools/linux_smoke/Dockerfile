FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb openbox xdotool x11-utils fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV DISPLAY=:99
WORKDIR /app
COPY tools/linux_smoke/run.sh /usr/local/bin/run-on-xvfb
RUN sed -i "s/
RUN sed -i "s/
RUN chmod +x /usr/local/bin/run-on-xvfb
