import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Pay to becomes a Corporation instead of free text.

    Remove and add rather than AlterField: converting the text column in place
    would have to cast '' and names to an integer key, which MySQL refuses.
    The old text is dropped; it was a hint, not data anything depends on.
    """

    dependencies = [
        ("eos_invoices", "0001_initial"),
        ("eveonline", "0025_remove_evecharacter_last_updated_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="paymentsource",
            name="pay_to",
        ),
        migrations.AddField(
            model_name="paymentsource",
            name="pay_to",
            field=models.ForeignKey(
                blank=True,
                help_text="The Corporation that receives the ISK. Lists the Corporations of the Alliance chosen on the Alliance tab.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="eveonline.evecorporationinfo",
                verbose_name="Pay to",
            ),
        ),
    ]
