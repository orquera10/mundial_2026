from django.contrib import messages
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegistroUsuarioForm
from .models import Equipo, EquipoFavorito, Partido, PartidoFavorito, Prediccion, bandera_url
from .site_scraper import (
    build_flashscore_lineups_report,
    build_flashscore_report,
    build_flashscore_statistics_report,
    build_flashscore_summary_report,
    fetch_flashscore_worldcup_matches,
    flashscore_daily_feed_name,
    flashscore_match_for_partido_in_matches,
    flashscore_team_name,
    find_flashscore_match_for_partido,
    summarize_lineups_for_tracking,
)
from .stadium_data import ESTADIOS_2026


CONFEDERACIONES = {
    'Algeria': ('CAF', 'Africa'),
    'Argentina': ('CONMEBOL', 'Sudamerica'),
    'Australia': ('AFC', 'Asia-Pacifico'),
    'Austria': ('UEFA', 'Europa'),
    'Belgium': ('UEFA', 'Europa'),
    'Bosnia and Herzegovina': ('UEFA', 'Europa'),
    'Brazil': ('CONMEBOL', 'Sudamerica'),
    'Cabo Verde': ('CAF', 'Africa'),
    'Canada': ('CONCACAF', 'Norteamerica'),
    'Colombia': ('CONMEBOL', 'Sudamerica'),
    'Congo DR': ('CAF', 'Africa'),
    "Cote d'Ivoire": ('CAF', 'Africa'),
    'Croatia': ('UEFA', 'Europa'),
    'Curacao': ('CONCACAF', 'Caribe'),
    'Czechia': ('UEFA', 'Europa'),
    'Ecuador': ('CONMEBOL', 'Sudamerica'),
    'Egypt': ('CAF', 'Africa'),
    'England': ('UEFA', 'Europa'),
    'France': ('UEFA', 'Europa'),
    'Germany': ('UEFA', 'Europa'),
    'Ghana': ('CAF', 'Africa'),
    'Haiti': ('CONCACAF', 'Caribe'),
    'IR Iran': ('AFC', 'Asia'),
    'Iraq': ('AFC', 'Asia'),
    'Japan': ('AFC', 'Asia'),
    'Jordan': ('AFC', 'Asia'),
    'Korea Republic': ('AFC', 'Asia'),
    'Mexico': ('CONCACAF', 'Norteamerica'),
    'Morocco': ('CAF', 'Africa'),
    'Netherlands': ('UEFA', 'Europa'),
    'New Zealand': ('OFC', 'Oceania'),
    'Norway': ('UEFA', 'Europa'),
    'Panama': ('CONCACAF', 'Centroamerica'),
    'Paraguay': ('CONMEBOL', 'Sudamerica'),
    'Portugal': ('UEFA', 'Europa'),
    'Qatar': ('AFC', 'Asia'),
    'Saudi Arabia': ('AFC', 'Asia'),
    'Scotland': ('UEFA', 'Europa'),
    'Senegal': ('CAF', 'Africa'),
    'South Africa': ('CAF', 'Africa'),
    'Spain': ('UEFA', 'Europa'),
    'Sweden': ('UEFA', 'Europa'),
    'Switzerland': ('UEFA', 'Europa'),
    'Tunisia': ('CAF', 'Africa'),
    'Turkiye': ('UEFA', 'Europa'),
    'Uruguay': ('CONMEBOL', 'Sudamerica'),
    'USA': ('CONCACAF', 'Norteamerica'),
    'Uzbekistan': ('AFC', 'Asia'),
}

PLANTELES_CONFIRMADOS = {}
TECNICOS_CONFIRMADOS = {}



def url_volver(request, fallback):
    referer = request.META.get('HTTP_REFERER', '')
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return referer
    return resolve_url(fallback)


def agrupar_partidos(partidos):
    secciones = []
    grupos = list('ABCDEFGHIJKL')
    partidos = list(partidos)

    for grupo in grupos:
        items = [partido for partido in partidos if partido.grupo == grupo]
        if items:
            equipos = []
            vistos = set()
            for partido in items:
                for equipo in (partido.equipo_local, partido.equipo_visitante):
                    if equipo and equipo.id not in vistos:
                        vistos.add(equipo.id)
                        equipos.append(equipo)
            secciones.append({'titulo': f'Grupo {grupo}', 'partidos': items, 'equipos': equipos})

    fases = dict(Partido.FASES)
    for fase, nombre in Partido.FASES:
        if fase == Partido.FASE_GRUPOS:
            continue
        items = [partido for partido in partidos if partido.fase == fase]
        if items:
            secciones.append({'titulo': fases[fase], 'partidos': items, 'equipos': []})

    return secciones


def secciones_prediccion_grupos(predicciones_por_partido):
    secciones = []
    for grupo in list('ABCDEFGHIJKL'):
        equipos = list(Equipo.objects.filter(grupo=grupo).order_by('nombre'))
        partidos = anotar_predicciones(
            Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=grupo)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero'),
            predicciones_por_partido,
        )
        secciones.append(
            {
                'grupo': grupo,
                'equipos': equipos,
                'partidos': partidos,
                'tabla': tabla_desde_predicciones(equipos, partidos),
            }
        )
    return secciones


def anotar_predicciones(partidos, predicciones_por_partido):
    partidos = list(partidos)
    for partido in partidos:
        partido.prediccion_usuario = predicciones_por_partido.get(partido.id)
    return partidos


def scraper_score_payload(match):
    score = (match or {}).get('score') or {}
    score_home = score.get('home', '')
    score_away = score.get('away', '')
    if score_home == '' or score_away == '':
        return None
    status = (match or {}).get('status', '')
    return {
        'marcador': f'{score_home} - {score_away}',
        'estado': status,
        'estado_display': scraper_status_display(status),
        'goles_local': int(score_home) if str(score_home).isdigit() else None,
        'goles_visitante': int(score_away) if str(score_away).isdigit() else None,
    }


def scraper_status_display(status):
    labels = {
        Partido.ESTADO_PROGRAMADO: 'Programado',
        Partido.ESTADO_EN_VIVO: 'En vivo',
        Partido.ESTADO_FINALIZADO: 'Finalizado',
    }
    return labels.get(status, status.replace('_', ' ').title() if status else '')


def aplicar_marcador_scraper(partido, match):
    payload = scraper_score_payload(match)
    if not payload:
        return partido
    partido.scraper_marcador = payload['marcador']
    partido.scraper_estado = payload['estado'] or partido.estado
    partido.scraper_estado_display = payload['estado_display'] or partido.estado_partido_label
    return partido


def aplicar_marcadores_scraper(partidos, scraped_by_id):
    for partido in partidos:
        scraped = scraped_by_id.get(partido.id)
        if scraped:
            aplicar_marcador_scraper(partido, scraped.get('match'))
    return partidos


