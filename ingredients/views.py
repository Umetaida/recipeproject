from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ingredient, Condition
from .serializers import IngredientSerializer, ConditionSerializer
from django.views.generic import ListView, CreateView
from django.shortcuts import redirect
from .forms import IngredientForm
from .models import Ingredient

#汎用ビュー部分（HTML表示用）
class IngredientCreateView(CreateView):
    model = Ingredient
    form_class = IngredientForm
    template_name = "ingredients/register.html"
    
    def form_valid(self, form):
        form.save()
        return redirect("ingredient_register")

class IngredientListView(ListView):
    model = Ingredient
    template_name = "ingredients/list.html"
    context_object_name = "ingredients"


#API部分（JSON返却用）
#食材
class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()#食材データを全部対象にする
    serializer_class = IngredientSerializer#JSON変換のためにシリアライザを利用

#体調
class ConditionViewSet(viewsets.ModelViewSet):
    queryset = Condition.objects.all().order_by('-created_at')#体調データを全部対象にして、それらを新しい順に並べる
    serializer_class = ConditionSerializer#JSON変換のためにシリアライザを利用

    #最新の体調だけを返す
    @action(detail=False, methods=['get'])#detail=False → 一覧のような「全体」に対する処理
    def latest(self, request):
        latest_condition = self.get_queryset().first()
        if latest_condition:
            serializer = self.get_serializer(latest_condition)#ConditionSerializerを呼び出して、latest_conditionをJSON形式に変換
            return Response(serializer.data)#モデルのデータを JSON に変換して返す
        return Response({"detail": "No condition found."}, status=404)

#レシピ

    
    #self.get_serializer() は serializer_class（この場合は ConditionSerializer）を呼び出すメソッド
