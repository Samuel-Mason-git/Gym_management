# Generated by Django 5.1.2 on 2024-12-17 17:44

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_gym_primary_owner_gymowner_is_primary_owner"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gym",
            name="primary_owner",
        ),
        migrations.RemoveField(
            model_name="gymowner",
            name="is_primary_owner",
        ),
    ]
