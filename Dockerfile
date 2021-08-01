FROM python:3.9

WORKDIR /usr/src/app

COPY . .
RUN pip install --no-cache-dir poetry
RUN poetry install

ENV TZ="America/Toronto" \
	BOT_TOKEN=-1 \
	CHAT_ID=0 \
	POSTGRES_USER=postgres \
	POSTGRES_PASSWORD=password \
	POSTGRES_HOST=db \
	POSTGRES_DB=telegram_bot

CMD [ "sh", "-c", "poetry run python -m telegram_stats_bot.main --tz=$TZ $BOT_TOKEN $CHAT_ID postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB" ]