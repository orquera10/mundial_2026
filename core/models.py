from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models
from django.utils import timezone


ARGENTINA_TZ = ZoneInfo('America/Argentina/Buenos_Aires')

VENUE_TIME_ZONES = {
    'Atlanta': 'America/New_York',
    'Boston': 'America/New_York',
    'Dallas': 'America/Chicago',
    'Guadalajara': 'America/Mexico_City',
    'Houston': 'America/Chicago',
    'Kansas City': 'America/Chicago',
    'Los Angeles': 'America/Los_Angeles',
    'Mexico City': 'America/Mexico_City',
    'Miami': 'America/New_York',
    'Monterrey': 'America/Mexico_City',
    'New York/New Jersey': 'America/New_York',
    'Philadelphia': 'America/New_York',
    'San Francisco Bay Area': 'America/Los_Angeles',
    'Seattle': 'America/Los_Angeles',
    'Toronto': 'America/Toronto',
    'Vancouver': 'America/Vancouver',
}

FLAGS = {
    'Algeria': '🇩🇿',
    'Argentina': '🇦🇷',
    'Australia': '🇦🇺',
    'Austria': '🇦🇹',
    'Belgium': '🇧🇪',
    'Bosnia and Herzegovina': '🇧🇦',
    'Brazil': '🇧🇷',
    'Cabo Verde': '🇨🇻',
    'Canada': '🇨🇦',
    'Colombia': '🇨🇴',
    'Congo DR': '🇨🇩',
    "Cote d'Ivoire": '🇨🇮',
    'Croatia': '🇭🇷',
    'Curacao': '🇨🇼',
    'Czechia': '🇨🇿',
    'Ecuador': '🇪🇨',
    'Egypt': '🇪🇬',
    'England': '🏴',
    'France': '🇫🇷',
    'Germany': '🇩🇪',
    'Ghana': '🇬🇭',
    'Haiti': '🇭🇹',
    'IR Iran': '🇮🇷',
    'Iraq': '🇮🇶',
    'Japan': '🇯🇵',
    'Jordan': '🇯🇴',
    'Korea Republic': '🇰🇷',
    'Mexico': '🇲🇽',
    'Morocco': '🇲🇦',
    'Netherlands': '🇳🇱',
    'New Zealand': '🇳🇿',
    'Norway': '🇳🇴',
    'Panama': '🇵🇦',
    'Paraguay': '🇵🇾',
    'Portugal': '🇵🇹',
    'Qatar': '🇶🇦',
    'Saudi Arabia': '🇸🇦',
    'Scotland': '🏴',
    'Senegal': '🇸🇳',
    'South Africa': '🇿🇦',
    'Spain': '🇪🇸',
    'Sweden': '🇸🇪',
    'Switzerland': '🇨🇭',
    'Tunisia': '🇹🇳',
    'Turkiye': '🇹🇷',
    'Uruguay': '🇺🇾',
    'USA': '🇺🇸',
    'Uzbekistan': '🇺🇿',
}

FLAG_CODES = {
    'Algeria': 'dz',
    'Argentina': 'ar',
    'Australia': 'au',
    'Austria': 'at',
    'Belgium': 'be',
    'Bosnia and Herzegovina': 'ba',
    'Brazil': 'br',
    'Cabo Verde': 'cv',
    'Canada': 'ca',
    'Colombia': 'co',
    'Congo DR': 'cd',
    "Cote d'Ivoire": 'ci',
    'Croatia': 'hr',
    'Curacao': 'cw',
    'Czechia': 'cz',
    'Ecuador': 'ec',
    'Egypt': 'eg',
    'England': 'gb-eng',
    'France': 'fr',
    'Germany': 'de',
    'Ghana': 'gh',
    'Haiti': 'ht',
    'IR Iran': 'ir',
    'Iraq': 'iq',
    'Japan': 'jp',
    'Jordan': 'jo',
    'Korea Republic': 'kr',
    'Mexico': 'mx',
    'Morocco': 'ma',
    'Netherlands': 'nl',
    'New Zealand': 'nz',
    'Norway': 'no',
    'Panama': 'pa',
    'Paraguay': 'py',
    'Portugal': 'pt',
    'Qatar': 'qa',
    'Saudi Arabia': 'sa',
    'Scotland': 'gb-sct',
    'Senegal': 'sn',
    'South Africa': 'za',
    'Spain': 'es',
    'Sweden': 'se',
    'Switzerland': 'ch',
    'Tunisia': 'tn',
    'Turkiye': 'tr',
    'Uruguay': 'uy',
    'USA': 'us',
    'Uzbekistan': 'uz',
}

