from celery import Celery

from config_files import celeryconfig

app = Celery('blog', include=['accounts.tasks', 'common.tasks'])

app.config_from_object(celeryconfig)
