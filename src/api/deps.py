from fastapi import Depends, Request

from src.core.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_conversation_service(container: Container = Depends(get_container)):
    return container.conversation_service


def get_messaging(container: Container = Depends(get_container)):
    return container.messaging


def get_reminder_service(container: Container = Depends(get_container)):
    return container.reminder_service


def get_settings_dep(container: Container = Depends(get_container)):
    return container.settings
