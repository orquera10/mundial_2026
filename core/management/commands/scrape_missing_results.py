from datetime import date

from django.core.management.base import BaseCommand

from core.models import Partido
from core.site_scraper import (
    fetch_flashscore_worldcup_matches,
    find_flashscore_match_for_partido,
    flashscore_match_for_partido_in_matches,
)
from core.views import (
    persistir_marcador_scraper,
    scraper_score_payload,
    scraper_tracking_complete,
    scraper_tracking_data,
)


FASE_GRUPOS_DATE_FROM = '2026-06-11'
FASE_GRUPOS_DATE_TO = '2026-06-30'


def parse_date(value, option_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'{option_name} debe tener formato YYYY-MM-DD.') from exc


def partido_necesita_resultado(partido):
    return (
        partido.estado != Partido.ESTADO_FINALIZADO
        or partido.goles_local is None
        or partido.goles_visitante is None
    )


def partido_tiene_snapshot_completo(partido):
    cached = partido.scraper_seguimiento or {}
    scraper = cached.get('scraper') or {}
    return bool(cached.get('complete') and scraper_tracking_complete(scraper))


class Command(BaseCommand):
    help = (
        'Scrapea resultados faltantes desde Flashscore y, si el partido finalizo, '
        'guarda la misma informacion de seguimiento que usa el detalle del partido.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--date-from', default='', help='Fecha inicial YYYY-MM-DD.')
        parser.add_argument('--date-to', default='', help='Fecha final YYYY-MM-DD.')
        parser.add_argument(
            '--fase-previa',
            action='store_true',
            help='Usa el rango completo de fase de grupos: 2026-06-11 a 2026-06-30.',
        )
        parser.add_argument(
            '--fase-final',
            action='store_true',
            help='Incluye solo partidos desde 16avos en adelante.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Revisa todos los partidos del rango aunque ya tengan resultado.',
        )
        parser.add_argument(
            '--skip-tracking',
            action='store_true',
            help='Solo persiste marcador/estado; no scrapea resumen, estadisticas, formaciones ni reporte.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra que actualizaria sin guardar cambios.',
        )
        parser.add_argument(
            '--source-url',
            default='',
            help='URL de Flashscore a leer antes del fallback, por ejemplo la pagina /resultados/.',
        )
        parser.add_argument(
            '--feed',
            default='',
            help='Feed de Flashscore a leer antes del fallback, por ejemplo f_1_-1_2_es-ar_1.',
        )

    def handle(self, *args, **options):
        date_from = options['date_from']
        date_to = options['date_to']
        if options['fase_previa']:
            date_from = FASE_GRUPOS_DATE_FROM
            date_to = FASE_GRUPOS_DATE_TO

        try:
            parsed_from = parse_date(date_from, '--date-from')
            parsed_to = parse_date(date_to, '--date-to')
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        partidos = Partido.objects.select_related('equipo_local', 'equipo_visitante').filter(
            equipo_local__isnull=False,
            equipo_visitante__isnull=False,
        )
        if parsed_from:
            partidos = partidos.filter(fecha__gte=parsed_from)
        if parsed_to:
            partidos = partidos.filter(fecha__lte=parsed_to)
        if options['fase_previa']:
            partidos = partidos.filter(fase=Partido.FASE_GRUPOS)
        if options['fase_final']:
            partidos = partidos.exclude(fase=Partido.FASE_GRUPOS)
        partidos = list(partidos.order_by('fecha', 'hora', 'numero'))
        if not options['all']:
            partidos = [
                partido
                for partido in partidos
                if partido_necesita_resultado(partido)
                or (not options['skip_tracking'] and not partido_tiene_snapshot_completo(partido))
            ]
        self.stdout.write(f'Partidos a revisar: {len(partidos)}')

        encontrados = 0
        marcador_actualizado = 0
        tracking_guardado = 0
        sin_match = 0
        sin_score = 0
        errores = 0
        source_matches = []

        if options['source_url'] or options['feed']:
            try:
                report = fetch_flashscore_worldcup_matches(
                    feed_name=options['feed'] or None,
                    source_url=options['source_url'] if options['source_url'] else '',
                )
            except Exception as exc:
                errores += 1
                self.stderr.write(f'Error leyendo fuente Flashscore: {exc}')
            else:
                source_matches = report.get('matches', [])
                self.stdout.write(f'Partidos en fuente Flashscore: {len(source_matches)}')

        for partido in partidos:
            try:
                match = flashscore_match_for_partido_in_matches(partido, source_matches) if source_matches else None
                if not match:
                    match = find_flashscore_match_for_partido(partido)
            except Exception as exc:
                errores += 1
                self.stderr.write(f'Partido {partido.numero}: error buscando en Flashscore: {exc}')
                continue

            if not match:
                sin_match += 1
                self.stdout.write(f'Partido {partido.numero}: sin match en Flashscore.')
                continue

            encontrados += 1
            payload = scraper_score_payload(match)
            if not payload:
                sin_score += 1
                self.stdout.write(f'Partido {partido.numero}: encontrado, sin marcador aun.')
                continue

            resumen = (
                f"Partido {partido.numero}: {partido.local_nombre} {payload['marcador']} "
                f"{partido.visitante_nombre} ({payload['estado']})"
            )
            if options['dry_run']:
                self.stdout.write(f'[dry-run] {resumen}')
                continue

            if persistir_marcador_scraper(partido, match):
                marcador_actualizado += 1
                partido.refresh_from_db()
                self.stdout.write(f'Actualizado marcador: {resumen}')
            else:
                self.stdout.write(f'Sin cambios de marcador: {resumen}')

            if options['skip_tracking'] or payload['estado'] != Partido.ESTADO_FINALIZADO:
                continue

            if partido_tiene_snapshot_completo(partido):
                continue

            data = scraper_tracking_data(partido, scraped_match=match, persist_snapshot=True)
            partido.refresh_from_db()
            if partido_tiene_snapshot_completo(partido):
                tracking_guardado += 1
                self.stdout.write(f'Guardado seguimiento completo: Partido {partido.numero}')
            else:
                disponibles = [
                    key.replace('_available', '')
                    for key, value in (data.get('scraper') or {}).items()
                    if key.endswith('_available') and value
                ]
                detalle = ', '.join(disponibles) or 'sin bloques completos'
                self.stdout.write(f'Seguimiento incompleto: Partido {partido.numero} ({detalle})')

        self.stdout.write(
            self.style.SUCCESS(
                'Resumen: '
                f'encontrados={encontrados}, '
                f'marcadores_actualizados={marcador_actualizado}, '
                f'tracking_guardado={tracking_guardado}, '
                f'sin_match={sin_match}, '
                f'sin_score={sin_score}, '
                f'errores={errores}'
            )
        )
