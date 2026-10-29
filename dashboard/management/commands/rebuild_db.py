import importlib.util
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Observation, Table


class Command(BaseCommand):
    help = (
        "Build or refresh db.sqlite3 from the files in git: migrate, load_tables, load_metrics, "
        "then verify_pdfs if the PDFs are in docs/. Safe to re-run; keeps admin accounts and "
        "reviewers' verified flags and notes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--tables", default=str(settings.BASE_DIR / "tables.json"))
        parser.add_argument("--docs", default=str(settings.BASE_DIR / "docs"))
        parser.add_argument("--skip-verify", action="store_true", help="Don't check values against the PDFs.")

    def handle(self, *args, **opts):
        steps = [
            ("Creating/updating database tables (migrate)", "migrate", [], {"interactive": False}),
            ("Loading extracted tables (load_tables)", "load_tables", [opts["tables"]], {}),
            ("Building metrics (load_metrics)", "load_metrics", [], {}),
        ]
        for i, (label, command, args, kwargs) in enumerate(steps, 1):
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{i}/4] {label}"))
            call_command(command, *args, verbosity=0 if command == "migrate" else 1, **kwargs)

        self.stdout.write(self.style.MIGRATE_HEADING("[4/4] Checking values against the PDFs (verify_pdfs)"))
        skip = self.verify_skip_reason(opts)
        if skip:
            self.stdout.write(self.style.WARNING(f"  Skipped: {skip}"))
        else:
            try:
                call_command("verify_pdfs", docs=opts["docs"])
            except CommandError as e:
                self.stdout.write(self.style.WARNING(f"  Skipped: {e}"))

        verified = Observation.objects.filter(verified=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"Database ready: {Table.objects.count()} tables, {Observation.objects.count()} observations "
            f"({verified} verified). Start the site with: python manage.py runserver"
        ))

    def verify_skip_reason(self, opts):
        if opts["skip_verify"]:
            return "--skip-verify given."
        if importlib.util.find_spec("pypdf") is None:
            return "pypdf is not installed (pip install -r requirements.txt)."
        if not any(Path(opts["docs"]).glob("*.pdf")):
            return f"no PDFs in {opts['docs']} (they're git-ignored; copy them in to verify)."
        return None
