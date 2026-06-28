from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from django.contrib.auth import get_user_model
from decouple import config

class Command(createsuperuser.Command):
    help = 'Create a superuser with a role'
    def handle(self, *args, **options):
        UserModel = get_user_model()
        # Get input manually
        username = config("ADMIN_USERNAME")
        email = config("ADMIN_EMAIL")
        password = config("ADMIN_PASSWORD")

        if not (username and email and password):
            raise CommandError("ADMIN_USERNAME, ADMIN_EMAIL, or ADMIN_PASSWORD not set")

        try:
            user, created = UserModel.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'password': password,  # will be hashed automatically
                    'is_superuser': True,
                    'is_staff': True,
                    'is_active': True,
                }
            )

            if not created:
                # Update password if needed
                user.set_password(password)
                user.save()
                print(f"Superuser '{email}' already exists, password updated.")

            self.stdout.write(self.style.SUCCESS(f"Superuser created successfully: {email}"))
        except Exception as e:
            raise CommandError(f"Error creating superuser: {str(e)}")