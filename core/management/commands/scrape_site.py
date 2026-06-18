import json

from django.core.management.base import BaseCommand, CommandError

from core.site_scraper import ScraperConfigError, scrape_page


class Command(BaseCommand):
    help = 'Prueba el scraper configurado con SCRAPER_BASE_URL.'

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            nargs='?',
            default='/',
            help='Ruta relativa al SCRAPER_BASE_URL o URL absoluta.',
        )
        parser.add_argument(
            '--include-html',
            action='store_true',
            help='Incluye el HTML completo en la salida JSON.',
        )

    def handle(self, *args, **options):
        try:
            page = scrape_page(options['path'], include_html=options['include_html'])
        except ScraperConfigError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(json.dumps(page.as_dict(options['include_html']), ensure_ascii=True, indent=2))
