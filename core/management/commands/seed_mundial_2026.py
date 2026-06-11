from datetime import date, time

from django.core.management.base import BaseCommand

from core.models import Equipo, Partido


TIME_SLOTS = [time(13, 0), time(16, 0), time(19, 0), time(22, 0)]


def match_time(numero):
    return TIME_SLOTS[(numero - 1) % len(TIME_SLOTS)]


def transmision_argentina(local, visitante, fase):
    canales = 'Telefe / TyC Sports'
    notas = ''
    if 'Argentina' in {local, visitante} or fase == Partido.FASE_FINAL:
        canales = 'Telefe / TV Publica / TyC Sports'
        notas = 'TV Publica anunciada para partidos de Argentina y la final.'
    return {
        'canales_argentina': canales,
        'streaming_argentina': 'A confirmar',
        'transmision_notas': notas,
    }


GROUP_MATCHES = [
    (1, 'A', '2026-06-11', 'Mexico City Stadium', 'Mexico City', 'Mexico', 'South Africa'),
    (2, 'A', '2026-06-11', 'Estadio Guadalajara', 'Guadalajara', 'Korea Republic', 'Czechia'),
    (3, 'B', '2026-06-12', 'Toronto Stadium', 'Toronto', 'Canada', 'Bosnia and Herzegovina'),
    (4, 'D', '2026-06-12', 'Los Angeles Stadium', 'Los Angeles', 'USA', 'Paraguay'),
    (5, 'C', '2026-06-13', 'Boston Stadium', 'Boston', 'Haiti', 'Scotland'),
    (6, 'D', '2026-06-13', 'BC Place Vancouver', 'Vancouver', 'Australia', 'Turkiye'),
    (7, 'C', '2026-06-13', 'New York New Jersey Stadium', 'New York/New Jersey', 'Brazil', 'Morocco'),
    (8, 'B', '2026-06-13', 'San Francisco Bay Area Stadium', 'San Francisco Bay Area', 'Qatar', 'Switzerland'),
    (9, 'E', '2026-06-14', 'Philadelphia Stadium', 'Philadelphia', "Cote d'Ivoire", 'Ecuador'),
    (10, 'E', '2026-06-14', 'Houston Stadium', 'Houston', 'Germany', 'Curacao'),
    (11, 'F', '2026-06-14', 'Dallas Stadium', 'Dallas', 'Netherlands', 'Japan'),
    (12, 'F', '2026-06-14', 'Estadio Monterrey', 'Monterrey', 'Sweden', 'Tunisia'),
    (13, 'H', '2026-06-15', 'Miami Stadium', 'Miami', 'Saudi Arabia', 'Uruguay'),
    (14, 'H', '2026-06-15', 'Atlanta Stadium', 'Atlanta', 'Spain', 'Cabo Verde'),
    (15, 'G', '2026-06-15', 'Los Angeles Stadium', 'Los Angeles', 'IR Iran', 'New Zealand'),
    (16, 'G', '2026-06-15', 'Seattle Stadium', 'Seattle', 'Belgium', 'Egypt'),
    (17, 'I', '2026-06-16', 'New York New Jersey Stadium', 'New York/New Jersey', 'France', 'Senegal'),
    (18, 'I', '2026-06-16', 'Boston Stadium', 'Boston', 'Iraq', 'Norway'),
    (19, 'J', '2026-06-16', 'Kansas City Stadium', 'Kansas City', 'Argentina', 'Algeria'),
    (20, 'J', '2026-06-16', 'San Francisco Bay Area Stadium', 'San Francisco Bay Area', 'Austria', 'Jordan'),
    (21, 'L', '2026-06-17', 'Toronto Stadium', 'Toronto', 'Ghana', 'Panama'),
    (22, 'L', '2026-06-17', 'Dallas Stadium', 'Dallas', 'England', 'Croatia'),
    (23, 'K', '2026-06-17', 'Houston Stadium', 'Houston', 'Portugal', 'Congo DR'),
    (24, 'K', '2026-06-17', 'Mexico City Stadium', 'Mexico City', 'Uzbekistan', 'Colombia'),
    (25, 'A', '2026-06-18', 'Atlanta Stadium', 'Atlanta', 'Czechia', 'South Africa'),
    (26, 'B', '2026-06-18', 'Los Angeles Stadium', 'Los Angeles', 'Switzerland', 'Bosnia and Herzegovina'),
    (27, 'B', '2026-06-18', 'BC Place Vancouver', 'Vancouver', 'Canada', 'Qatar'),
    (28, 'A', '2026-06-18', 'Estadio Guadalajara', 'Guadalajara', 'Mexico', 'Korea Republic'),
    (29, 'C', '2026-06-19', 'Philadelphia Stadium', 'Philadelphia', 'Brazil', 'Haiti'),
    (30, 'C', '2026-06-19', 'Boston Stadium', 'Boston', 'Scotland', 'Morocco'),
    (31, 'D', '2026-06-19', 'San Francisco Bay Area Stadium', 'San Francisco Bay Area', 'Turkiye', 'Paraguay'),
    (32, 'D', '2026-06-19', 'Seattle Stadium', 'Seattle', 'USA', 'Australia'),
    (33, 'E', '2026-06-20', 'Toronto Stadium', 'Toronto', 'Germany', "Cote d'Ivoire"),
    (34, 'E', '2026-06-20', 'Kansas City Stadium', 'Kansas City', 'Ecuador', 'Curacao'),
    (35, 'F', '2026-06-20', 'Houston Stadium', 'Houston', 'Netherlands', 'Sweden'),
    (36, 'F', '2026-06-20', 'Estadio Monterrey', 'Monterrey', 'Tunisia', 'Japan'),
    (37, 'H', '2026-06-21', 'Miami Stadium', 'Miami', 'Uruguay', 'Cabo Verde'),
    (38, 'H', '2026-06-21', 'Atlanta Stadium', 'Atlanta', 'Spain', 'Saudi Arabia'),
    (39, 'G', '2026-06-21', 'Los Angeles Stadium', 'Los Angeles', 'Belgium', 'IR Iran'),
    (40, 'G', '2026-06-21', 'BC Place Vancouver', 'Vancouver', 'New Zealand', 'Egypt'),
    (41, 'I', '2026-06-22', 'New York New Jersey Stadium', 'New York/New Jersey', 'Norway', 'Senegal'),
    (42, 'I', '2026-06-22', 'Philadelphia Stadium', 'Philadelphia', 'France', 'Iraq'),
    (43, 'J', '2026-06-22', 'Dallas Stadium', 'Dallas', 'Argentina', 'Austria'),
    (44, 'J', '2026-06-22', 'San Francisco Bay Area Stadium', 'San Francisco Bay Area', 'Jordan', 'Algeria'),
    (45, 'L', '2026-06-23', 'Boston Stadium', 'Boston', 'England', 'Ghana'),
    (46, 'L', '2026-06-23', 'Toronto Stadium', 'Toronto', 'Panama', 'Croatia'),
    (47, 'K', '2026-06-23', 'Houston Stadium', 'Houston', 'Portugal', 'Uzbekistan'),
    (48, 'K', '2026-06-23', 'Estadio Guadalajara', 'Guadalajara', 'Colombia', 'Congo DR'),
    (49, 'C', '2026-06-24', 'Miami Stadium', 'Miami', 'Scotland', 'Brazil'),
    (50, 'C', '2026-06-24', 'Atlanta Stadium', 'Atlanta', 'Morocco', 'Haiti'),
    (51, 'B', '2026-06-24', 'BC Place Vancouver', 'Vancouver', 'Switzerland', 'Canada'),
    (52, 'B', '2026-06-24', 'Seattle Stadium', 'Seattle', 'Bosnia and Herzegovina', 'Qatar'),
    (53, 'A', '2026-06-24', 'Mexico City Stadium', 'Mexico City', 'Czechia', 'Mexico'),
    (54, 'A', '2026-06-24', 'Estadio Monterrey', 'Monterrey', 'South Africa', 'Korea Republic'),
    (55, 'E', '2026-06-25', 'Philadelphia Stadium', 'Philadelphia', 'Curacao', "Cote d'Ivoire"),
    (56, 'E', '2026-06-25', 'New York New Jersey Stadium', 'New York/New Jersey', 'Ecuador', 'Germany'),
    (57, 'F', '2026-06-25', 'Dallas Stadium', 'Dallas', 'Japan', 'Sweden'),
    (58, 'F', '2026-06-25', 'Kansas City Stadium', 'Kansas City', 'Tunisia', 'Netherlands'),
    (59, 'D', '2026-06-25', 'Los Angeles Stadium', 'Los Angeles', 'Turkiye', 'USA'),
    (60, 'D', '2026-06-25', 'San Francisco Bay Area Stadium', 'San Francisco Bay Area', 'Paraguay', 'Australia'),
    (61, 'I', '2026-06-26', 'Boston Stadium', 'Boston', 'Norway', 'France'),
    (62, 'I', '2026-06-26', 'Toronto Stadium', 'Toronto', 'Senegal', 'Iraq'),
    (63, 'G', '2026-06-26', 'Seattle Stadium', 'Seattle', 'Egypt', 'IR Iran'),
    (64, 'G', '2026-06-26', 'BC Place Vancouver', 'Vancouver', 'New Zealand', 'Belgium'),
    (65, 'H', '2026-06-26', 'Houston Stadium', 'Houston', 'Cabo Verde', 'Saudi Arabia'),
    (66, 'H', '2026-06-26', 'Estadio Guadalajara', 'Guadalajara', 'Uruguay', 'Spain'),
    (67, 'L', '2026-06-27', 'New York New Jersey Stadium', 'New York/New Jersey', 'Panama', 'England'),
    (68, 'L', '2026-06-27', 'Philadelphia Stadium', 'Philadelphia', 'Croatia', 'Ghana'),
    (69, 'J', '2026-06-27', 'Kansas City Stadium', 'Kansas City', 'Algeria', 'Austria'),
    (70, 'J', '2026-06-27', 'Dallas Stadium', 'Dallas', 'Jordan', 'Argentina'),
    (71, 'K', '2026-06-27', 'Miami Stadium', 'Miami', 'Colombia', 'Portugal'),
    (72, 'K', '2026-06-27', 'Atlanta Stadium', 'Atlanta', 'Congo DR', 'Uzbekistan'),
]

