# Generated by Django 5.1.2 on 2024-12-18 19:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_remove_gym_primary_owner_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="gymowner",
            name="is_primary_owner",
            field=models.BooleanField(default=False),
        ),
    ]
