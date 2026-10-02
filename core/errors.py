from django.http import HttpResponse
from django.template.loader import get_template


def error_response(status, title, message, recovery_url='/', recovery_label='Return to Push'):
    # Do not run account context processors: an error page must still work
    # when the database or authenticated session is unavailable.
    html = get_template('error.html').render({
        'status': status, 'title': title, 'message': message,
        'recovery_url': recovery_url, 'recovery_label': recovery_label,
    })
    response = HttpResponse(html, status=status)
    response['Cache-Control'] = 'no-store, private'
    return response


def csrf_failure(request, reason=''):
    staff_action = request.path.startswith('/moderation/')
    return error_response(
        403, 'Please reopen the page.',
        'Your action was not submitted because the page security check failed. '
        'Open a fresh page, sign in if asked, then try again.',
        '/moderation/' if staff_action else '/',
        'Return to the trust desk' if staff_action else 'Return to Push',
    )


def bad_request(request, exception=None):
    return error_response(400, 'We could not read that request.',
                          'Return to Push and try again from a fresh page.')


def not_found(request, exception=None):
    return error_response(404, 'That page could not be found.',
                          'The address may have changed, or the page may no longer be available.')


def server_error(request):
    return error_response(500, 'We could not complete that request.',
                          'Please try again shortly. Check your work record before repeating a payment.')
