import json

from django.core.management.base import BaseCommand

from core.site_scraper import fetch_flashscore_worldcup_matches


class Command(BaseCommand):
    help = 'Extrae links de partidos del Mundial desde la pagina principal/feed de Flashscore.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            default='',
            help='URL de Flashscore a scrapear. Si se omite usa SCRAPER_BASE_URL.',
        )
        parser.add_argument(
            '--block',
            default='',
            help='Bloque cjs.initialFeeds a leer, por ejemplo fixtures o summary-fixtures.',
        )
        parser.add_argument(
            '--feed',
            default='',
            help='Nombre del feed de Flashscore para fallback. Por defecto usa SCRAPER_FLASHSCORE_TODAY_FEED.',
        )

    def handle(self, *args, **options):
        source_url = options['url'] or None
        if options['feed'] and not source_url and not options['block']:
            source_url = ''
        report = fetch_flashscore_worldcup_matches(
            feed_name=options['feed'] or None,
            source_url=source_url,
            block_name=options['block'] or None,
        )
        self.stdout.write(json.dumps(report, ensure_ascii=True, indent=2))
