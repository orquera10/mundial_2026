from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegistroUsuarioForm
from .models import Equipo, EquipoFavorito, Partido, PartidoFavorito, Prediccion, bandera_url


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


def tabla_desde_resultados(equipos, partidos):
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
        if partido.goles_local is None or partido.goles_visitante is None:
            continue

        local = tabla[partido.equipo_local_id]
        visitante = tabla[partido.equipo_visitante_id]
        goles_local = partido.goles_local
        goles_visitante = partido.goles_visitante

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
    if request.user.is_authenticated:
        favoritos_ids = set(
            PartidoFavorito.objects.filter(usuario=request.user).values_list('partido_id', flat=True)
        )
        predicciones_por_partido = {
            prediccion.partido_id: prediccion
            for prediccion in Prediccion.objects.filter(usuario=request.user)
        }

    partidos = anotar_predicciones(partidos, predicciones_por_partido)
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
    proximos = anotar_predicciones(partidos_en_vivo + partidos_programados, predicciones_por_partido)
    resumen = Partido.objects.aggregate(
        total=Count('id'),
        programados=Count('id', filter=Q(estado=Partido.ESTADO_PROGRAMADO)),
        en_vivo=Count('id', filter=Q(estado=Partido.ESTADO_EN_VIVO)),
        finalizados=Count('id', filter=Q(estado=Partido.ESTADO_FINALIZADO)),
    )

    secciones_partidos = agrupar_partidos(partidos)
    for seccion in secciones_partidos:
        if seccion.get('equipos'):
            seccion['tabla'] = tabla_desde_resultados(seccion['equipos'], seccion['partidos'])
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
    tabla_grupo = []
    proximos_grupo = []

    if partido.grupo:
        partidos_grupo = list(
            Partido.objects.filter(fase=Partido.FASE_GRUPOS, grupo=partido.grupo)
            .select_related('equipo_local', 'equipo_visitante')
            .order_by('fecha', 'hora', 'numero')
        )
        equipos_grupo = list(Equipo.objects.filter(grupo=partido.grupo).order_by('nombre'))
        tabla_grupo = tabla_desde_resultados(equipos_grupo, partidos_grupo)
        proximos_grupo = [
            item
            for item in partidos_grupo
            if item.id != partido.id and item.estado == Partido.ESTADO_PROGRAMADO
        ][:4]

    return render(
        request,
        'core/partido_detalle.html',
        {
            'partido': partido,
            'favorito': favorito,
            'tabla_grupo': tabla_grupo,
            'proximos_grupo': proximos_grupo,
        },
    )


def seleccion_detalle(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
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
            'tecnico': TECNICOS_CONFIRMADOS.get(equipo.nombre, 'A confirmar'),
            'convocados': PLANTELES_CONFIRMADOS.get(equipo.nombre, []),
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

def api_partidos_vivo(request):
    partidos_en_vivo = Partido.objects.filter(
        estado=Partido.ESTADO_EN_VIVO
    )
    data = [
        {
            'id': partido.id,
            'goles_local': partido.goles_local,
            'goles_visitante': partido.goles_visitante,
            'marcador': partido.marcador,
            'estado': partido.estado,
            'estado_display': partido.get_estado_display(),
        }
        for partido in partidos_en_vivo
    ]
    return JsonResponse(data, safe=False)

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
