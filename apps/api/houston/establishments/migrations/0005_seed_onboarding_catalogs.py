from django.db import migrations


MODULES = [
    ("hotel", "Hotel"),
    ("restaurant", "Restaurant"),
    ("bar", "Bar"),
    ("rooftop", "Rooftop"),
    ("seminar_rooms", "Seminar rooms"),
    ("coworking", "Coworking"),
]

DOMAINS = [
    ("maintenance", "Maintenance"),
    ("housekeeping", "Housekeeping"),
    ("cleaning", "Cleaning"),
    ("security", "Security"),
    ("guest_experience", "Guest experience"),
    ("kitchen", "Kitchen"),
    ("restaurant_room", "Restaurant room"),
    ("pricing", "Pricing"),
    ("event_management", "Event management"),
    ("management", "Management"),
]

UNITS = [
    ("lobby", "Lobby"),
    ("rooms", "Rooms"),
    ("corridors", "Corridors"),
    ("restaurant", "Restaurant"),
    ("kitchen", "Kitchen"),
    ("bar", "Bar"),
    ("rooftop", "Rooftop"),
    ("seminar_rooms", "Seminar rooms"),
    ("storage", "Storage"),
    ("technical_rooms", "Technical rooms"),
    ("outdoor_areas", "Outdoor areas"),
]


def seed_catalog(apps, schema_editor):
    catalog_sets = [
        ("OnboardingCatalogModule", MODULES),
        ("OnboardingCatalogDomain", DOMAINS),
        ("OnboardingCatalogUnit", UNITS),
    ]
    for model_name, rows in catalog_sets:
        model = apps.get_model("establishments", model_name)
        for sort_order, (key, label) in enumerate(rows, start=10):
            model.objects.update_or_create(
                key=key,
                defaults={
                    "label": label,
                    "description": "",
                    "active": True,
                    "sort_order": sort_order,
                },
            )


def unseed_catalog(apps, schema_editor):
    catalog_sets = [
        ("OnboardingCatalogModule", MODULES),
        ("OnboardingCatalogDomain", DOMAINS),
        ("OnboardingCatalogUnit", UNITS),
    ]
    for model_name, rows in catalog_sets:
        model = apps.get_model("establishments", model_name)
        model.objects.filter(key__in=[key for key, _label in rows]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0004_onboardingcatalogdomain_onboardingcatalogmodule_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, unseed_catalog),
    ]