TEAM_COLORS = {
    'Algeria': ('#006233', '#ffffff', '#d21034'),
    'Argentina': ('#4b9ae4', '#ffffff', '#f6b40e'),
    'Australia': ( '#ffcd00','#00843d', '#ffffff'),
    'Austria': ('#ed2939', '#ffffff', '#c8102e'),
    'Belgium': ('#ed2939','#fae042',  '#000000'),
    'Bosnia and Herzegovina': ('#002f6c', '#fcd116', '#ffffff'),
    'Brazil': ( '#ffdf00', '#009c3b','#002776'),
    'Cabo Verde': ('#003893', '#ffffff', '#cf2027'),
    'Canada': ('#d52b1e', '#ffffff', '#a6192e'),
    'Colombia': ('#fcd116', '#003893', '#ce1126'),
    'Congo DR': ('#007fff', '#f7d618', '#ce1021'),
    "Cote d'Ivoire": ('#f77f00', '#ffffff', '#009e60'),
    'Croatia': ('#ff0000', '#ffffff', '#171796'),
    'Curacao': ('#002b7f', '#f9e814', '#ffffff'),
    'Czechia': ('#d7141a', '#ffffff', '#11457e'),
    'Ecuador': ('#ffdd00', '#034ea2', '#ed1c24'),
    'Egypt': ('#ce1126', '#ffffff', '#000000'),
    'England': ('#ffffff','#cf142b',  '#003087'),
    'France': ("#011e3a", '#ffffff', '#ef4135'),
    'Germany': ('#000000', '#dd0000', '#ffce00'),
    'Ghana': ('#006b3f', '#fcd116', '#ce1126'),
    'Haiti': ('#00209f', '#d21034', '#ffffff'),
    'IR Iran': ('#239f40', '#ffffff', '#da0000'),
    'Iraq': ('#ce1126', '#ffffff', '#000000'),
    'Japan': ('#ffffff','#bc002d',  '#1f2937'),
    'Jordan': ('#ce1126', '#ffffff', '#007a3d'),
    'Korea Republic': ('#c60c30', '#ffffff', '#003478'),
    'Mexico': ('#006847', '#ffffff', '#ce1126'),
    'Morocco': ('#c1272d', '#006233', '#ffffff'),
    'Netherlands': ('#ff4f00', '#ffffff', '#21468b'),
    'New Zealand': ('#00247d', '#ffffff', '#cc142b'),
    'Norway': ('#ba0c2f', '#ffffff', '#00205b'),
    'Panama': ('#005293', '#ffffff', '#d21034'),
    'Paraguay': ('#d52b1e','#0038a8',  '#ffffff'),
    'Portugal': ('#ff0000', '#006600', '#ffcc00'),
    'Qatar': ('#8a1538', '#ffffff', '#5f0f2f'),
    'Saudi Arabia': ('#006c35', '#ffffff', '#d7f3df'),
    'Scotland': ('#005eb8', '#ffffff', '#003f7f'),
    'Senegal': ('#00853f', '#fdef42', '#e31b23'),
    'South Africa': ('#007a4d', '#ffb612', '#de3831'),
    'Spain': ('#aa151b', '#f1bf00', '#ffffff'),
    'Sweden': ('#006aa7', '#fecc00', '#ffffff'),
    'Switzerland': ('#d52b1e', '#ffffff', '#b00020'),
    'Tunisia': ('#e70013', '#ffffff', '#c40010'),
    'Turkiye': ('#e30a17', '#ffffff', '#b80012'),
    'Uruguay': ("#5181e0", '#ffffff', '#fcd116'),
    'USA': ('#3c3b6e', '#ffffff', '#b22234'),
    'Uzbekistan': ('#1eb6e7', '#ffffff', '#009b3a'),
}

DEFAULT_TEAM_COLORS = ('#004b8d', '#ffffff', '#007852')


def bandera_url(nombre):
    codigo = FLAG_CODES.get(nombre)
    if not codigo:
        return ''
    return f'https://flagcdn.com/w80/{codigo}.png'


def colores_equipo(nombre):
    return TEAM_COLORS.get(nombre, DEFAULT_TEAM_COLORS)


