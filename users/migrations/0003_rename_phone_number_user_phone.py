# Generated by Django 4.2.3 on 2023-08-31 18:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_email_confirm_key_user_email_is_confirmed_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='phone_number',
            new_name='phone',
        ),
    ]
