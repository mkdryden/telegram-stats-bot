import logging

from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)


def init_dbs(engine: Engine):
    sql = """
        create table if not exists messages_utc
        (
            message_id              bigint,
            date                    timestamptz,
            from_user               bigint,
            forward_from_message_id bigint,
            forward_from            bigint,
            forward_from_chat       bigint,
            caption                 text,
            text                    text,
            sticker_set_name        text,
            new_chat_title          text,
            reply_to_message        bigint,
            file_id                 text,
            type                    text
        );
        
        create index if not exists messages_utc_date_index
            on messages_utc (date);
        
        create index if not exists messages_utc_from_user_index
            on messages_utc (from_user);
        
        create index if not exists messages_utc_type_index
            on messages_utc (type);
            
        create table if not exists user_events
        (
            message_id bigint,
            user_id    bigint,
            date       timestamp with time zone,
            event      text
        );
        
        create index if not exists ix_user_events_message_id
            on user_events (message_id);
        
        create table if not exists user_names
        (
            user_id  bigint,
            date     timestamptz,
            username text
        );
        
        create index if not exists user_names_user_id_date_index
            on user_names (user_id, date);
        
        """

    with engine.connect() as con:
        con.execute(sql)
