#!/usr/bin/env python
import argparse
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def main():
    import django

    django.setup()

    from core.api_integration import sync_due_matches_results, sync_matches_results
    from core.management.commands.sync_results import FASE_PREVIA_DATE_FROM, FASE_PREVIA_DATE_TO

    parser = argparse.ArgumentParser(
        description='Sincroniza resultados de partidos una sola vez y termina.'
    )
    parser.add_argument(
        '--date-from',
        default=os.environ.get('RESULTS_SYNC_DATE_FROM', ''),
        help='Fecha inicial en formato YYYY-MM-DD. Tambien puede venir de RESULTS_SYNC_DATE_FROM.',
    )
    parser.add_argument(
        '--date-to',
        default=os.environ.get('RESULTS_SYNC_DATE_TO', ''),
        help='Fecha final en formato YYYY-MM-DD. Tambien puede venir de RESULTS_SYNC_DATE_TO.',
    )
    parser.add_argument(
        '--fase-previa',
        action='store_true',
        default=os.environ.get('RESULTS_SYNC_FASE_PREVIA', '').lower() in {'1', 'true', 'yes', 'si'},
        help='Con --force-range usa el rango completo de fase de grupos del Mundial 2026.',
    )
    parser.add_argument(
        '--follow-hours',
        type=int,
        default=int(os.environ.get('RESULTS_SYNC_FOLLOW_HOURS', '12')),
        help='Horas posteriores al inicio en las que un partido no finalizado se sigue consultando.',
    )
    parser.add_argument(
        '--force-range',
        action='store_true',
        default=os.environ.get('RESULTS_SYNC_FORCE_RANGE', '').lower() in {'1', 'true', 'yes', 'si'},
        help='Fuerza la sincronizacion por rango. Sin esto usa modo inteligente para Coolify.',
    )
    args = parser.parse_args()

    if not args.force_range:
        result = sync_due_matches_results(
            follow_hours=args.follow_hours,
        )
        mensaje = result.get('mensaje', '')
        print(
            (
                f"Partidos consultados: {result.get('consultados', 0)}. "
                f"Partidos actualizados: {result.get('actualizados', 0)}. "
                f"{mensaje}"
            ).strip()
        )
        if result.get('date_from') and result.get('date_to'):
            print(f"Rango API consultado: {result['date_from']} a {result['date_to']}")
        return

    date_from = args.date_from
    date_to = args.date_to
    if args.fase_previa:
        date_from = FASE_PREVIA_DATE_FROM
        date_to = FASE_PREVIA_DATE_TO

    updated = sync_matches_results(date_from=date_from, date_to=date_to)
    print(f'Partidos actualizados: {updated}')


if __name__ == '__main__':
    main()
