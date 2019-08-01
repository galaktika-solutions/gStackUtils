from django.views.generic import View, TemplateView
from django.http import HttpResponse


class DemoView(TemplateView):
    template_name = "demo/demo.html"


class FileDownload(View):
    def get(self, request, path):
        response = HttpResponse(content_type='application/file')
        response['X-Accel-Redirect'] = b"/media_internal/" + path.encode("utf-8")
        return response