def persistir_marcador_scraper(partido, match):
    payload = scraper_score_payload(match)
    if not payload:
        return False

    update_fields = []
    estado = payload['estado']
    if estado and partido.estado != estado:
        partido.estado = estado
        update_fields.append('estado')

    for field, value in (
        ('goles_local', payload['goles_local']),
        ('goles_visitante', payload['goles_visitante']),
    ):
        if value is not None and getattr(partido, field) != value:
            setattr(partido, field, value)
            update_fields.append(field)

    if update_fields:
        partido.save(update_fields=sorted(set(update_fields)))
        return True
    return False


def persistir_marcadores_scraper(scraped_items):
    actualizados = set()
    for scraped in scraped_items:
        if persistir_marcador_scraper(scraped['partido'], scraped.get('match')):
            actualizados.add(scraped['partido'].id)
    return actualizados


def aplicar_marcadores_snapshot(partidos):
    for partido in partidos:
        aplicar_marcador_snapshot(partido)
    return partidos


def resultados_scraper_por_partido(scraped_by_id):
    resultados = {}
    for partido_id, scraped in scraped_by_id.items():
        payload = scraper_score_payload(scraped.get('match'))
        if payload and payload['goles_local'] is not None and payload['goles_visitante'] is not None:
            resultados[partido_id] = {
                'goles_local': payload['goles_local'],
                'goles_visitante': payload['goles_visitante'],
            }
    return resultados


def resultados_snapshot_por_partido(partidos):
    resultados = {}
    for partido in partidos:
        cached = partido.scraper_seguimiento or {}
        scraper = cached.get('scraper') or {}
        if not cached.get('complete') or not scraper_tracking_complete(scraper):
            continue
        marcador = cached.get('marcador') or ''
        partes = [parte.strip() for parte in marcador.split('-', 1)]
        if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
            continue
        resultados[partido.id] = {
            'goles_local': int(partes[0]),
            'goles_visitante': int(partes[1]),
        }
    return resultados


def scraper_tracking_complete(scraper):
    return all(
        [
            scraper.get('summary_available'),
            scraper.get('statistics_available'),
            scraper.get('lineups_available'),
            scraper.get('commentary_available'),
            scraper.get('report_available'),
        ]
    )


def partido_tracking_finalizado(status):
    return status == Partido.ESTADO_FINALIZADO


def cached_tracking_response(partido, data):
    cached = partido.scraper_seguimiento or {}
    scraper = cached.get('scraper') or {}
    if not cached.get('complete') or not scraper_tracking_complete(scraper):
        return None
    data.update(
        {
            'source': 'flashscore_cache',
            'updated_at': cached.get('updated_at') or data['updated_at'],
            'estado': cached.get('estado', data['estado']),
            'estado_display': cached.get('estado_display', data['estado_display']),
            'marcador': cached.get('marcador', data['marcador']),
            'scraper': scraper,
        }
    )
    data['scraper']['message'] = 'Datos cargados desde la base local.'
    return data


def aplicar_marcador_snapshot(partido):
    cached = partido.scraper_seguimiento or {}
    scraper = cached.get('scraper') or {}
    if not cached.get('complete') or not scraper_tracking_complete(scraper):
        return False
    partido.scraper_marcador = cached.get('marcador') or '-'
    partido.scraper_estado = cached.get('estado') or partido.estado
    partido.scraper_estado_display = cached.get('estado_display') or partido.estado_partido_label
    return True


def save_tracking_snapshot_if_complete(partido, data):
    scraper = data.get('scraper') or {}
    if not partido_tracking_finalizado(scraper.get('status') or data.get('estado')):
        return False
    if not scraper_tracking_complete(scraper):
        return False
    partido.scraper_seguimiento = {
        'complete': True,
        'updated_at': data.get('updated_at'),
        'estado': data.get('estado'),
        'estado_display': data.get('estado_display'),
        'marcador': data.get('marcador'),
        'scraper': scraper,
    }
    partido.scraper_seguimiento_actualizado = timezone.now()
    partido.save(update_fields=['scraper_seguimiento', 'scraper_seguimiento_actualizado'])
    return True


def tabla_desde_predicciones(equipos, partidos):
    tabla = {
        equipo.id: {
            'equipo': equipo,
            'pj': 0,
            'pg': 0,
            'pe': 0,
            'pp': 0,
            'gf': 0,
            'gc': 0,
            'dg': 0,
            'pts': 0,
        }
        for equipo in equipos
    }

    for partido in partidos:
        prediccion = getattr(partido, 'prediccion_usuario', None)
        if not prediccion or not partido.equipo_local_id or not partido.equipo_visitante_id:
            continue

        local = tabla[partido.equipo_local_id]
        visitante = tabla[partido.equipo_visitante_id]
        goles_local = prediccion.goles_local
        goles_visitante = prediccion.goles_visitante

        local['pj'] += 1
        visitante['pj'] += 1
        local['gf'] += goles_local
        local['gc'] += goles_visitante
        visitante['gf'] += goles_visitante
        visitante['gc'] += goles_local

        if goles_local > goles_visitante:
            local['pg'] += 1
            local['pts'] += 3
            visitante['pp'] += 1
        elif goles_local < goles_visitante:
            visitante['pg'] += 1
            visitante['pts'] += 3
            local['pp'] += 1
        else:
            local['pe'] += 1
            visitante['pe'] += 1
            local['pts'] += 1
            visitante['pts'] += 1

    for fila in tabla.values():
        fila['dg'] = fila['gf'] - fila['gc']

    return sorted(
        tabla.values(),
        key=lambda fila: (-fila['pts'], -fila['dg'], -fila['gf'], fila['equipo'].nombre),
    )


def tabla_desde_resultados(equipos, partidos, resultados_en_vivo=None):
    resultados_en_vivo = resultados_en_vivo or {}
    tabla = {
        equipo.id: {
            'equipo': equipo,
            'pj': 0,
            'pg': 0,
            'pe': 0,
            'pp': 0,
            'gf': 0,
            'gc': 0,
            'dg': 0,
            'pts': 0,
        }
        for equipo in equipos
    }

    for partido in partidos:
        if not partido.equipo_local_id or not partido.equipo_visitante_id:
            continue
        resultado_en_vivo = resultados_en_vivo.get(partido.id)
        if resultado_en_vivo:
            goles_local = resultado_en_vivo.get('goles_local')
            goles_visitante = resultado_en_vivo.get('goles_visitante')
        else:
            goles_local = partido.goles_local
            goles_visitante = partido.goles_visitante
        if goles_local is None or goles_visitante is None:
            continue

        local = tabla[partido.equipo_local_id]
        visitante = tabla[partido.equipo_visitante_id]

        local['pj'] += 1
        visitante['pj'] += 1
        local['gf'] += goles_local
        local['gc'] += goles_visitante
        visitante['gf'] += goles_visitante
        visitante['gc'] += goles_local

        if goles_local > goles_visitante:
            local['pg'] += 1
            local['pts'] += 3
            visitante['pp'] += 1
        elif goles_local < goles_visitante:
            visitante['pg'] += 1
            visitante['pts'] += 3
            local['pp'] += 1
        else:
            local['pe'] += 1
            visitante['pe'] += 1
            local['pts'] += 1
            visitante['pts'] += 1

    for fila in tabla.values():
        fila['dg'] = fila['gf'] - fila['gc']

    return sorted(
        tabla.values(),
        key=lambda fila: (-fila['pts'], -fila['dg'], -fila['gf'], fila['equipo'].nombre),
    )


