web: bin/start-nginx bin/start-pgbouncer-stunnel newrelic-admin run-program uwsgi uwsgi.ini
worker: celery -A mitxpro.celery:app worker -B -l $MITXPRO_LOG_LEVEL
extra_worker: celery -A mitxpro.celery:app worker -l $MITXPRO_LOG_LEVEL
