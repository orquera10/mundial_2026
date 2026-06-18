from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_partido_estado_api'),
    ]

    operations = [
        migrations.AddField(
            model_name='partido',
            name='scraper_seguimiento',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='partido',
            name='scraper_seguimiento_actualizado',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
