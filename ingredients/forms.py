from django import forms
from .models import Ingredient
from django.core.exceptions import ValidationError
from django.forms.widgets import DateInput
from django.utils import timezone

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ["name", "quantity", "date", "expiry_type"]
        widgets={
            "date": DateInput(
                attrs={
                    "type": "date",#カレンダーを表示させる
                },
                format="%Y-%m-%d"
            )
        }
    
    def clean_date(self):#日付判定
        date = self.cleaned_data.get("date")
        today = timezone.now().date()
        
        if date < today:
            raise ValidationError("期限は今日以降の日付を選択してください。")
        
        return date

