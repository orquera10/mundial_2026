from django.contrib import admin

from .models import Equipo, JugadorSeleccion, Partido, PartidoFavorito, Prediccion


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'grupo', 'codigo_fifa', 'tecnico', 'tecnico_nacionalidad')
    list_filter = ('grupo',)
    search_fields = (
        'nombre',
        'codigo_fifa',
        'tecnico',
        'tecnico_nombre_tabla',
        'tecnico_nombres',
        'tecnico_apellidos',
        'tecnico_nacionalidad',
    )


@admin.register(JugadorSeleccion)
class JugadorSeleccionAdmin(admin.ModelAdmin):
    list_display = (
        'orden',
        'nombre',
        'equipo',
        'posicion',
        'camiseta',
        'club',
        'internacionalidades',
        'goles',
    )
    list_filter = ('equipo', 'posicion')
    search_fields = (
        'nombre',
        'nombre_tabla',
        'nombres',
        'apellidos',
        'camiseta',
        'nombre_camiseta',
        'club',
        'equipo__nombre',
    )


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = (
        'numero',
        'fecha',
        'fase',
        'grupo',
        'equipo_local',
        'equipo_visitante',
        'marcador',
        'estado',
        'canales_argentina',
        'arbitro',
        'estadio',
    )
    list_editable = ('estado', 'canales_argentina')
    list_filter = ('fase', 'grupo', 'estado', 'fecha')
    search_fields = (
        'equipo_local__nombre',
        'equipo_visitante__nombre',
        'etiqueta_local',
        'etiqueta_visitante',
        'estadio',
        'ciudad',
        'canales_argentina',
        'streaming_argentina',
        'arbitro',
    )
    fieldsets = (
        (
            None,
            {
                'fields': (
                    'numero',
                    'fase',
                    'grupo',
                    'fecha',
                    'hora',
                    'estado',
                    'equipo_local',
                    'equipo_visitante',
                    'etiqueta_local',
                    'etiqueta_visitante',
                    'goles_local',
                    'goles_visitante',
                    'estadio',
                    'ciudad',
                    'notas',
                )
            },
        ),
        (
            'Transmision en Argentina',
            {
                'fields': (
                    'canales_argentina',
                    'streaming_argentina',
                    'transmision_notas',
                )
            },
        ),
        (
            'Datos externos',
            {
                'fields': (
                    'football_data_id',
                    'jornada',
                    'etapa_api',
                    'grupo_api',
                    'arbitro',
                    'arbitro_nacionalidad',
                    'evento_actualizado',
                    'escudo_local_url',
                    'escudo_visitante_url',
                )
            },
        ),
    )
    ordering = ('fecha', 'hora', 'numero')


@admin.register(PartidoFavorito)
class PartidoFavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'partido', 'creado')
    list_filter = ('creado',)
    search_fields = ('usuario__username', 'partido__equipo_local__nombre', 'partido__equipo_visitante__nombre')


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'partido', 'goles_local', 'goles_visitante', 'actualizado')
    list_filter = ('actualizado',)
    search_fields = ('usuario__username', 'partido__equipo_local__nombre', 'partido__equipo_visitante__nombre')
