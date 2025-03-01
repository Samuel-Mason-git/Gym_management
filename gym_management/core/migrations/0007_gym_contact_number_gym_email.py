# Generated by Django 5.1.2 on 2024-12-16 20:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_member_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="gym",
            name="contact_number",
            field=models.CharField(max_length=15, null=True),
        ),
        migrations.AddField(
            model_name="gym",
            name="email",
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
    ]
