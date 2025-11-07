FROM python:3.12
ARG APP_VERSION

WORKDIR /app

RUN apt-get update

RUN apt-get install -y locales
RUN echo "" > /etc/locale.gen
RUN for locale in "en_US ISO-8859-1" "uk_UA ISO-8859-5" "ru_RU ISO-8859-5"; do echo "$locale" >> /etc/locale.gen; done
RUN locale-gen

RUN apt-get install -y build-essential python3-dev libffi-dev
COPY bot_app/requirements.txt /app/
RUN pip install -r requirements.txt

COPY bot_app ./bot_app

# Set application version from passed in Tag
RUN if [ -n "$APP_VERSION" ]; then sed -i "s/__version__ =.*/__version__ = '$APP_VERSION'/g" ./bot_app/config.py; fi

CMD python -m "bot_app"
