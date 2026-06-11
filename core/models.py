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


def bandera_url(nombre):
    codigo = FLAG_CODES.get(nombre)
    if not codigo:
        return ''
    return f'https://flagcdn.com/w80/{codigo}.png'


class Equipo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    grupo = models.CharField(max_length=1, blank=True)

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
