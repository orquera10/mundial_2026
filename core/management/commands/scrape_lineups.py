import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.site_scraper import build_flashscore_lineups_report, scrape_page


class Command(BaseCommand):
    help = 'Scrapea formaciones de Flashscore y las cruza con JugadorSeleccion.'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            nargs='?',
            default='',
            help='URL del partido. Si se omite usa SCRAPER_BASE_URL.',
        )

    def handle(self, *args, **options):
        page = scrape_page(options['url'] or getattr(settings, 'SCRAPER_BASE_URL', ''))
        if not page.event_id:
            raise CommandError('No se pudo detectar event_id_c en la pagina de Flashscore.')

        report = build_flashscore_lineups_report(page.event_id, page.url)
        self.stdout.write(json.dumps(report, ensure_ascii=True, indent=2))