def equipo_slot(equipo, etiqueta=None):
    if equipo:
        return {
            'nombre': etiqueta or equipo.nombre,
            'bandera': equipo.bandera,
            'bandera_url': equipo.bandera_url,
            'placeholder': False,
        }
    return {'nombre': etiqueta or 'Clasificado', 'bandera': '🏳', 'bandera_url': ''}


def placeholder_slot(etiqueta):
    return {'nombre': etiqueta, 'bandera': '🏳', 'bandera_url': bandera_url(etiqueta)}


def aplicar_display_partido(partido, local_slot, visitante_slot):
    partido.display_local_nombre = local_slot['nombre']
    partido.display_local_bandera = local_slot['bandera']
    partido.display_local_bandera_url = local_slot['bandera_url']
    partido.display_local_placeholder = local_slot.get('placeholder', not local_slot.get('bandera_url'))
    partido.display_visitante_nombre = visitante_slot['nombre']
    partido.display_visitante_bandera = visitante_slot['bandera']
    partido.display_visitante_bandera_url = visitante_slot['bandera_url']
    partido.display_visitante_placeholder = visitante_slot.get('placeholder', not visitante_slot.get('bandera_url'))
    return partido


def construir_slots_clasificados(secciones):
    primeros = {}
    segundos = {}
    terceros = []

    for seccion in secciones:
        tabla = seccion['tabla']
        grupo = seccion['grupo']
        if not any(fila['pj'] > 0 for fila in tabla):
            continue
        if len(tabla) >= 1:
            primeros[grupo] = equipo_slot(tabla[0]['equipo'], f"1° {tabla[0]['equipo'].nombre}")
        if len(tabla) >= 2:
            segundos[grupo] = equipo_slot(tabla[1]['equipo'], f"2° {tabla[1]['equipo'].nombre}")
        if len(tabla) >= 3:
            fila = tabla[2]
            terceros.append(
                {
                    **equipo_slot(fila['equipo'], f"3° {fila['equipo'].nombre}"),
                    'pts': fila['pts'],
                    'dg': fila['dg'],
                    'gf': fila['gf'],
                    'grupo': grupo,
                }
            )

    terceros = sorted(terceros, key=lambda fila: (-fila['pts'], -fila['dg'], -fila['gf'], fila['grupo']))[:8]
    mejores_terceros = {index + 1: tercero for index, tercero in enumerate(terceros)}
    return primeros, segundos, mejores_terceros


def slot_o_placeholder(diccionario, clave, etiqueta):
    return diccionario.get(clave) or placeholder_slot(etiqueta)


def completar_fase_final(fases_finales, secciones):
    primeros, segundos, mejores_terceros = construir_slots_clasificados(secciones)
    cruces_16avos = {
        73: (slot_o_placeholder(primeros, 'A', '1° Grupo A'), slot_o_placeholder(mejores_terceros, 8, 'Mejor 3° 8')),
        74: (slot_o_placeholder(primeros, 'B', '1° Grupo B'), slot_o_placeholder(mejores_terceros, 7, 'Mejor 3° 7')),
        75: (slot_o_placeholder(primeros, 'C', '1° Grupo C'), slot_o_placeholder(mejores_terceros, 6, 'Mejor 3° 6')),
        76: (slot_o_placeholder(primeros, 'D', '1° Grupo D'), slot_o_placeholder(mejores_terceros, 5, 'Mejor 3° 5')),
        77: (slot_o_placeholder(primeros, 'E', '1° Grupo E'), slot_o_placeholder(mejores_terceros, 4, 'Mejor 3° 4')),
        78: (slot_o_placeholder(primeros, 'F', '1° Grupo F'), slot_o_placeholder(mejores_terceros, 3, 'Mejor 3° 3')),
        79: (slot_o_placeholder(primeros, 'G', '1° Grupo G'), slot_o_placeholder(mejores_terceros, 2, 'Mejor 3° 2')),
        80: (slot_o_placeholder(primeros, 'H', '1° Grupo H'), slot_o_placeholder(mejores_terceros, 1, 'Mejor 3° 1')),
        81: (slot_o_placeholder(primeros, 'I', '1° Grupo I'), slot_o_placeholder(segundos, 'L', '2° Grupo L')),
        82: (slot_o_placeholder(primeros, 'J', '1° Grupo J'), slot_o_placeholder(segundos, 'K', '2° Grupo K')),
        83: (slot_o_placeholder(primeros, 'K', '1° Grupo K'), slot_o_placeholder(segundos, 'J', '2° Grupo J')),
        84: (slot_o_placeholder(primeros, 'L', '1° Grupo L'), slot_o_placeholder(segundos, 'I', '2° Grupo I')),
        85: (slot_o_placeholder(segundos, 'A', '2° Grupo A'), slot_o_placeholder(segundos, 'B', '2° Grupo B')),
        86: (slot_o_placeholder(segundos, 'C', '2° Grupo C'), slot_o_placeholder(segundos, 'D', '2° Grupo D')),
        87: (slot_o_placeholder(segundos, 'E', '2° Grupo E'), slot_o_placeholder(segundos, 'F', '2° Grupo F')),
        88: (slot_o_placeholder(segundos, 'G', '2° Grupo G'), slot_o_placeholder(segundos, 'H', '2° Grupo H')),
    }

    partidos_por_numero = {}
    resultado_slots = {}

    for fase in fases_finales:
        for partido in fase['partidos']:
            partidos_por_numero[partido.numero] = partido
            if partido.numero in cruces_16avos:
                local_slot, visitante_slot = cruces_16avos[partido.numero]
            else:
                local_slot = resolver_slot_eliminatorio(partido.etiqueta_local, resultado_slots)
                visitante_slot = resolver_slot_eliminatorio(partido.etiqueta_visitante, resultado_slots)
            aplicar_display_partido(partido, local_slot, visitante_slot)
            resultado_slots[partido.numero] = resultado_desde_prediccion(partido)

    return fases_finales


