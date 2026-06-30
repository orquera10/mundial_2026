from django.core.management.base import BaseCommand

from core.models import Partido


class Command(BaseCommand):
    help = 'Normaliza marcadores de partidos definidos por penales usando el snapshot de Flashscore.'

    def handle(self, *args, **options):
        revisados = 0
        actualizados = 0
        con_penales = 0

        partidos = Partido.objects.exclude(scraper_seguimiento={}).order_by('numero')
        for partido in partidos:
            revisados += 1
            info = partido.info_penales()
            if not info:
                continue

            con_penales += 1
            update_fields = []
            if partido.goles_local != info['goles_local']:
                partido.goles_local = info['goles_local']
                update_fields.append('goles_local')
            if partido.goles_visitante != info['goles_visitante']:
                partido.goles_visitante = info['goles_visitante']
                update_fields.append('goles_visitante')
            marcador_normalizado = f"{info['goles_local']} - {info['goles_visitante']}"
            nota_penales = partido.nota_penales
            seguimiento = dict(partido.scraper_seguimiento or {})
            if seguimiento.get('marcador') != marcador_normalizado or seguimiento.get('nota_penales') != nota_penales:
                seguimiento['marcador'] = marcador_normalizado
                seguimiento['nota_penales'] = nota_penales
                partido.scraper_seguimiento = seguimiento
                update_fields.append('scraper_seguimiento')

            if update_fields:
                partido.save(update_fields=sorted(set(update_fields)))
                actualizados += 1
                estado = 'actualizado'
            else:
                estado = 'ok'

            self.stdout.write(
                f'Partido {partido.numero}: {partido.local_nombre} {partido.marcador} '
                f'{partido.visitante_nombre} - {partido.nota_penales} ({estado})'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Revisados: {revisados}. Con penales: {con_penales}. Actualizados: {actualizados}.'
            )
        )
