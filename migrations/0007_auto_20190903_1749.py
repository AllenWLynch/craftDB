# Generated by Django 2.2.4 on 2019-09-03 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('craftDB', '0006_auto_20190903_1742'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='sprite',
            field=models.ImageField(default='/media/sprites/default.jpg', upload_to='sprites/'),
        ),
    ]
