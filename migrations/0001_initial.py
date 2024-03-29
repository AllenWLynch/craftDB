# Generated by Django 2.2.4 on 2019-09-07 04:13

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(max_length=300, verbose_name='Item Name')),
                ('itemid', models.CharField(max_length=300, verbose_name='ID')),
                ('stack', models.IntegerField(default=64, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(64)], verbose_name='Stack Size')),
                ('sprite', models.ImageField(default='/media/sprites/default.jpg', upload_to='sprites/')),
                ('base_resource', models.BooleanField(default=False, verbose_name='Base Resource')),
            ],
        ),
        migrations.CreateModel(
            name='Mod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('abbrevations', models.CharField(default='', max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='OreDict',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('leading_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lead', to='craftDB.Item', verbose_name='Representative Item')),
            ],
            options={
                'verbose_name': 'Ore Dictionary',
                'verbose_name_plural': 'Ore Dictionaries',
            },
        ),
        migrations.AddField(
            model_name='item',
            name='mod',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='craftDB.Mod', verbose_name='Source Mod'),
        ),
        migrations.AddField(
            model_name='item',
            name='oredict',
            field=models.ManyToManyField(blank=True, to='craftDB.OreDict', verbose_name='Ore Dictionary'),
        ),
    ]