KNOCKOUT_ROUNDS = [
    (73, Partido.FASE_16AVOS, '2026-06-28', '16avos 1', '16avos 2'),
    (74, Partido.FASE_16AVOS, '2026-06-28', '16avos 3', '16avos 4'),
    (75, Partido.FASE_16AVOS, '2026-06-28', '16avos 5', '16avos 6'),
    (76, Partido.FASE_16AVOS, '2026-06-29', '16avos 7', '16avos 8'),
    (77, Partido.FASE_16AVOS, '2026-06-29', '16avos 9', '16avos 10'),
    (78, Partido.FASE_16AVOS, '2026-06-29', '16avos 11', '16avos 12'),
    (79, Partido.FASE_16AVOS, '2026-06-30', '16avos 13', '16avos 14'),
    (80, Partido.FASE_16AVOS, '2026-06-30', '16avos 15', '16avos 16'),
    (81, Partido.FASE_16AVOS, '2026-06-30', '16avos 17', '16avos 18'),
    (82, Partido.FASE_16AVOS, '2026-07-01', '16avos 19', '16avos 20'),
    (83, Partido.FASE_16AVOS, '2026-07-01', '16avos 21', '16avos 22'),
    (84, Partido.FASE_16AVOS, '2026-07-01', '16avos 23', '16avos 24'),
    (85, Partido.FASE_16AVOS, '2026-07-02', '16avos 25', '16avos 26'),
    (86, Partido.FASE_16AVOS, '2026-07-02', '16avos 27', '16avos 28'),
    (87, Partido.FASE_16AVOS, '2026-07-03', '16avos 29', '16avos 30'),
    (88, Partido.FASE_16AVOS, '2026-07-03', '16avos 31', '16avos 32'),
    (89, Partido.FASE_16, '2026-07-04', 'Ganador 73', 'Ganador 74'),
    (90, Partido.FASE_16, '2026-07-04', 'Ganador 75', 'Ganador 76'),
    (91, Partido.FASE_16, '2026-07-05', 'Ganador 77', 'Ganador 78'),
    (92, Partido.FASE_16, '2026-07-05', 'Ganador 79', 'Ganador 80'),
    (93, Partido.FASE_16, '2026-07-06', 'Ganador 81', 'Ganador 82'),
    (94, Partido.FASE_16, '2026-07-06', 'Ganador 83', 'Ganador 84'),
    (95, Partido.FASE_16, '2026-07-07', 'Ganador 85', 'Ganador 86'),
    (96, Partido.FASE_16, '2026-07-07', 'Ganador 87', 'Ganador 88'),
    (97, Partido.FASE_CUARTOS, '2026-07-09', 'Ganador 89', 'Ganador 90'),
    (98, Partido.FASE_CUARTOS, '2026-07-10', 'Ganador 91', 'Ganador 92'),
    (99, Partido.FASE_CUARTOS, '2026-07-11', 'Ganador 93', 'Ganador 94'),
    (100, Partido.FASE_CUARTOS, '2026-07-11', 'Ganador 95', 'Ganador 96'),
    (101, Partido.FASE_SEMIS, '2026-07-14', 'Ganador 97', 'Ganador 98'),
    (102, Partido.FASE_SEMIS, '2026-07-15', 'Ganador 99', 'Ganador 100'),
    (103, Partido.FASE_TERCER_PUESTO, '2026-07-18', 'Perdedor 101', 'Perdedor 102'),
    (104, Partido.FASE_FINAL, '2026-07-19', 'Ganador 101', 'Ganador 102'),
]


