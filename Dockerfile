FROM python:3.8
 
WORKDIR /app
COPY bot /app
COPY entrypoint.sh /app
 
RUN apt-get update
RUN apt-get install --yes libportaudio2
RUN apt-get install --yes ffmpeg

RUN pip install -r requirements.txt


ENTRYPOINT ["./entrypoint.sh"]
