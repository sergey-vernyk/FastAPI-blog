from celery import Celery

app = Celery('blog', include=['accounts.tasks'])

app.config_from_object('config_files.celeryconfig')
