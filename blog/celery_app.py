from celery import Celery

app = Celery('blog', include=['accounts.tasks'])

app.config_from_object('blog.config_files.celeryconfig')
