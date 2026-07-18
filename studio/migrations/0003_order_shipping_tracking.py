from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("studio", "0002_commerce_and_jobs")]
    operations = [
        migrations.AddField(
            model_name="order",
            name="carrier",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="order",
            name="shipped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