def marcar_fase_final_como_proyeccion(fases_finales):
    for fase in fases_finales:
        for partido in fase['partidos']:
            local = getattr(partido, 'display_local_nombre', '')
            visitante = getattr(partido, 'display_visitante_nombre', '')
            if not local and not visitante:
                continue
            local_placeholder = getattr(partido, 'display_local_placeholder', False)
            visitante_placeholder = getattr(partido, 'display_visitante_placeholder', False)
            if local_placeholder and visitante_placeholder:
                continue
            partido.proyeccion_local_nombre = local
            partido.proyeccion_visitante_nombre = visitante
            partido.proyeccion_local_bandera = getattr(partido, 'display_local_bandera', '')
            partido.proyeccion_visitante_bandera = getattr(partido, 'display_visitante_bandera', '')
            partido.proyeccion_local_bandera_url = getattr(partido, 'display_local_bandera_url', '')
            partido.proyeccion_visitante_bandera_url = getattr(partido, 'display_visitante_bandera_url', '')
            partido.proyeccion_local_placeholder = local_placeholder
            partido.proyeccion_visitante_placeholder = visitante_placeholder
            for atributo in (
                'display_local_nombre',
                'display_visitante_nombre',
                'display_local_bandera',
                'display_visitante_bandera',
                'display_local_bandera_url',
                'display_visitante_bandera_url',
                'display_local_placeholder',
                'display_visitante_placeholder',
            ):
                if hasattr(partido, atributo):
                    delattr(partido, atributo)
    return fases_finales


def resolver_slot_eliminatorio(etiqueta, resultado_slots):
    partes = etiqueta.split()
    if len(partes) == 2 and partes[1].isdigit():
        numero = int(partes[1])
        resultado = resultado_slots.get(numero)
        if resultado:
            if partes[0] == 'Ganador':
                return resultado['ganador']
            if partes[0] == 'Perdedor':
                return resultado['perdedor']
    return placeholder_slot(etiqueta)


def resultado_desde_prediccion(partido):
    local = {
        'nombre': getattr(partido, 'display_local_nombre', partido.local_nombre),
        'bandera': getattr(partido, 'display_local_bandera', partido.bandera_local),
        'bandera_url': getattr(partido, 'display_local_bandera_url', partido.bandera_local_url),
    }
    visitante = {
        'nombre': getattr(partido, 'display_visitante_nombre', partido.visitante_nombre),
        'bandera': getattr(partido, 'display_visitante_bandera', partido.bandera_visitante),
        'bandera_url': getattr(partido, 'display_visitante_bandera_url', partido.bandera_visitante_url),
    }
    prediccion = getattr(partido, 'prediccion_usuario', None)
    if not prediccion or prediccion.goles_local == prediccion.goles_visitante:
        return {'ganador': placeholder_slot(f'Ganador {partido.numero}'), 'perdedor': placeholder_slot(f'Perdedor {partido.numero}')}
    if prediccion.goles_local > prediccion.goles_visitante:
        return {'ganador': local, 'perdedor': visitante}
    return {'ganador': visitante, 'perdedor': local}


