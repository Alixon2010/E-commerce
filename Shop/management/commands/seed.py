import random

from django.core.management.base import BaseCommand
from faker import Faker

from Shop.models import (
    Card,
    CardProduct,
    Category,
    Order,
    OrderedProduct,
    Product,
    Profile,
    User,
)

fake = Faker()


class Command(BaseCommand):
    help = "Seed database with 50 users and 150 products using Faker"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # --- Users & Profiles ---
        users = []
        for _ in range(50):
            username = fake.user_name()
            email = fake.email()
            password = "password123"
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            Profile.objects.create(user=user, phone=fake.phone_number()[:15], img=None)
            users.append(user)

        # --- Categories ---
        categories = []
        for name in ["Electronics", "Books", "Clothing", "Toys", "Home", "Sports"]:
            cat = Category.objects.create(name=name)
            categories.append(cat)

        # --- Products ---

        products = []
        for _ in range(150):
            prod = Product.objects.create(
                name=fake.word().capitalize(),
                description=fake.text(max_nb_chars=200),
                price=round(random.uniform(10, 500), 2),
                stock=random.randint(1, 50),
                category=random.choice(categories),
                discount_percent=random.randint(0, 50),
            )
            products.append(prod)

        # --- Cards ---
        for user in users:
            card = Card.objects.create(user=user)
            for p in random.sample(products, random.randint(3, 10)):
                CardProduct.objects.create(
                    card=card, product=p, quantity=random.randint(1, 5)
                )

        # --- Orders ---
        for _ in range(100):  # создаём 100 заказов
            user = random.choice(users)
            order = Order.objects.create(
                user=user,
                status=random.choice([s[0] for s in Order.STATUS_CHOICES]),
                latitude=float(fake.latitude()),
                longitude=float(fake.longitude()),
            )
            for p in random.sample(products, random.randint(1, 8)):
                OrderedProduct.objects.create(
                    order=order, product=p, quantity=random.randint(1, 5)
                )

        self.stdout.write(
            self.style.SUCCESS("Seeding completed! 50 users and 150 products created.")
        )
