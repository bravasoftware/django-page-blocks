# Generated by Django 3.2.5 on 2022-03-16 11:50

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pageblocks', '0003_auto_20211107_1804'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='pageblocks/%Y/%m/%d/')),
            ],
        ),
    ]