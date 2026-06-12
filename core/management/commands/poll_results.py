import os
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.api_integration import sync_matches_results
from core.management.commands.sync_results import FASE_PREVIA_DATE_FROM, FASE_PREVIA_DATE_TO


class Command(BaseCommand):
    help = 'Sincroniza resultados de partidos en un loop para usar como worker.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=int(os.environ.get('RESULTS_POLL_INTERVAL', '300')),
            help='Segundos entre sincronizaciones. Por defecto usa RESULTS_POLL_INTERVAL o 300.',
        )
        parser.add_argument(
            '--date-from',
            default=os.environ.get('RESULTS_POLL_DATE_FROM', ''),
            help='Fecha inicial en formato YYYY-MM-DD.',
        )
        parser.add_argument(
            '--date-to',
            default=os.environ.get('RESULTS_POLL_DATE_TO', ''),
            help='Fecha final en formato YYYY-MM-DD.',
        )
        parser.add_argument(
            '--fase-previa',
            action='store_true',
            help='Sincroniza toda la fase de grupos del Mundial 2026.',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Ejecuta una sola sincronizacion y termina.',
        )

    def handle(self, *args, **options):
        interval = max(options['interval'], 30)
        date_from = options['date_from']
        date_to = options['date_to']

        if options['fase_previa']:
            date_from = FASE_PREVIA_DATE_FROM
            date_to = FASE_PREVIA_DATE_TO

        while True:
            timestamp = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S')
            try:
                partidos_actualizados = sync_matches_results(date_from=date_from, date_to=date_to)
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f'[{timestamp}] Error sincronizando resultados: {exc}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[{timestamp}] Partidos actualizados: {partidos_actualizados}'
                    )
                )

            if options['once']:
                break

            time.sleep(interval)
