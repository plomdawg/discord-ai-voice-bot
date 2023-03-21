FROM python:3.8
 
WORKDIR /app
COPY bot /app
COPY entrypoint.sh /app
 
RUN pip install -r requirements.txt

ENTRYPOINT ["./entrypoint.sh"]