def home(request):
    grupo = request.GET.get('grupo', '')
    fase = request.GET.get('fase', '')
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '').strip()
    solo_favoritos = request.GET.get('favoritos') == '1'

    partidos = Partido.objects.select_related('equipo_local', 'equipo_visitante')

    if grupo:
        partidos = partidos.filter(grupo=grupo)
    if fase:
        partidos = partidos.filter(fase=fase)
    if estado:
        partidos = partidos.filter(estado=estado)
    if busqueda:
        partidos = partidos.filter(
            Q(equipo_local__nombre__icontains=busqueda)
            | Q(equipo_visitante__nombre__icontains=busqueda)
            | Q(etiqueta_local__icontains=busqueda)
            | Q(etiqueta_visitante__icontains=busqueda)
            | Q(estadio__icontains=busqueda)
            | Q(ciudad__icontains=busqueda)
        )
    if solo_favoritos and request.user.is_authenticated:
        partidos = partidos.filter(favoritos__usuario=request.user)

    favoritos_ids = set()
    predicciones_por_partido = {}
    favoritos_partidos = []
    if request.user.is_authenticated:
        favoritos_ids = set(
            PartidoFavorito.objects.filter(usuario=request.user).values_list('partido_id', flat=True)
        )
        predicciones_por_partido = {
            prediccion.partido_id: prediccion
            for prediccion in Prediccion.objects.filter(usuario=request.user)
        }
        favoritos_partidos = list(
            Partido.objects.filter(favoritos__usuario=request.user)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero')
        )

    try:
        scraped_items = scraper_partidos_del_dia()
    except Exception:
        scraped_items = []
    persistir_marcadores_scraper(scraped_items)

    partidos = anotar_predicciones(partidos, predicciones_por_partido)
    aplicar_marcadores_snapshot(partidos)
    scraped_by_id = {item['id']: item for item in scraped_items}
    resultados_scraper = {
        **resultados_snapshot_por_partido(partidos),
        **resultados_scraper_por_partido(scraped_by_id),
    }
    aplicar_marcadores_scraper(partidos, scraped_by_id)
    partidos_en_vivo = list(
        Partido.objects.filter(estado=Partido.ESTADO_EN_VIVO)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    cupo_proximos = max(4 - len(partidos_en_vivo), 0)
    partidos_programados = list(
        Partido.objects.filter(estado=Partido.ESTADO_PROGRAMADO)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')[:cupo_proximos]
    )
    partidos_anteriores = list(
        Partido.objects.filter(estado=Partido.ESTADO_FINALIZADO)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('-fecha', '-hora', '-numero')[:4]
    )
    proximos = anotar_predicciones(partidos_en_vivo + partidos_programados, predicciones_por_partido)
    anteriores = anotar_predicciones(partidos_anteriores, predicciones_por_partido)
    favoritos_partidos = anotar_predicciones(favoritos_partidos, predicciones_por_partido)
    aplicar_marcadores_snapshot(proximos)
    aplicar_marcadores_snapshot(anteriores)
    aplicar_marcadores_snapshot(favoritos_partidos)
    aplicar_marcadores_scraper(proximos, scraped_by_id)
    aplicar_marcadores_scraper(anteriores, scraped_by_id)
    aplicar_marcadores_scraper(favoritos_partidos, scraped_by_id)
    resumen = Partido.objects.aggregate(
        total=Count('id'),
        programados=Count('id', filter=Q(estado=Partido.ESTADO_PROGRAMADO)),
        en_vivo=Count('id', filter=Q(estado=Partido.ESTADO_EN_VIVO)),
        finalizados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
    )

    secciones_partidos = agrupar_partidos(partidos)
    for seccion in secciones_partidos:
        if seccion.get('equipos'):
            seccion['tabla'] = tabla_desde_resultados(
                seccion['equipos'],
                seccion['partidos'],
                resultados_en_vivo=resultados_scraper,
            )
    if request.user.is_authenticated:
        fases_proyectadas = [seccion for seccion in secciones_partidos if not seccion.get('equipos')]
        completar_fase_final(fases_proyectadas, secciones_prediccion_grupos(predicciones_por_partido))
        marcar_fase_final_como_proyeccion(fases_proyectadas)

    partidos_calendario = Partido.objects.select_related('equipo_local', 'equipo_visitante').order_by('fecha')
    calendario_dias = []
    fechas_vistas = set()
    for partido in partidos_calendario:
        if partido.fecha not in fechas_vistas:
            fechas_vistas.add(partido.fecha)
            calendario_dias.append({'fecha': partido.fecha, 'partidos': []})
        calendario_dias[-1]['partidos'].append(partido)

    contexto = {
        'partidos': partidos,
        'secciones_partidos': secciones_partidos,
        'proximos': proximos,
        'anteriores': anteriores,
        'favoritos_partidos': favoritos_partidos,
        'resumen': resumen,
        'favoritos_ids': favoritos_ids,
        'grupos': list('ABCDEFGHIJKL'),
        'fases': Partido.FASES,
        'estados': Partido.ESTADOS,
        'filtros': {
            'grupo': grupo,
            'fase': fase,
            'estado': estado,
            'q': busqueda,
            'favoritos': solo_favoritos,
        },
        'calendario_dias': calendario_dias,
    }
    return render(request, 'core/home.html', contexto)


def partido_detalle(request, partido_id):
    partido = get_object_or_404(
        Partido.objects.select_related('equipo_local', 'equipo_visitante'),
        id=partido_id,
    )
    favorito = False
    prediccion = None
    if request.user.is_authenticated:
        favorito = PartidoFavorito.objects.filter(usuario=request.user, partido=partido).exists()
        prediccion = Prediccion.objects.filter(usuario=request.user, partido=partido).first()
    partido.prediccion_usuario = prediccion
    resultados_partido = {}
    live_team_ids = [
        team_id
        for team_id in (partido.equipo_local_id, partido.equipo_visitante_id)
        if partido.estado == Partido.ESTADO_EN_VIVO and team_id
    ]
    if not aplicar_marcador_snapshot(partido):
        try:
            scraped_match = find_flashscore_match_for_partido(partido)
        except Exception:
            scraped_match = None
        if scraped_match:
            aplicar_marcador_scraper(partido, scraped_match)
            score_payload = scraper_score_payload(scraped_match)
            if score_payload and score_payload['goles_local'] is not None and score_payload['goles_visitante'] is not None:
                resultados_partido[partido.id] = {
                    'goles_local': score_payload['goles_local'],
                    'goles_visitante': score_payload['goles_visitante'],
                }
            if score_payload and score_payload['estado'] == Partido.ESTADO_EN_VIVO:
                live_team_ids = [
                    team_id
                    for team_id in (partido.equipo_local_id, partido.equipo_visitante_id)
                    if team_id
                ]
    tabla_grupo = []
    proximos_grupo = []

    if partido.grupo:
        partidos_grupo = list(
            Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=partido.grupo)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero')
        )
        equipos_grupo = list(Equipo.objects.filter(grupo=partido.grupo).order_by('nombre'))
        tabla_grupo = tabla_desde_resultados(equipos_grupo, partidos_grupo, resultados_en_vivo=resultados_partido)
        proximos_grupo = [
            item
            for item in partidos_grupo
            if (
                (item.id != partido.id and item.estado == Partido.ESTADO_PROGRAMADO)
                or (item.id == partido.id and (getattr(partido, 'scraper_estado', partido.estado) == Partido.ESTADO_EN_VIVO))
            )
        ][:4]

    estadio_detalle_item = next(
        (
            item
            for item in ESTADIOS_2026
            if partido.estadio
            in {
                item.get('estadio', ''),
                item.get('titulo_fifa', ''),
                item.get('nombre_habitual', ''),
            }
        ),
        None,
    )

    return render(
        request,
        'core/partido_detalle.html',
        {
            'partido': partido,
            'favorito': favorito,
            'tabla_grupo': tabla_grupo,
            'proximos_grupo': proximos_grupo,
            'live_team_ids': live_team_ids,
            'estadio_detalle': estadio_detalle_item,
            'volver_url': url_volver(request, 'core:home'),
        },
    )


def seleccion_detalle(request, equipo_id):
    equipo = get_object_or_404(Equipo.objects.prefetch_related('jugadores'), id=equipo_id)
    partidos = list(
        Partido.objects.filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )

    predicciones_por_partido = {}
    favoritos_ids = set()
    if request.user.is_authenticated:
        favoritos_ids = set(
            PartidoFavorito.objects.filter(usuario=request.user).values_list('partido_id', flat=True)
        )
        predicciones_por_partido = {
            prediccion.partido_id: prediccion
            for prediccion in Prediccion.objects.filter(usuario=request.user)
        }
    partidos = anotar_predicciones(partidos, predicciones_por_partido)

    equipos_grupo = list(Equipo.objects.filter(grupo=equipo.grupo).order_by('nombre'))
    partidos_grupo = list(
        Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=equipo.grupo)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    tabla_grupo = tabla_desde_resultados(equipos_grupo, partidos_grupo) if equipo.grupo else []
    fila_equipo = next((fila for fila in tabla_grupo if fila['equipo'].id == equipo.id), None)
    confederacion, region = CONFEDERACIONES.get(equipo.nombre, ('A confirmar', 'A confirmar'))

    orden_posiciones = {
        'Portero': (1, 'portero'),
        'Defensa': (2, 'defensa'),
        'Mediocentro': (3, 'mediocentro'),
        'Delantero': (4, 'delantero'),
    }
    convocados = sorted(
        equipo.jugadores.all(),
        key=lambda jugador: (orden_posiciones.get(jugador.posicion, (9, ''))[0], jugador.orden),
    )
    for jugador in convocados:
        jugador.posicion_clase = orden_posiciones.get(jugador.posicion, (9, 'otro'))[1]
        nombre_camiseta = jugador.camiseta or jugador.nombre
        jugador.camiseta_larga = len(nombre_camiseta) > 12
        jugador.camiseta_muy_larga = len(nombre_camiseta) > 16
        jugador.nombre_completo = f'{jugador.nombres} {jugador.apellidos}'.strip()

    return render(
        request,
        'core/seleccion_detalle.html',
        {
            'equipo': equipo,
            'partidos': partidos,
            'favoritos_ids': favoritos_ids,
            'tabla_grupo': tabla_grupo,
            'fila_equipo': fila_equipo,
            'confederacion': confederacion,
            'region': region,
            'codigo_fifa': equipo.codigo_fifa,
            'tecnico': equipo.tecnico or TECNICOS_CONFIRMADOS.get(equipo.nombre, 'A confirmar'),
            'convocados': convocados or PLANTELES_CONFIRMADOS.get(equipo.nombre, []),
            'volver_url': url_volver(request, 'core:paises'),
        },
    )


