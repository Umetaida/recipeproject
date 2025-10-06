from django.db import models

class Ingredient(models.Model):
    EXPIRY_TYPE_CHOICES = [
        ('賞味期限', '賞味期限'),
        ('消費期限', '消費期限'),
    ]
    
    name = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50, blank=True, null=True)
    date = models.CharField(max_length=50, blank=True, null=True)
    expiry_type = models.CharField(
        max_length=10,
        choices=EXPIRY_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name="期限の種類"
    )

class Condition(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # 保存時の日時
    status = models.CharField(max_length=100)

    def __str__(self):#管理画面での表示
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} - {self.status}"

