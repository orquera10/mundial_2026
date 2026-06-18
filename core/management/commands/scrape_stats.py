import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.site_scraper import build_flashscore_statistics_report, scrape_page


class Command(BaseCommand):
    help = 'Scrapea estadisticas de un partido de Flashscore.'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            nargs='?',
            default='',
            help='URL del partido. Si se omite usa SCRAPER_BASE_URL.',
        )
        parser.add_argument(
            '--event-id',
            default='',
            help='Event ID de Flashscore. Si se informa, no intenta detectarlo desde la URL.',
        )

    def handle(self, *args, **options):
        url = options['url'] or getattr(settings, 'SCRAPER_BASE_URL', '')
        event_id = options['event_id']

        if event_id:
            referer_url = url or 'https://www.flashscore.com.ar/'
        else:
            page = scrape_page(url)
            if not page.event_id:
                raise CommandError('No se pudo detectar event_id_c en la pagina de Flashscore.')
            event_id = page.event_id
            referer_url = page.url

        report = build_flashscore_statistics_report(event_id, referer_url)
        self.stdout.write(json.dumps(report, ensure_ascii=True, indent=2))
