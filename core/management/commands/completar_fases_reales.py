from django.core.management.base import BaseCommand
from django.db import transaction

from core.knockout_rules import ANNEX_C_COLUMN_TO_MATCH, ROUND_OF_32_MATCHUPS, terceros_por_partido
from core.models import Equipo, Partido
from core.views import construir_slots_clasificados, slot_o_placeholder, tabla_desde_resultados


def obtener_secciones_grupos():
    secciones = []
    for grupo in list('ABCDEFGHIJKL'):
        equipos = list(Equipo.objects.filter(grupo=grupo).order_by('nombre'))
        if not equipos:
            continue
        partidos = list(
            Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=grupo)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero')
        )
        secciones.append(
            {
                'grupo': grupo,
                'equipos': equipos,
                'partidos': partidos,
                'tabla': tabla_desde_resultados(equipos, partidos),
            }
        )
    return secciones


def equipo_desde_slot(slot):
    if not slot or slot.get('placeholder'):
        return None
    nombre = slot.get('nombre', '').strip()
    if nombre[:1].isdigit():
        partes = nombre.split(maxsplit=1)
        nombre = partes[1] if len(partes) == 2 else nombre
    return Equipo.objects.filter(nombre=nombre).first()


def construir_cruces_16avos_oficiales(primeros, segundos, mejores_terceros):
    terceros_por_grupo = {tercero['grupo']: tercero for tercero in mejores_terceros.values()}
    terceros_por_match = terceros_por_partido(terceros_por_grupo)

    def resolver_slot(spec):
        tipo, clave, etiqueta = spec
        if tipo == 'primeros':
            return slot_o_placeholder(primeros, clave, etiqueta)
        if tipo == 'segundos':
            return slot_o_placeholder(segundos, clave, etiqueta)
        if tipo == 'terceros':
            return terceros_por_match.get(ANNEX_C_COLUMN_TO_MATCH[clave]) or slot_o_placeholder({}, clave, etiqueta)
        return slot_o_placeholder({}, clave, etiqueta)

    return {
        numero: (resolver_slot(local), resolver_slot(visitante))
        for numero, (local, visitante) in ROUND_OF_32_MATCHUPS.items()
    }


class Command(BaseCommand):
    help = 'Completa los 16avos con los clasificados reales segun el cuadro oficial FIFA.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Calculando clasificados de la fase de grupos...')
        secciones_grupos = obtener_secciones_grupos()
        primeros, segundos, mejores_terceros = construir_slots_clasificados(secciones_grupos)
        cruces_16avos = construir_cruces_16avos_oficiales(primeros, segundos, mejores_terceros)

        partidos_actualizados = 0
        for partido in Partido.objects.filter(fase=Partido.FASE_16AVOS).order_by('numero'):
            local_slot, visitante_slot = cruces_16avos.get(partido.numero, ({}, {}))
            equipo_local_nuevo = equipo_desde_slot(local_slot)
            equipo_visitante_nuevo = equipo_desde_slot(visitante_slot)

            if partido.equipo_local == equipo_local_nuevo and partido.equipo_visitante == equipo_visitante_nuevo:
                continue

            partido.equipo_local = equipo_local_nuevo
            partido.equipo_visitante = equipo_visitante_nuevo
            partido.save(update_fields=['equipo_local', 'equipo_visitante'])
            partidos_actualizados += 1
            self.stdout.write(
                f'  -> Partido {partido.numero}: {partido.local_nombre} vs {partido.visitante_nombre}'
            )

        self.stdout.write(
            self.style.SUCCESS(f'Proceso completado. 16avos actualizados: {partidos_actualizados}.')
        )
