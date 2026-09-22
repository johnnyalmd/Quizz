from django.urls import include, path
from rest_framework.routers import DefaultRouter

from study.api.views import LessonViewSet, SessionViewSet

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lesson")
router.register("sessions", SessionViewSet, basename="session")

urlpatterns = [
    path("", include(router.urls)),
]
