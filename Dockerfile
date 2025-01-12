FROM python:3.11-alpine3.18
LABEL maintainer="v.s.viesich@gmail.com"

ENV PYTHOUNNBUFFERED=1

WORKDIR /app/

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /files/media /app/files

RUN adduser \
    --disabled-password \
    --no-create-home \
    my_user

RUN chown -R my_user /files/media /app/files
RUN chmod -R 755 /files/media /app/files

USER my_user