class Equipo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    grupo = models.CharField(max_length=1, blank=True)
    codigo_fifa = models.CharField(max_length=6, blank=True)
    tecnico = models.CharField(max_length=120, blank=True)
    tecnico_nombre_tabla = models.CharField(max_length=120, blank=True)
    tecnico_nombres = models.CharField(max_length=120, blank=True)
    tecnico_apellidos = models.CharField(max_length=140, blank=True)
    tecnico_nacionalidad = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ['grupo', 'nombre']

    def __str__(self):
        return self.nombre

    @property
    def bandera(self):
        return FLAGS.get(self.nombre, 'ðŸ³')

    @property
    def bandera_url(self):
        return bandera_url(self.nombre)

    @property
    def color_principal(self):
        return colores_equipo(self.nombre)[0]

    @property
    def color_secundario(self):
        return colores_equipo(self.nombre)[1]

    @property
    def color_terciario(self):
        return colores_equipo(self.nombre)[2]


class JugadorSeleccion(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='jugadores')
    orden = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=120)
    nombre_tabla = models.CharField(max_length=120, blank=True)
    nombres = models.CharField(max_length=140, blank=True)
    apellidos = models.CharField(max_length=160, blank=True)
    nombre_camiseta = models.CharField(max_length=80, blank=True)
    camiseta = models.CharField(max_length=80, blank=True)
    posicion = models.CharField(max_length=40)
    fecha_nacimiento = models.CharField(max_length=12, blank=True)
    club = models.CharField(max_length=140, blank=True)
    altura_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    internacionalidades = models.PositiveSmallIntegerField(null=True, blank=True)
    goles = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['equipo__nombre', 'orden']
        constraints = [
            models.UniqueConstraint(fields=['equipo', 'orden'], name='jugador_unico_por_equipo_y_orden'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.equipo})'

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        try:
            dia, mes, anio = [int(parte) for parte in self.fecha_nacimiento.split('/')]
        except (TypeError, ValueError):
            return None
        hoy = timezone.localdate()
        edad = hoy.year - anio
        if (hoy.month, hoy.day) < (mes, dia):
            edad -= 1
        return edad


