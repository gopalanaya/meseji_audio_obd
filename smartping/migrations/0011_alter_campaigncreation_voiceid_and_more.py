# Generated by Django 5.1.1 on 2025-03-13 05:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartping', '0010_alter_voxupload_plantype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaigncreation',
            name='voiceId',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='smartping.voxupload', to_field='voiceid'),
        ),
        migrations.AlterField(
            model_name='voxupload',
            name='voiceid',
            field=models.CharField(blank=True, max_length=15),
        ),
    ]
