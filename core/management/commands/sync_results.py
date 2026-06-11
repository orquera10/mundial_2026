from django.core.management.base import BaseCommand

from core.api_integration import sync_matches_results


class Command(BaseCommand):
    help = 'Sincroniza resultados de partidos desde API externa'

    def add_arguments(self, parser):
        parser.add_argument('--date-from', default='', help='Fecha inicial en formato YYYY-MM-DD.')
        parser.add_argument('--date-to', default='', help='Fecha final en formato YYYY-MM-DD.')
        parser.add_argument(
            '--fase-previa',
            action='store_true',
            help='Sincroniza toda la fase de grupos del Mundial 2026.',
        )

    def handle(self, *args, **options):
        date_from = options['date_from']
        date_to = options['date_to']
        if options['fase_previa']:
            date_from = '2026-06-11'
            date_to = '2026-06-27'

        partidos_actualizados = sync_matches_results(date_from=date_from, date_to=date_to)
        self.stdout.write(
            self.style.SUCCESS(f'Partidos actualizados: {partidos_actualizados}')
        )
