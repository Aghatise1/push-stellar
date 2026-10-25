"""Read-only staff views for pilot reliability diagnostics."""
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .access import staff_only
from .pilot_reliability import (
    build_pilot_reliability_inspection,
    build_pilot_reliability_report,
)


@staff_only('owner', 'admin')
@require_GET
def pilot_reliability(request):
    report = build_pilot_reliability_report()
    request.user.email = ''
    response = render(request, 'pilot_reliability.html', {'report': report})
    response['Cache-Control'] = 'no-store'
    return response


@staff_only('owner', 'admin')
@require_GET
def pilot_reliability_inspect(request, pk):
    inspection = build_pilot_reliability_inspection(pk)
    if inspection is None:
        raise Http404('Pilot reliability record not found.')
    request.user.email = ''
    response = render(request, 'pilot_reliability_inspect.html', {'inspection': inspection})
    response['Cache-Control'] = 'no-store'
    return response