class Partido(models.Model):
    ESTADO_PROGRAMADO = 'programado'
    ESTADO_EN_VIVO = 'en_vivo'
    ESTADO_FINALIZADO = 'finalizado'
    ESTADOS = [
        (ESTADO_PROGRAMADO, 'Programado'),
        (ESTADO_EN_VIVO, 'En vivo'),
        (ESTADO_FINALIZADO, 'Finalizado'),
    ]

    FASE_GRUPOS = 'grupos'
    FASE_16AVOS = '16avos'
    FASE_16 = 'octavos'
    FASE_CUARTOS = 'cuartos'
    FASE_SEMIS = 'semis'
    FASE_TERCER_PUESTO = 'tercer_puesto'
    FASE_FINAL = 'final'
    FASES = [
        (FASE_GRUPOS, 'Fase de grupos'),
        (FASE_16AVOS, '16avos de final'),
        (FASE_16, 'Octavos de final'),
        (FASE_CUARTOS, 'Cuartos de final'),
        (FASE_SEMIS, 'Semifinales'),
        (FASE_TERCER_PUESTO, 'Tercer puesto'),
        (FASE_FINAL, 'Final'),
    ]

    numero = models.PositiveSmallIntegerField(unique=True)
    fase = models.CharField(max_length=20, choices=FASES, default=FASE_GRUPOS)
    grupo = models.CharField(max_length=1, blank=True)
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    estadio = models.CharField(max_length=120)
    ciudad = models.CharField(max_length=80, blank=True)
    equipo_local = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partidos_local',
    )
    equipo_visitante = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partidos_visitante',
    )
    etiqueta_local = models.CharField(max_length=100, blank=True)
    etiqueta_visitante = models.CharField(max_length=100, blank=True)
    goles_local = models.PositiveSmallIntegerField(null=True, blank=True)
    goles_visitante = models.PositiveSmallIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PROGRAMADO)
    notas = models.CharField(max_length=180, blank=True)
    canales_argentina = models.CharField(max_length=180, blank=True)
    streaming_argentina = models.CharField(max_length=180, blank=True)
    transmision_notas = models.CharField(max_length=220, blank=True)
    football_data_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    jornada = models.PositiveSmallIntegerField(null=True, blank=True)
    etapa_api = models.CharField(max_length=60, blank=True)
    grupo_api = models.CharField(max_length=60, blank=True)
    arbitro = models.CharField(max_length=100, blank=True)
    arbitro_nacionalidad = models.CharField(max_length=80, blank=True)
    evento_actualizado = models.DateTimeField(null=True, blank=True)
    escudo_local_url = models.URLField(blank=True)
    escudo_visitante_url = models.URLField(blank=True)

    class Meta:
        ordering = ['fecha', 'hora', 'numero']

    def __str__(self):
        return f'Partido {self.numero}: {self.local_nombre} vs {self.visitante_nombre}'

    @property
    def local_nombre(self):
        return self.equipo_local.nombre if self.equipo_local else self.etiqueta_local

    @property
    def visitante_nombre(self):
        return self.equipo_visitante.nombre if self.equipo_visitante else self.etiqueta_visitante

    @property
    def bandera_local(self):
        return FLAGS.get(self.local_nombre, '🏳')

    @property
    def bandera_visitante(self):
        return FLAGS.get(self.visitante_nombre, '🏳')

    @property
    def bandera_local_url(self):
        return bandera_url(self.local_nombre)

    @property
    def bandera_visitante_url(self):
        return bandera_url(self.visitante_nombre)

    @property
    def color_local(self):
        return colores_equipo(self.local_nombre)[0]

    @property
    def color_visitante(self):
        return colores_equipo(self.visitante_nombre)[0]

    @property
    def color_local_secundario(self):
        return colores_equipo(self.local_nombre)[1]

    @property
    def color_visitante_secundario(self):
        return colores_equipo(self.visitante_nombre)[1]

    @property
    def color_local_terciario(self):
        return colores_equipo(self.local_nombre)[2]

    @property
    def color_visitante_terciario(self):
        return colores_equipo(self.visitante_nombre)[2]

    @property
    def horario(self):
        if not self.hora:
            return 'Horario a confirmar'
        return self.hora.strftime('%H:%M')

    @property
    def zona_horaria_sede(self):
        return VENUE_TIME_ZONES.get(self.ciudad, 'America/Argentina/Buenos_Aires')

    @property
    def inicio_argentina(self):
        if not self.hora:
            return None
        inicio_local = datetime.combine(self.fecha, self.hora, tzinfo=ZoneInfo(self.zona_horaria_sede))
        return inicio_local.astimezone(ARGENTINA_TZ)

    @property
    def fecha_argentina(self):
        inicio = self.inicio_argentina
        return inicio.date() if inicio else self.fecha

    @property
    def horario_argentina(self):
        inicio = self.inicio_argentina
        if not inicio:
            return 'Horario a confirmar'
        return f'{inicio:%H:%M} ARG'

    @property
    def marcador(self):
        if self.goles_local is None or self.goles_visitante is None:
            return '-'
        return f'{self.goles_local} - {self.goles_visitante}'

    @property
    def es_hoy(self):
        return self.fecha == timezone.localdate()


class PartidoFavorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='favoritos')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'partido'], name='favorito_unico_por_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario} sigue {self.partido}'


class EquipoFavorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='favoritos')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'equipo'], name='equipo_favorito_unico_por_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario} sigue {self.equipo}'


class Prediccion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='predicciones')
    goles_local = models.PositiveSmallIntegerField()
    goles_visitante = models.PositiveSmallIntegerField()
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'partido'], name='prediccion_unica_por_usuario'),
        ]

    def __str__(self):
        return f'{self.usuario}: {self.partido} {self.goles_local}-{self.goles_visitante}'

    @staticmethod
    def signo(goles_local, goles_visitante):
        if goles_local > goles_visitante:
            return 'local'
        if goles_local < goles_visitante:
            return 'visitante'
        return 'empate'

    @property
    def comparacion_estado(self):
        if self.partido.estado != Partido.ESTADO_FINALIZADO:
            return ''
        if self.partido.goles_local is None or self.partido.goles_visitante is None:
            return ''
        if (
            self.goles_local == self.partido.goles_local
            and self.goles_visitante == self.partido.goles_visitante
        ):
            return 'exacta'
        predicho = self.signo(self.goles_local, self.goles_visitante)
        real = self.signo(self.partido.goles_local, self.partido.goles_visitante)
        if predicho == real:
            return 'ganador'
        return 'fallida'

    @property
    def comparacion_label(self):
        etiquetas = {
            'exacta': 'Resultado exacto',
            'ganador': 'Ganador acertado',
            'fallida': 'No acertada',
        }
        return etiquetas.get(self.comparacion_estado, 'Prediccion guardada')
