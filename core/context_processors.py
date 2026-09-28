from core.preferences import get_preferences


def ui_preferences(request):
    return {"ui_preferences": get_preferences(request.session)}
