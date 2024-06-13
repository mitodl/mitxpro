web: bin/start-nginx bin/start-pgbouncer newrelic-admin run-program uwsgi uwsgi.ini
worker: bin/start-pgbouncer newrelic-admin run-program celery -E -A mitxpro.celery:app worker -B -l $MITXPRO_LOG_LEVEL
extra_worker: bin/start-pgbouncer newrelic-admin run-program celery -E -A mitxpro.celery:app worker -l $MITXPRO_LOG_LEVEL
