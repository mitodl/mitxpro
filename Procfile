release: bash scripts/heroku-release-phase.sh
web: bin/start-nginx bin/start-pgbouncer newrelic-admin run-program granian --interface wsgi --host 0.0.0.0 --port 8051 --workers 2 mitxpro.wsgi:application
worker: bin/start-pgbouncer newrelic-admin run-program celery -A mitxpro.celery:app worker -E -B -l $MITXPRO_LOG_LEVEL
extra_worker: bin/start-pgbouncer newrelic-admin run-program celery -A mitxpro.celery:app worker -E -l $MITXPRO_LOG_LEVEL
