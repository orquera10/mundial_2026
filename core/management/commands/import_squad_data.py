from django.core.management.base import BaseCommand

from core.models import Equipo, JugadorSeleccion
from core.team_squads import SQUAD_DATA


class Command(BaseCommand):
    help = 'Importa codigos FIFA, tecnicos y convocados desde los datos extraidos del PDF de FIFA.'

    def handle(self, *args, **options):
        equipos_actualizados = 0
        jugadores_creados = 0
        faltantes = []

        for nombre_equipo, datos in SQUAD_DATA.items():
            try:
                equipo = Equipo.objects.get(nombre=nombre_equipo)
            except Equipo.DoesNotExist:
                faltantes.append(nombre_equipo)
                continue

            equipo.codigo_fifa = datos.get('codigo_fifa', '')
            equipo.tecnico = datos.get('tecnico', '')
            equipo.tecnico_nombre_tabla = datos.get('tecnico_nombre_tabla', '')
            equipo.tecnico_nombres = datos.get('tecnico_nombres', '')
            equipo.tecnico_apellidos = datos.get('tecnico_apellidos', '')
            equipo.tecnico_nacionalidad = datos.get('tecnico_nacionalidad', '')
            equipo.save(
                update_fields=[
                    'codigo_fifa',
                    'tecnico',
                    'tecnico_nombre_tabla',
                    'tecnico_nombres',
                    'tecnico_apellidos',
                    'tecnico_nacionalidad',
                ]
            )
            equipos_actualizados += 1

            equipo.jugadores.all().delete()
            jugadores = [
                JugadorSeleccion(
                    equipo=equipo,
                    orden=indice,
                    nombre=jugador.get('nombre', ''),
                    nombre_tabla=jugador.get('nombre_tabla', ''),
                    nombres=jugador.get('nombres', ''),
                    apellidos=jugador.get('apellidos', ''),
                    nombre_camiseta=jugador.get('nombre_camiseta', ''),
                    camiseta=jugador.get('camiseta', ''),
                    posicion=jugador.get('posicion', ''),
                    fecha_nacimiento=jugador.get('fecha_nacimiento', ''),
                    club=jugador.get('club', ''),
                    altura_cm=jugador.get('altura_cm'),
                    internacionalidades=jugador.get('internacionalidades'),
                    goles=jugador.get('goles'),
                )
                for indice, jugador in enumerate(datos.get('convocados', []), start=1)
            ]
            JugadorSeleccion.objects.bulk_create(jugadores)
            jugadores_creados += len(jugadores)

        self.stdout.write(
            self.style.SUCCESS(
                f'Equipos actualizados: {equipos_actualizados}. Jugadores importados: {jugadores_creados}.'
            )
        )
        if faltantes:
            self.stdout.write(self.style.WARNING(f'Equipos sin coincidencia: {", ".join(faltantes)}'))
