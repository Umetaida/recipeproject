from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView
from .models import Ingredient, Condition
from .serializers import IngredientSerializer, ConditionSerializer
from .forms import IngredientForm
import requests, json, random
import re
import os
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt

# ===== 汎用ビュー部分（HTML表示用） =====
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


# ===== API部分（JSON返却用） =====
class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class ConditionViewSet(viewsets.ModelViewSet):
    queryset = Condition.objects.all().order_by("-created_at")
    serializer_class = ConditionSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if "expiry_type" not in data or data["expiry_type"] == "":
            data["expiry_type"] = None
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=["get"])
    def latest(self, request):
        latest_condition = self.get_queryset().first()
        if latest_condition:
            serializer = self.get_serializer(latest_condition)
            return Response(serializer.data)
        return Response({"detail": "No condition found."}, status=404)


# ===== Helper: レシピデータ正規化 =====
def _normalize_recipe(raw):
    """
    外部APIやAIの出力でフィールド名がブレる可能性があるため
    必須のキーで埋める（空欄でも必ずキーを持つようにする）
    """
    # まず取り得る材料フィールドを探す
    materials = raw.get("recipeMaterial") or raw.get("ingredients") or raw.get("recipe_material") or raw.get("materials") or []
    if isinstance(materials, str):
        # カンマや日本語の区切りに対応
        materials = re.split(r'[、,，\n]+', materials)
        materials = [m.strip() for m in materials if m.strip()]

    # used_ingredients がすでにあれば使う（AIが付与してくる場合）
    used = raw.get("used_ingredients") or raw.get("usedIngredients") or raw.get("used_ingredients_list") or []
    if isinstance(used, str):
        used = re.split(r'[、,，\n]+', used)
        used = [u.strip() for u in used if u.strip()]

    return {
        "id": raw.get("id"),
        "recipeId": str(raw.get("recipeId") or raw.get("id") or ""),
        "recipeTitle": raw.get("recipeTitle") or raw.get("title") or raw.get("recipe_title") or raw.get("catch_copy") or "",
        "recipeDescription": raw.get("recipeDescription") or raw.get("catch_copy") or raw.get("recipe_description") or raw.get("description") or "",
        "foodImageUrl": raw.get("foodImageUrl") or raw.get("image") or raw.get("imageUrl") or raw.get("foodImageUrl") or "",
        "recipeUrl": raw.get("recipeUrl") or raw.get("url") or raw.get("recipeUrl") or "",
        "recipeCost": raw.get("recipeCost") or raw.get("cost") or "",
        "recipeMaterial": list(materials),
        "instructions": raw.get("instructions") or raw.get("steps") or [],
        "used_ingredients": list(used),
        "recommendation_reason": raw.get("recommendation_reason") or raw.get("recommendation") or "",
        "main_nutrients": raw.get("main_nutrients") or raw.get("mainNutrients") or [],
        "cooking_point": raw.get("cooking_point") or raw.get("cookingPoint") or "",
    }


