"""Read-only staff view for pilot reliability diagnostics."""
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .access import staff_only
from .pilot_reliability import build_pilot_reliability_report


@staff_only('owner', 'admin')
@require_GET
def pilot_reliability(request):
    report = build_pilot_reliability_report()
    response = render(request, 'pilot_reliability.html', {'report': report})
    response['Cache-Control'] = 'no-store'
    return response
