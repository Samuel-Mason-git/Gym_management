# Generated by Django 5.1.2 on 2024-12-17 17:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_gym_contact_number_gym_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="gym",
            name="primary_owner",
            field=models.ForeignKey(
                default=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="primary_own",
                to="core.gymowner",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="gymowner",
            name="is_primary_owner",
            field=models.BooleanField(default=False),
        ),
    ]