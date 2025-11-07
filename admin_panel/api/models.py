from django.db import models


class AllowedApi(models.Model):
    record_id = models.AutoField(unique=True, null=False, primary_key=True)
    api_key = models.CharField(unique=True, max_length=50)
    comment = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "api_allowed_keys"
        verbose_name_plural = "Допустимі api key"

    def __str__(self):
        return f"{self.api_key}: {self.comment}"


class ApiReqLog(models.Model):
    record_id = models.AutoField(unique=True, null=False, primary_key=True)
    headers = models.BinaryField()
    body = models.BinaryField()
    ip_address = models.CharField(max_length=20)
    date = models.DateTimeField()

    def __str__(self):
        return f"Запит {self.record_id}"

    class Meta:
        db_table = "api_requests_log"
        verbose_name_plural = "Лог запитів до апі"
