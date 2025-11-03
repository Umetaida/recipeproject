from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, IngredientListView, ConditionViewSet

#DefaultRouter() を作成→「ViewSetに対応するURL」を自動的に作ってくれる
router = DefaultRouter()
router.register(r'foods', IngredientViewSet)
router.register(r'conditions', ConditionViewSet)


urlpatterns = [
    path('api/suggest/', views.ai_recipe_suggest, name='ai_recipe_suggest'),
    path('api/save_recipe/', views.save_recipe, name='save_recipe'),
    path('api/saved_recipes/', views.get_saved_recipes, name='saved_recipes'),
    path('', include(router.urls)),  # routerは最後に
]

