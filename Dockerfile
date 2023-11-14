FROM python:3.11

WORKDIR /usr/src/app

COPY . .
RUN pip install .

ENV TZ="America/New_York" \
	BOT_TOKEN=-1 \
	CHAT_ID=0 \
	POSTGRES_USER=postgres \
	POSTGRES_PASSWORD=password \
	POSTGRES_HOST=db \
	POSTGRES_DB=telegram_bot

CMD [ "sh", "-c", "python -m telegram_stats_bot.main --tz=$TZ $BOT_TOKEN $CHAT_ID postgresql+psycopg://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB" ]
