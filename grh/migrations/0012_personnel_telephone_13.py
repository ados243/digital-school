from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("grh", "0011_edt_et_mobile_money"),
    ]

    operations = [
        migrations.AlterField(
            model_name="personnel",
            name="telephone",
            field=models.CharField(max_length=13),
        ),
    ]
