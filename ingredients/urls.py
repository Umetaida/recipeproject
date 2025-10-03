from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, IngredientListView, ConditionViewSet

#DefaultRouter() を作成→「ViewSetに対応するURL」を自動的に作ってくれる
router = DefaultRouter()
router.register(r'foods', IngredientViewSet)
router.register(r'conditions', ConditionViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
