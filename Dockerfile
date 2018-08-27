FROM python:2.7.15-stretch

COPY . /app/

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
     festival \
     pulseaudio \
     pulseaudio-utils \
     wget \
     tar \
     build-essential \
     autoconf \
     libasound2-dev

RUN bash build-pjsip.sh
RUN pip install -r requirements.txt

ENTRYPOINT ["/app/caller.py"]