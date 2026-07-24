from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ScriptViewSet,
    SceneViewSet,
    LineViewSet,
    CharacterViewSet,
    RelationshipViewSet,
    BeatViewSet,
)

router = DefaultRouter()
router.register(r"scripts", ScriptViewSet, basename="script")
router.register(r"scenes", SceneViewSet, basename="scene")
router.register(r"lines", LineViewSet, basename="line")
router.register(r"characters", CharacterViewSet, basename="character")
router.register(r"relationships", RelationshipViewSet, basename="relationship")
router.register(r"beats", BeatViewSet, basename="beat")

urlpatterns = [
    path("", include(router.urls)),
]
