# Generated by Django 5.1.2 on 2024-12-18 23:16

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_gymownership"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gymowner",
            name="is_primary_owner",
        ),
    ]