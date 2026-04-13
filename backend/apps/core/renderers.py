from rest_framework.renderers import JSONRenderer
import json


class ApiRenderer(JSONRenderer):
    """Wraps all successful responses in {"data": ...}."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is not None:
            response = renderer_context.get("response")
            # Error responses are already wrapped by the exception handler
            if response is not None and response.status_code >= 400:
                return super().render(data, accepted_media_type, renderer_context)
        wrapped = {"data": data}
        return super().render(wrapped, accepted_media_type, renderer_context)
