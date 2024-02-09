from celery import Celery

from config_files import celeryconfig

app = Celery('blog', include=['accounts.tasks'])

app.config_from_object(celeryconfig)
