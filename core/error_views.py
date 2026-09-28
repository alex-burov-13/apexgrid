"""Branded error handlers without leaking exception details."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def handler404(
    request: HttpRequest,
    exception: Exception,
) -> HttpResponse:
    return render(request, "404.html", status=404)


def handler500(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)
