import contextvars
import logging


request_id = contextvars.ContextVar('push_request_id', default='-')


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get()
        return True
