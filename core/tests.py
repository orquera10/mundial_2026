from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from .api_integration import sync_match_result
from .models import Partido, Prediccion


class MundialHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_mundial_2026', verbosity=0)

    def test_fixture_inicial_carga_104_partidos(self):
        self.assertEqual(Partido.objects.count(), 104)

    def test_home_muestra_tablero(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Partidos del Mundial 2026')
        self.assertContains(response, '104')

    def test_home_muestra_partidos_desplegables(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="match-card', html=False)
        self.assertContains(response, 'match-summary')
        self.assertContains(response, 'match-expanded')

    def test_horario_se_muestra_en_hora_argentina(self):
        partido = Partido.objects.get(numero=4)

        self.assertEqual(partido.ciudad, 'Los Angeles')
        self.assertEqual(partido.horario, '22:00')
        self.assertEqual(partido.fecha_argentina.isoformat(), '2026-06-13')
        self.assertEqual(partido.horario_argentina, '02:00 ARG')

    def test_home_renderiza_actualizador_de_partidos_en_vivo(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'actualizarPartidosEnVivo')
        self.assertContains(response, '/api/partidos-vivo/')

    def test_api_partidos_vivo_devuelve_marcador_actual(self):
        partido = Partido.objects.get(numero=1)
        partido.estado = Partido.ESTADO_EN_VIVO
        partido.goles_local = 0
        partido.goles_visitante = 1
        partido.save(update_fields=['estado', 'goles_local', 'goles_visitante'])

        response = self.client.get('/api/partidos-vivo/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    'id': partido.id,
                    'goles_local': 0,
                    'goles_visitante': 1,
                    'marcador': '0 - 1',
                    'estado': Partido.ESTADO_EN_VIVO,
                    'estado_display': 'En vivo',
                }
            ],
        )

    def test_sync_match_result_actualiza_cero_goles_y_estado(self):
        partido = Partido.objects.get(numero=1)
        actualizado = sync_match_result(
            partido,
            [
                {
                    'matchNumber': 1,
                    'status': 'IN_PLAY',
                    'score': {'fullTime': {'home': 0, 'away': 2}},
                }
            ],
        )

        partido.refresh_from_db()
        self.assertTrue(actualizado)
        self.assertEqual(partido.estado, Partido.ESTADO_EN_VIVO)
        self.assertEqual(partido.goles_local, 0)
        self.assertEqual(partido.goles_visitante, 2)

    def test_sync_match_result_empareja_formato_football_data_por_equipos(self):
        partido = Partido.objects.get(numero=1)
        actualizado = sync_match_result(
            partido,
            [
                {
                    'id': 537327,
                    'status': 'FINISHED',
                    'homeTeam': {'name': 'Mexico'},
                    'awayTeam': {'name': 'South Africa'},
                    'score': {'fullTime': {'home': 2, 'away': 1}},
                }
            ],
        )

        partido.refresh_from_db()
        self.assertTrue(actualizado)
        self.assertEqual(partido.estado, Partido.ESTADO_FINALIZADO)
        self.assertEqual(partido.goles_local, 2)
        self.assertEqual(partido.goles_visitante, 1)

    def test_sync_match_result_actualiza_horario_desde_utc_y_alias_de_equipo(self):
        partido = Partido.objects.get(numero=2)
        actualizado = sync_match_result(
            partido,
            [
                {
                    'status': 'TIMED',
                    'utcDate': '2026-06-12T02:00:00Z',
                    'homeTeam': {'name': 'South Korea'},
                    'awayTeam': {'name': 'Czechia'},
                    'score': {'fullTime': {'home': None, 'away': None}},
                }
            ],
        )

        partido.refresh_from_db()
        self.assertTrue(actualizado)
        self.assertEqual(partido.fecha.isoformat(), '2026-06-11')
        self.assertEqual(partido.horario, '20:00')
        self.assertEqual(partido.fecha_argentina.isoformat(), '2026-06-11')
        self.assertEqual(partido.horario_argentina, '23:00 ARG')

    def test_sync_results_command_acepta_fase_previa(self):
        from io import StringIO
        from unittest.mock import patch

        from core.management.commands.sync_results import Command

        with patch('core.management.commands.sync_results.sync_matches_results', return_value=72) as sync:
            command = Command()
            command.stdout = StringIO()
            command.handle(date_from='', date_to='', fase_previa=True)

        sync.assert_called_once_with(date_from='2026-06-11', date_to='2026-06-27')

    def test_busqueda_por_equipo_filtra_partidos(self):
        response = self.client.get('/', {'q': 'Argentina'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Argentina')
        self.assertContains(response, 'Algeria')
        self.assertContains(response, '3 resultado/s')

    def test_usuario_logueado_puede_guardar_prediccion(self):
        usuario = User.objects.create_user(username='demo', password='clave-segura-123')
        partido = Partido.objects.get(numero=19)
        self.client.force_login(usuario)

        response = self.client.post(
            f'/partidos/{partido.id}/prediccion/',
            {'goles_local': '2', 'goles_visitante': '1', 'next': '/'},
        )

        self.assertEqual(response.status_code, 302)
        prediccion = Prediccion.objects.get(usuario=usuario, partido=partido)
        self.assertEqual(prediccion.goles_local, 2)
        self.assertEqual(prediccion.goles_visitante, 1)

    def test_pagina_predicciones_muestra_grupos(self):
        response = self.client.get('/predicciones/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Predicciones')
        self.assertContains(response, 'Grupo A')
        self.assertContains(response, 'Mexico')

    def test_pagina_predicciones_actualiza_tabla_en_cliente(self):
        response = self.client.get('/predicciones/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'actualizarTablaGrupo')
        self.assertContains(response, 'data-team-row')
        self.assertContains(response, 'prediction:saved')

    def test_pagina_predicciones_muestra_fase_final(self):
        response = self.client.get('/predicciones/', {'vista': 'final'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fase final')
        self.assertContains(response, '16avos de final')
        self.assertContains(response, 'Partido 73')

    def test_pagina_predicciones_muestra_llaves(self):
        response = self.client.get('/predicciones/', {'vista': 'llaves'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Llaves')
        self.assertContains(response, 'bracket-board')

    def test_fase_final_usa_clasificados_de_predicciones(self):
        usuario = User.objects.create_user(username='bracket', password='clave-segura-123')
        self.client.force_login(usuario)
        for numero, local, visitante in [(1, 3, 0), (28, 2, 0), (53, 0, 1)]:
            Prediccion.objects.create(
                usuario=usuario,
                partido=Partido.objects.get(numero=numero),
                goles_local=local,
                goles_visitante=visitante,
            )

        response = self.client.get('/predicciones/', {'vista': 'final'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1° Mexico')

    def test_pagina_predicciones_precarga_marcador_guardado(self):
        usuario = User.objects.create_user(username='predictor', password='clave-segura-123')
        partido = Partido.objects.get(numero=19)
        Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=3, goles_visitante=2)
        self.client.force_login(usuario)

        response = self.client.get('/predicciones/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="3"')
        self.assertContains(response, 'value="2"')

    def test_prediccion_ajax_guarda_sin_redireccion(self):
        usuario = User.objects.create_user(username='ajax', password='clave-segura-123')
        partido = Partido.objects.get(numero=19)
        self.client.force_login(usuario)

        response = self.client.post(
            f'/partidos/{partido.id}/prediccion/',
            {'goles_local': '1', 'goles_visitante': '0'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertTrue(Prediccion.objects.filter(usuario=usuario, partido=partido).exists())

    def test_resetear_prediccion_ajax(self):
        usuario = User.objects.create_user(username='reset-one', password='clave-segura-123')
        partido = Partido.objects.get(numero=19)
        Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=2, goles_visitante=0)
        self.client.force_login(usuario)

        response = self.client.post(
            f'/partidos/{partido.id}/prediccion/reset/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Prediccion.objects.filter(usuario=usuario, partido=partido).exists())

    def test_resetear_todas_las_predicciones(self):
        usuario = User.objects.create_user(username='reset-all', password='clave-segura-123')
        partidos = [Partido.objects.get(numero=19), Partido.objects.get(numero=43)]
        for partido in partidos:
            Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=1, goles_visitante=1)
        self.client.force_login(usuario)

        response = self.client.post('/predicciones/reset/', {'next': '/predicciones/'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Prediccion.objects.filter(usuario=usuario).count(), 0)

# Create your tests here.
