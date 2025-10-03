from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50, blank=True, null=True)
    date = models.CharField(max_length=50, blank=True, null=True)

class Condition(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # 保存時の日時
    status = models.CharField(max_length=100)

    def __str__(self):#管理画面での表示
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} - {self.status}"

