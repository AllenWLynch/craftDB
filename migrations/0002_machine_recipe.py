# Generated by Django 2.2.4 on 2019-09-07 04:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('craftDB', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(default=1, verbose_name='Amount')),
                ('from_mod', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='craftDB.Mod', verbose_name='From Mod')),
                ('output', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='craftDB.Item', verbose_name='Output')),
            ],
            options={
                'verbose_name': 'Recipe',
                'verbose_name_plural': 'Recipes',
            },
        ),
        migrations.CreateModel(
            name='Machine',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=400)),
                ('aliases', models.ManyToManyField(blank=True, related_name='_machine_aliases_+', to='craftDB.Machine')),
            ],
        ),
    ]
