FROM python:3.8-slim-buster

RUN pip install flask
RUN pip install gunicorn pyopenssl
RUN pip install firebase-admin
RUN pip install arrow

COPY . /app
WORKDIR /app

ENV FLASK_APP=forecaster_flask.py

EXPOSE 5000

CMD ["gunicorn", "forecaster_flask:APP", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2"]