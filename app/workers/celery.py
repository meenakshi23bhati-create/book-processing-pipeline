from celery import Celery
from   app.core.config import settings

celery_app= Celery(
    "book_processor",
    broker= settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.task"]
)

celery_app.conf.update(
    task_serializer= "json",
    result_serializer= "json",
    accept_content=["json"],
    task_track_started= True,
    worker_prefetch_multiplier=1 ,  # ek time mein ek task — fair distribution
)