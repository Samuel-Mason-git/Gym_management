# Generated by Django 5.1.2 on 2024-11-23 15:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_gym_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="gym",
            name="slug",
            field=models.SlugField(blank=True, unique=True),
        ),
    ]