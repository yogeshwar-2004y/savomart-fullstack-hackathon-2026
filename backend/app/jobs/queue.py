from redis import Redis
from rq import Queue

from app.core.config import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue(settings.queue_name, connection=redis)
