import base64
import json
from google.cloud import sql
from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import os

# Database connection (production only - this runs in Cloud)
connector = Connector()


def getconn():
    conn = connector.connect(
        os.environ.get("CLOUD_SQL_CONNECTION_NAME"),
        "pymysql",
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        db=os.environ.get("DB_NAME")
    )
    return conn


engine = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)
SessionLocal = sessionmaker(bind=engine)


def process_ranking_event(event, context):
    """
    Triggered by a message on a Pub/Sub topic.
    This function processes ranking creation events.
    """
    print(f"Function triggered by messageId {context.event_id}")
    print(f"Event type: {context.event_type}")

    # Decode the Pub/Sub message
    if 'data' in event:
        message_data = base64.b64decode(event['data']).decode('utf-8')
        event_data = json.loads(message_data)

        print(f"Processing event: {event_data}")

        ranking_id = event_data.get('ranking_id')
        event_type = event_data.get('event_type')

        if event_type == "ranking_created":
            # Do something with the ranking
            session = SessionLocal()
            try:
                # Example: Log the ranking details
                ranking = session.execute(
                    sqlalchemy.text("""
                        SELECT id, user_id, created_at 
                        FROM rankings 
                        WHERE id = :id
                    """),
                    {"id": ranking_id}
                ).first()

                if ranking:
                    print(f"✅ Processed ranking: {ranking[0]} for user: {ranking[1]}")

                    # You could do additional processing here:
                    # - Send notification
                    # - Update analytics
                    # - Trigger another workflow
                else:
                    print(f"⚠️ Ranking {ranking_id} not found")

            except Exception as e:
                print(f"❌ Error processing ranking: {e}")
            finally:
                session.close()
    else:
        print("No data in event")