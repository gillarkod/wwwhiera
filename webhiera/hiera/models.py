from django.db import models


class HieraMergeable(models.Model):
    merge_parameter = models.CharField(max_length=100, primary_key=True)
    default_value = models.BooleanField(default=False)
    merges_parameter = models.CharField(max_length=50)

    def __str__(self):
        return self.merge_parameter


class HieraGroup(models.Model):
    group_name = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.group_name