# ===== Gemini + 外部APIを利用したレシピ提案API =====
@csrf_exempt
@api_view(["POST"])
def ai_recipe_suggest(request):
    """
    Flutterから送られた食材リストをもとに、
    外部API＋Geminiを使って5件のレシピを提案する。
    - 登録食材は最大30件に制限
    - 同じレシピばかりにならないようランダム抽出
    - 出力フォーマットはFlutter側のRecipeモデルに完全準拠
    """
    try:
        data = request.data
        ingredients = data.get("ingredients", [])
        condition = data.get("condition", "")
        print("📦 受け取ったデータ:", data)
        print("🥕 食材リスト:", ingredients)
        print("🩺 今日の気分:", condition)

        # 🔹 食材リストを最大30件に制限（シャッフルして多様性を確保）
        if len(ingredients) > 30:
            random.shuffle(ingredients)
            ingredients = ingredients[:30]

        # ==== 外部APIからレシピデータを取得 ====
        external_api_url = "https://shokumarurecipe.onrender.com/recipes/"
        try:
            res = requests.get(external_api_url)
            res.raise_for_status()
            recipe_data = res.json()
            print("外部APIデータ取得件数:", len(recipe_data))
        except Exception as e:
            print(f"外部API取得エラー: {e}")
            return Response({"error": "外部レシピデータを取得できませんでした。"}, status=500)

        # ==== 登録食材をすべて判定して候補レシピを作成 ====
        candidate_recipes = []
        for recipe in recipe_data:
            materials = recipe.get("recipeMaterial") or []
            if isinstance(materials, str):
                materials = [m.strip() for m in re.split(r'[、,，\n]+', materials) if m.strip()]

            # 🔹 登録食材すべてを判定
            matched = [ing for ing in ingredients if any(ing == m or ing in m for m in materials)]
            if matched:
                used_list = recipe.get("usedIngredients") or []
                if isinstance(used_list, str):
                    used_list = [u.strip() for u in re.split(r'[、,，\n]+', used_list) if u.strip()]

                # 🔹 マッチした食材を usedIngredients に反映
                used_list = list(set(used_list) | set(matched))

                candidate_recipes.append({
                    **recipe,
                    "recipeMaterial": materials,
                    "usedIngredients": used_list,
                    "matched_count": len(matched),
                })

        # 🔹 使用食材数が多い順、作成日（賞味期限）順でソート
        candidate_recipes.sort(key=lambda r: (-r.get("matched_count", 0), r.get("created_at", "")))

        # ==== 候補がなければフォールバック ====
        if not candidate_recipes:
            candidate_recipes = recipe_data[:20]

        # ==== ランダムに30件選択して Gemini に渡す ====
        random.shuffle(candidate_recipes)
        candidate_recipes = candidate_recipes[:30]

        # ==== Gemini設定 ====
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.5-flash")

        # ==== Gemini プロンプト（候補レシピと使用食材を連動） ====
        prompt = f"""
        あなたは優秀な料理アドバイザーです。
        以下の条件に従って5つのレシピを提案してください。

        条件:
        - 以下の「食材リスト」から少なくとも1つ以上を含むレシピを選ぶ
        - 「食材リスト」に登録されている食材をより多く利用しているレシピを優先的に選ぶ
        - 「食材リスト」に登録されていない食材を利用するレシピは絶対に選ばないこと（例えそのレシピが体調に合っているとしても）
        - 「食材リスト」に登録されている名前そのままの食材を利用するものを選ぶこと(例：登録名が「キャベツ」の場合、冷凍ロールキャベツは登録されているレシピではない)
        - 今日の気分（体調）に合った内容にする
        - 同じようなレシピが続かないようバランスよく選ぶ
        - 出力形式は **必ず** JSON 配列のみ
        - 利用食材には利用量（100g、1玉、小さじ1杯など）も記載すること
        - 各レシピの構造は以下の通り（Flutterアプリと連携するため固定）:

        [
          {{
            "recipeId": "xxxx",
            "title": "レシピ名",
            "catch_copy": "短い説明文",
            "foodImageUrl": "https://example.com/img.jpg",
            "recipeUrl": "https://example.com",
            "recipeCost": "300円",
            "ingredients": ["玉ねぎ 1個", "にんじん 1本"],
            "instructions": ["1. 材料を切る", "2. 炒める", "3. 煮込む"],
            "recommendation_reason": "食材と体調からこのレシピを選びました。",
            "main_nutrients": ["たんぱく質", "ビタミンC"],
            "cooking_point": "焦がさないように中火で炒めましょう。"
          }},
          ...
        ]

        食材リスト: {', '.join(ingredients)}
        今日の気分: {condition or '特になし'}
        候補レシピ: {json.dumps(candidate_recipes[:15], ensure_ascii=False)}
        """

        # ==== Gemini呼び出し ====
        try:
            result = model.generate_content(prompt)
            text = result.text
            match = re.search(r"\[.*\]", text, re.DOTALL)
            if match:
                ai_recipes = json.loads(match.group(0))
            else:
                ai_recipes = []
        except Exception as e:
            print(f"Gemini処理エラー: {e}")
            ai_recipes = []

        # ==== フォールバック（Gemini失敗時） ====
        if not ai_recipes:
            random.shuffle(candidate_recipes)
            ai_recipes = candidate_recipes[:5]
            for r in ai_recipes:
                r.setdefault("instructions", ["手順情報なし"])
                r.setdefault("recommendation_reason", "登録食材に基づく提案です。")
                r.setdefault("main_nutrients", [])
                r.setdefault("cooking_point", "")
                r.setdefault("ingredients", r.get("recipeMaterial", []))

        # ==== 出力データ整形（Flutterモデルに準拠） ====
        normalized_recipes = []
        for r in ai_recipes:
            normalized = {
                "recipeId": r.get("recipeId", str(random.randint(10000, 99999))),
                "title": r.get("title") or r.get("recipeTitle") or "タイトル不明",
                "catch_copy": r.get("catch_copy") or r.get("recipeDescription") or "",
                "foodImageUrl": r.get("foodImageUrl") or r.get("foodImageURL") or "",
                "recipeUrl": r.get("recipeUrl") or "",
                "recipeCost": r.get("recipeCost") or "",
                "ingredients": r.get("ingredients") or r.get("recipeMaterial") or [],
                "instructions": r.get("instructions") or [],
                "recommendation_reason": r.get("recommendation_reason") or "",
                "main_nutrients": r.get("main_nutrients") or [],
                "cooking_point": r.get("cooking_point") or "",
                "used_ingredients": r.get("usedIngredients") or [],
            }
            normalized_recipes.append(normalized)

        return JsonResponse({"recipes": normalized_recipes}, safe=False)

    except Exception as e:
        print(f"❌ サーバー内部エラー: {e}")
        return Response({"error": str(e)}, status=500)






# ===== 保存系（簡易） =====
@csrf_exempt
@api_view(["POST"])
def save_recipe(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print("保存リクエスト受信:", data)
        # TODO: 他人のDBへPOSTするならここで requests.post(...) する
        return JsonResponse({'message': 'Recipe saved successfully'}, status=201)
    return JsonResponse({'error': 'Invalid method'}, status=405)


@csrf_exempt
def get_saved_recipes(request):
    recipes = [
        {"recipeId": "001", "recipeTitle": "テストレシピ", "recipeDescription": "説明", "recipeMaterial": ["卵", "牛乳"], "foodImageUrl": "https://example.com/test.jpg", "recipeUrl": "#", "recipeCost": "200円", "used_ingredients": ["卵"]}
    ]
    return JsonResponse(recipes, safe=False, json_dumps_params={'ensure_ascii': False})