class Command(BaseCommand):
    help = 'Carga equipos y partidos base del Mundial 2026.'

    def handle(self, *args, **options):
        equipos = {}
        for _, grupo, _, _, _, local, visitante in GROUP_MATCHES:
            for nombre in (local, visitante):
                equipo, _ = Equipo.objects.update_or_create(nombre=nombre, defaults={'grupo': grupo})
                equipos[nombre] = equipo

        creados = 0
        for numero, grupo, fecha, estadio, ciudad, local, visitante in GROUP_MATCHES:
            partido, created = Partido.objects.get_or_create(
                numero=numero,
                defaults={
                    'fase': Partido.FASE_GRUPOS,
                    'grupo': grupo,
                    'fecha': date.fromisoformat(fecha),
                    'hora': match_time(numero),
                    'estadio': estadio,
                    'ciudad': ciudad,
                    'equipo_local': equipos[local],
                    'equipo_visitante': equipos[visitante],
                    'etiqueta_local': '',
                    'etiqueta_visitante': '',
                    **transmision_argentina(local, visitante, Partido.FASE_GRUPOS),
                },
            )
            if not created:
                for campo, valor in {
                    'fase': Partido.FASE_GRUPOS,
                    'grupo': grupo,
                    'estadio': estadio,
                    'ciudad': ciudad,
                    'equipo_local': equipos[local],
                    'equipo_visitante': equipos[visitante],
                    'etiqueta_local': '',
                    'etiqueta_visitante': '',
                    **transmision_argentina(local, visitante, Partido.FASE_GRUPOS),
                }.items():
                    setattr(partido, campo, valor)
                partido.save(
                    update_fields=[
                        'fase',
                        'grupo',
                        'estadio',
                        'ciudad',
                        'equipo_local',
                        'equipo_visitante',
                        'etiqueta_local',
                        'etiqueta_visitante',
                        'canales_argentina',
                        'streaming_argentina',
                        'transmision_notas',
                    ]
                )
            creados += int(created)

        for index, (numero, fase, fecha, local, visitante) in enumerate(KNOCKOUT_ROUNDS, start=1):
            partido, created = Partido.objects.get_or_create(
                numero=numero,
                defaults={
                    'fase': fase,
                    'grupo': '',
                    'fecha': date.fromisoformat(fecha),
                    'hora': match_time(numero),
                    'estadio': 'Sede a confirmar',
                    'ciudad': '',
                    'equipo_local': None,
                    'equipo_visitante': None,
                    'etiqueta_local': local,
                    'etiqueta_visitante': visitante,
                    'notas': 'Actualizar cuando se definan los cruces.',
                    **transmision_argentina(local, visitante, fase),
                },
            )
            if not created:
                for campo, valor in {
                    'fase': fase,
                    'grupo': '',
                    'estadio': 'Sede a confirmar',
                    'ciudad': '',
                    'equipo_local': None,
                    'equipo_visitante': None,
                    'etiqueta_local': local,
                    'etiqueta_visitante': visitante,
                    'notas': 'Actualizar cuando se definan los cruces.',
                    **transmision_argentina(local, visitante, fase),
                }.items():
                    setattr(partido, campo, valor)
                partido.save(
                    update_fields=[
                        'fase',
                        'grupo',
                        'estadio',
                        'ciudad',
                        'equipo_local',
                        'equipo_visitante',
                        'etiqueta_local',
                        'etiqueta_visitante',
                        'notas',
                        'canales_argentina',
                        'streaming_argentina',
                        'transmision_notas',
                    ]
                )
            creados += int(created)

        self.stdout.write(self.style.SUCCESS(f'Fixture cargado. Partidos nuevos: {creados}.'))
