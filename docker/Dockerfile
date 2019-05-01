FROM ubuntu:bionic-20190307

ENV DEBIAN_FRONTEND noninteractive

# locales
RUN apt-get update && apt-get install -y locales rsync
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8

RUN groupadd -r postgres --gid=999 && useradd -r -g postgres --uid=999 postgres

# postgres
ENV PG_MAJOR 10
RUN apt-get update && apt-get install -y postgresql-common
RUN sed -ri 's/#(create_main_cluster) .*$/\1 = false/' /etc/postgresql-common/createcluster.conf
RUN apt-get update && apt-get install -y postgresql-$PG_MAJOR
RUN apt-get update && apt-get install -y libpq-dev
ENV PGDATA /data/postgres
ENV PATH $PATH:/usr/lib/postgresql/$PG_MAJOR/bin

# python
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y python3.6 python3-pip python3-venv
ENV PATH $PATH:/src/.venv/bin

# django
ENV PYTHONPATH /src/django_project/
RUN groupadd -r django --gid=8000 && useradd -r -m -g django --uid=8000 django
ENV DJANGO_SETTINGS_MODULE core.settings
# RUN pip install --no-cache-dir \
#   django==2.2

# COPY --chown=django:django / /src

WORKDIR /src
