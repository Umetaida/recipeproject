from django.contrib import admin
from .models import Ingredient, Condition

@admin.register(Ingredient)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'date', 'expiry_type')

@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('status', 'created_at')


