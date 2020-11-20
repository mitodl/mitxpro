"""Utility functions for celery"""
from datetime import timedelta

from celery.schedules import schedule


class OffsettingSchedule(schedule):
    """
    Specialized celery schedule class that allows for easy definition of an offset time for a
    scheduled task (e.g.: the task should run every 30, but it should start after a 15 second offset)

    Inspired by this SO answer: https://stackoverflow.com/a/41700962
    """

    def __init__(self, run_every=None, offset=None):
        self._run_every = run_every
        self._offset = offset
        self._apply_offset = offset is not None
        super().__init__(run_every=self._run_every + (offset or timedelta(seconds=0)))

    def is_due(self, last_run_at):
        retval = super().is_due(last_run_at)
        if self._apply_offset is not None and retval.is_due:
            self._apply_offset = False
            self.run_every = self._run_every
            retval = super().is_due(last_run_at)
        return retval

    def __reduce__(self):
        return self.__class__, (self._run_every, self._offset)