def paises(request):
    equipos = list(Equipo.objects.order_by('grupo', 'nombre'))
    favoritos_ids = set()
    if request.user.is_authenticated:
        favoritos_ids = set(
            EquipoFavorito.objects.filter(usuario=request.user).values_list('equipo_id', flat=True)
        )

    proximos_por_equipo = {}
    partidos = (
        Partido.objects.filter(fase=Partido.FASE_GRUPOS)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    for partido in partidos:
        for equipo in (partido.equipo_local, partido.equipo_visitante):
            if not equipo:
                continue
            proximos_por_equipo.setdefault(equipo.id, [])
            if len(proximos_por_equipo[equipo.id]) < 2:
                proximos_por_equipo[equipo.id].append(partido)

    tarjetas = []
    for equipo in equipos:
        confederacion, region = CONFEDERACIONES.get(equipo.nombre, ('A definir', 'A confirmar'))
        tarjetas.append(
            {
                'equipo': equipo,
                'confederacion': confederacion,
                'region': region,
                'proximos': proximos_por_equipo.get(equipo.id, []),
                'favorito': equipo.id in favoritos_ids,
            }
        )

    return render(request, 'core/paises.html', {'tarjetas': tarjetas})


def construir_tarjetas_estadios():
    partidos_por_estadio = {}
    partidos = (
        Partido.objects.exclude(estadio='Sede a confirmar')
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    for partido in partidos:
        partidos_por_estadio.setdefault(partido.estadio, []).append(partido)

    tarjetas = []
    for estadio in ESTADIOS_2026:
        partidos_estadio = partidos_por_estadio.get(estadio['estadio'], [])
        proximos = [partido for partido in partidos_estadio if partido.estado != Partido.ESTADO_FINALIZADO]
        descripcion = [
            parrafo
            for parrafo in estadio.get('descripcion', [])
            if 'Partido ' not in parrafo
        ]
        tarjetas.append(
            {
                **estadio,
                'descripcion': descripcion,
                'resumen': descripcion[0] if descripcion else '',
                'partidos': partidos_estadio,
                'partidos_count': len(partidos_estadio),
                'proximos': proximos[:3],
                'finalizados_count': len(partidos_estadio) - len(proximos),
            }
        )
    return tarjetas


def estadios(request):
    tarjetas = construir_tarjetas_estadios()
    return render(
        request,
        'core/estadios.html',
        {
            'estadios': tarjetas,
            'total_estadios': len(tarjetas),
            'fuente_fifa_url': (
                'https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/'
                'articles/copa-mundial-2026-estadios-fifa-soccer-futbol-mexico-estados-unidos-canada'
            ),
        },
    )


def estadio_detalle(request, slug):
    estadio = next((item for item in construir_tarjetas_estadios() if item['slug'] == slug), None)
    if not estadio:
        raise Http404('Estadio no encontrado')

    return render(
        request,
        'core/estadio_detalle.html',
        {
            'estadio': estadio,
            'volver_url': resolve_url('core:estadios'),
            'fuente_fifa_url': (
                'https://www.fifa.com/es/tournaments/mens/worldcup/canadamexicousa2026/'
                'articles/copa-mundial-2026-estadios-fifa-soccer-futbol-mexico-estados-unidos-canada'
            ),
        },
    )


def predicciones(request):
    vista = request.GET.get('vista', 'previa')
    if vista not in {'previa', 'final', 'llaves'}:
        vista = 'previa'

    predicciones_por_partido = {}
    if request.user.is_authenticated:
        predicciones_por_partido = {
            prediccion.partido_id: prediccion
            for prediccion in Prediccion.objects.filter(usuario=request.user)
        }

    secciones = [
        seccion
        for seccion in secciones_prediccion_grupos(predicciones_por_partido)
        if seccion['equipos'] or seccion['partidos']
    ]

    fases_finales = []
    fases = dict(Partido.FASES)
    for fase, nombre in Partido.FASES:
        if fase == Partido.FASE_GRUPOS:
            continue
        partidos = anotar_predicciones(
            Partido.objects.filter(fase=fase)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero'),
            predicciones_por_partido,
        )
        if partidos:
            fases_finales.append({'fase': fase, 'titulo': fases[fase], 'partidos': partidos})
    fases_finales = completar_fase_final(fases_finales, secciones)

    contexto = {
        'vista': vista,
        'secciones': secciones,
        'fases_finales': fases_finales,
    }
    return render(request, 'core/predicciones.html', contexto)


@login_required
def alternar_favorito(request, partido_id):
    if request.method != 'POST':
        return redirect('core:home')

    partido = get_object_or_404(Partido, id=partido_id)
    favorito = PartidoFavorito.objects.filter(usuario=request.user, partido=partido).first()
    if favorito:
        favorito.delete()
        messages.success(request, 'Partido quitado de tus favoritos.')
    else:
        PartidoFavorito.objects.create(usuario=request.user, partido=partido)
        messages.success(request, 'Partido agregado a tus favoritos.')

    volver = request.POST.get('next') or 'core:home'
    return redirect(volver)


@login_required
def alternar_pais_favorito(request, equipo_id):
    if request.method != 'POST':
        return redirect('core:paises')

    equipo = get_object_or_404(Equipo, id=equipo_id)
    favorito = EquipoFavorito.objects.filter(usuario=request.user, equipo=equipo).first()
    if favorito:
        favorito.delete()
        messages.success(request, f'{equipo.nombre} quitado de tus paises favoritos.')
    else:
        EquipoFavorito.objects.create(usuario=request.user, equipo=equipo)
        partidos = Partido.objects.filter(Q(equipo_local=equipo) | Q(equipo_visitante=equipo))
        favoritos_existentes = set(
            PartidoFavorito.objects.filter(
                usuario=request.user,
                partido__in=partidos,
            ).values_list('partido_id', flat=True)
        )
        nuevos_favoritos = [
            PartidoFavorito(usuario=request.user, partido=partido)
            for partido in partidos
            if partido.id not in favoritos_existentes
        ]
        PartidoFavorito.objects.bulk_create(nuevos_favoritos)
        messages.success(
            request,
            f'{equipo.nombre} agregado a tus paises favoritos. Tambien se agregaron sus partidos.',
        )

    volver = request.POST.get('next') or 'core:paises'
    return redirect(volver)


@login_required
def guardar_prediccion(request, partido_id):
    if request.method != 'POST':
        return redirect('core:home')

    partido = get_object_or_404(Partido, id=partido_id)
    volver = request.POST.get('next') or 'core:home'

    es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        goles_local = int(request.POST.get('goles_local', ''))
        goles_visitante = int(request.POST.get('goles_visitante', ''))
    except ValueError:
        if es_ajax:
            return JsonResponse({'ok': False, 'mensaje': 'Completa ambos goles.'}, status=400)
        messages.error(request, 'La prediccion necesita goles numericos.')
        return redirect(volver)

    if goles_local < 0 or goles_visitante < 0 or goles_local > 99 or goles_visitante > 99:
        if es_ajax:
            return JsonResponse({'ok': False, 'mensaje': 'Usa goles entre 0 y 99.'}, status=400)
        messages.error(request, 'Usa goles entre 0 y 99.')
        return redirect(volver)

    Prediccion.objects.update_or_create(
        usuario=request.user,
        partido=partido,
        defaults={'goles_local': goles_local, 'goles_visitante': goles_visitante},
    )
    if es_ajax:
        return JsonResponse(
            {
                'ok': True,
                'mensaje': 'Guardada',
                'goles_local': goles_local,
                'goles_visitante': goles_visitante,
            }
        )
    messages.success(request, 'Prediccion guardada.')
    return redirect(volver)


@login_required
def resetear_prediccion(request, partido_id):
    if request.method != 'POST':
        return redirect('core:home')

    partido = get_object_or_404(Partido, id=partido_id)
    Prediccion.objects.filter(usuario=request.user, partido=partido).delete()
    es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if es_ajax:
        return JsonResponse({'ok': True, 'mensaje': 'Prediccion resetada.'})

    volver = request.POST.get('next') or 'core:home'
    messages.success(request, 'Prediccion restablecida.')
    return redirect(volver)


@login_required
def resetear_todas_predicciones(request):
    if request.method != 'POST':
        return redirect('core:predicciones')

    borradas, _ = Prediccion.objects.filter(usuario=request.user).delete()
    volver = request.POST.get('next') or 'core:predicciones'
    messages.success(request, f'Se restablecieron {borradas} predicciones.')
    return redirect(volver)


def tabla_grupo_payload(grupo, resultados_en_vivo=None):
    equipos = list(Equipo.objects.filter(grupo=grupo).order_by('nombre'))
    partidos = list(
        Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=grupo)
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    return [
        {
            'team_id': fila['equipo'].id,
            'team_name': fila['equipo'].nombre,
            'pj': fila['pj'],
            'pg': fila['pg'],
            'pe': fila['pe'],
            'pp': fila['pp'],
            'gf': fila['gf'],
            'gc': fila['gc'],
            'dg': fila['dg'],
            'pts': fila['pts'],
        }
        for fila in tabla_desde_resultados(equipos, partidos, resultados_en_vivo=resultados_en_vivo)
    ]


def scraper_partidos_del_dia():
    hoy = timezone.localdate()
    partidos = list(
        Partido.objects.filter(fase=Partido.FASE_GRUPOS, fecha__in=[hoy, hoy + timedelta(days=1), hoy - timedelta(days=1)])
        .select_related('equipo_local', 'equipo_visitante')
        .order_by('fecha', 'hora', 'numero')
    )
    if not partidos:
        return []

    resultados = []
    for offset in (0, 1, -1):
        try:
            report = fetch_flashscore_worldcup_matches(
                feed_name=flashscore_daily_feed_name(offset),
                source_url='',
            )
        except Exception:
            continue
        for partido in partidos:
            if any(item['id'] == partido.id for item in resultados):
                continue
            match = flashscore_match_for_partido_in_matches(partido, report.get('matches', []))
            if not match:
                continue
            score = match.get('score') or {}
            if match.get('status') == 'programado' and score.get('home') == '' and score.get('away') == '':
                continue
            resultados.append(
                {
                    'id': partido.id,
                    'partido': partido,
                    'match': match,
                }
            )
    return resultados


def api_partidos_vivo(request):
    es_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    scraped_items = scraper_partidos_del_dia()
    scraped_by_id = {item['id']: item for item in scraped_items}

    resultados_en_vivo = {}
    grupos_afectados = set()
    requiere_refresco = False
    data = [
    ]
    for scraped in scraped_items:
        partido = scraped['partido']
        match = scraped.get('match') or {}
        score_payload = scraper_score_payload(match)
        if not score_payload:
            continue
        goles_local = score_payload['goles_local']
        goles_visitante = score_payload['goles_visitante']
        estado = score_payload['estado'] or partido.estado
        estado_display = score_payload['estado_display'] or partido.estado_partido_label
        marcador = score_payload['marcador']
        estado_anterior = partido.estado
        if persistir_marcador_scraper(partido, match) and partido.estado != estado_anterior:
            requiere_refresco = True
        if partido.grupo and goles_local is not None and goles_visitante is not None:
            grupos_afectados.add(partido.grupo)
            resultados_en_vivo[partido.id] = {
                'goles_local': goles_local,
                'goles_visitante': goles_visitante,
            }
        data.append(
            {
                'id': partido.id,
                'grupo': partido.grupo,
                'equipo_local_id': partido.equipo_local_id,
                'equipo_visitante_id': partido.equipo_visitante_id,
                'goles_local': goles_local,
                'goles_visitante': goles_visitante,
                'marcador': marcador,
                'estado': estado,
                'estado_display': estado_display,
                'evento_actualizado': partido.evento_actualizado.isoformat() if partido.evento_actualizado else '',
            }
        )

    if not es_ajax:
        return JsonResponse(data, safe=False)

    response = {
        'partidos': data,
        'refresh_required': requiere_refresco,
        'tablas': {
            grupo: tabla_grupo_payload(grupo, resultados_en_vivo=resultados_en_vivo)
            for grupo in sorted(grupos_afectados)
        },
        'jugando': {
            grupo: [
                team_id
                for item in scraped_items
                for partido in [item['partido']]
                if partido.grupo == grupo
                and partido.id in resultados_en_vivo
                and scraped_by_id.get(partido.id, {}).get('match', {}).get('status') == 'en_vivo'
                for team_id in (partido.equipo_local_id, partido.equipo_visitante_id)
                if team_id
            ]
            for grupo in sorted(grupos_afectados)
        },
    }
    return JsonResponse(response)


def api_partido_seguimiento(request, partido_id):
    partido = get_object_or_404(
        Partido.objects.select_related('equipo_local', 'equipo_visitante'),
        id=partido_id,
    )
    data = {
        'ok': True,
        'partido_id': partido.id,
        'source': 'flashscore',
        'updated_at': timezone.localtime(timezone.now()).isoformat(),
        'local': partido.local_nombre,
        'visitante': partido.visitante_nombre,
        'estado': partido.estado,
        'estado_display': partido.estado_partido_label,
        'marcador': '-',
        'scraper': {
            'available': True,
            'found': False,
            'status': '',
            'url': '',
            'event_id': '',
            'score': {},
            'lineups_available': False,
            'lineups': {},
            'statistics_available': False,
            'statistics': {},
            'summary_available': False,
            'commentary_available': False,
            'summary': {},
            'report_available': False,
            'report': {},
            'message': 'Sin datos del scraper para este partido.',
        },
    }

    cached_data = cached_tracking_response(partido, data)
    if cached_data:
        return JsonResponse(cached_data)

    try:
        scraped_match = find_flashscore_match_for_partido(partido)
    except Exception:
        data['scraper'].update(
            {
                'available': False,
                'status': 'sin_conexion',
                'message': (
                    'No se pudo conectar con Flashscore desde el servidor. '
                    'No se actualiza el marcador hasta recuperar el scraper.'
                ),
            }
        )
        return JsonResponse(data)

    if not scraped_match:
        return JsonResponse(data)

    score = scraped_match.get('score') or {}
    score_payload = scraper_score_payload(scraped_match)
    if score_payload:
        data['marcador'] = score_payload['marcador']
        data['estado'] = score_payload['estado'] or data['estado']
        data['estado_display'] = score_payload['estado_display'] or data['estado_display']
        if partido.grupo and score_payload['goles_local'] is not None and score_payload['goles_visitante'] is not None:
            data['tabla_grupo'] = tabla_grupo_payload(
                partido.grupo,
                resultados_en_vivo={
                    partido.id: {
                        'goles_local': score_payload['goles_local'],
                        'goles_visitante': score_payload['goles_visitante'],
                    }
                },
            )
            data['jugando'] = [
                team_id
                for team_id in (partido.equipo_local_id, partido.equipo_visitante_id)
                if score_payload['estado'] == Partido.ESTADO_EN_VIVO and team_id
            ]

    data['scraper'].update(
        {
            'found': True,
            'status': scraped_match.get('status', ''),
            'url': scraped_match.get('url', ''),
            'event_id': scraped_match.get('event_id', ''),
            'score': score,
            'message': 'Datos actualizados desde Flashscore.',
        }
    )

    if scraped_match.get('status') != 'programado' and scraped_match.get('event_id') and scraped_match.get('url'):
        try:
            summary = build_flashscore_summary_report(
                scraped_match['event_id'],
                scraped_match['url'],
                home_team=flashscore_team_name(scraped_match.get('home', '')),
                away_team=flashscore_team_name(scraped_match.get('away', '')),
            )
        except Exception:
            data['scraper']['summary_available'] = False
        else:
            data['scraper']['summary'] = summary
            data['scraper']['summary_available'] = any(
                period.get('events') for period in summary.get('periods', [])
            )
            data['scraper']['commentary_available'] = any(
                item.get('description')
                for period in summary.get('periods', [])
                for item in period.get('commentary', [])
            )

        try:
            report = build_flashscore_report(scraped_match['event_id'], scraped_match['url'])
        except Exception:
            data['scraper']['report_available'] = False
        else:
            data['scraper']['report'] = report
            data['scraper']['report_available'] = bool(
                report.get('title') or report.get('paragraphs')
            )

        try:
            statistics = build_flashscore_statistics_report(scraped_match['event_id'], scraped_match['url'])
        except Exception:
            data['scraper']['statistics_available'] = False
        else:
            data['scraper']['statistics'] = statistics
            data['scraper']['statistics_available'] = any(
                group.get('stats')
                for period in statistics.get('periods', [])
                for group in period.get('groups', [])
            )

        try:
            lineups = build_flashscore_lineups_report(scraped_match['event_id'], scraped_match['url'])
        except Exception:
            data['scraper']['message'] = 'Datos de partido disponibles. Formaciones no disponibles por ahora.'
        else:
            summarized = summarize_lineups_for_tracking(lineups)
            data['scraper']['lineups'] = summarized
            data['scraper']['lineups_available'] = any(
                team.get('starters') for team in summarized.values()
            )

    save_tracking_snapshot_if_complete(partido, data)
    return JsonResponse(data)

def registro(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(request, 'Tu cuenta fue creada correctamente.')
            return redirect('core:home')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'core/registro.html', {'form': form})


def almanaque(request):
    grupo = request.GET.get('grupo', '')
    fase = request.GET.get('fase', '')
    busqueda = request.GET.get('q', '').strip()

    partidos = Partido.objects.select_related('equipo_local', 'equipo_visitante')

    if grupo:
        partidos = partidos.filter(grupo=grupo)
    if fase:
        partidos = partidos.filter(fase=fase)
    if busqueda:
        partidos = partidos.filter(
            Q(equipo_local__nombre__icontains=busqueda)
            | Q(equipo_visitante__nombre__icontains=busqueda)
            | Q(estadio__icontains=busqueda)
            | Q(ciudad__icontains=busqueda)
        )

    predicciones_por_partido = {}
    favoritos_ids = set()
    if request.user.is_authenticated:
        favoritos_ids = set(
            PartidoFavorito.objects.filter(usuario=request.user).values_list('partido_id', flat=True)
        )
        predicciones_por_partido = {
            prediccion.partido_id: prediccion
            for prediccion in Prediccion.objects.filter(usuario=request.user)
        }

    partidos = anotar_predicciones(partidos, predicciones_por_partido)
    aplicar_marcadores_snapshot(partidos)
    try:
        scraped_items = scraper_partidos_del_dia()
    except Exception:
        scraped_items = []
    aplicar_marcadores_scraper(partidos, {item['id']: item for item in scraped_items})
    if request.user.is_authenticated:
        fases_proyectadas = [
            {'partidos': [partido for partido in partidos if partido.fase != Partido.FASE_GRUPOS]}
        ]
        completar_fase_final(fases_proyectadas, secciones_prediccion_grupos(predicciones_por_partido))
        marcar_fase_final_como_proyeccion(fases_proyectadas)

    calendario_dias = []
    fechas_vistas = set()
    for partido in partidos:
        if partido.fecha not in fechas_vistas:
            fechas_vistas.add(partido.fecha)
            calendario_dias.append({'fecha': partido.fecha, 'partidos': []})
        calendario_dias[-1]['partidos'].append(partido)

    contexto = {
        'calendario_dias': calendario_dias,
        'favoritos_ids': favoritos_ids,
        'grupos': list('ABCDEFGHIJKL'),
        'fases': Partido.FASES,
        'filtros': {
            'grupo': grupo,
            'fase': fase,
            'q': busqueda,
        },
    }
    return render(request, 'core/almanaque.html', contexto)
