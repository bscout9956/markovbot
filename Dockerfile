ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-alpine

RUN mkdir /markovbot
WORKDIR /markovbot

COPY ./ /markovbot/

RUN pip install -r requirements.txt

CMD ["python3","markovbot.py"]
