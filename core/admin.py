from django.contrib import admin

from .models import Equipo, Partido, PartidoFavorito, Prediccion


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'grupo')
    list_filter = ('grupo',)
    search_fields = ('nombre',)


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
