from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from .api_integration import sync_match_result
from .models import Equipo, Partido, Prediccion


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
        self.assertContains(response, 'Mas detalles')

    def test_tarjetas_usan_colores_de_las_selecciones(self):
        partido = Partido.objects.get(numero=1)

        self.assertEqual(partido.color_local, '#006847')
        self.assertEqual(partido.color_visitante, '#007a4d')

        response = self.client.get('/')

        self.assertContains(response, '--team-local: #006847')
        self.assertContains(response, '--team-visitor: #007a4d')

    def test_nombres_de_selecciones_linkean_a_su_pagina(self):
        mexico = Equipo.objects.get(nombre='Mexico')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/selecciones/{mexico.id}/')

    def test_pagina_de_seleccion_muestra_ficha_basica(self):
        mexico = Equipo.objects.get(nombre='Mexico')

        response = self.client.get(f'/selecciones/{mexico.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mexico')
        self.assertContains(response, 'CONCACAF')
        self.assertContains(response, 'Tecnico')
        self.assertContains(response, 'Lista de 26 convocados a confirmar')
        self.assertContains(response, 'Partidos')
        self.assertContains(response, 'mini-flag')
        self.assertContains(response, 'match-expanded')

    def test_home_muestra_filtros_compactados(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'filter-panel')
        self.assertContains(response, 'Todos los partidos')
        self.assertNotContains(response, '<details class="panel filter-panel" open>', html=False)

    def test_home_abre_filtros_si_hay_filtro_activo(self):
        response = self.client.get('/', {'grupo': 'A'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="panel filter-panel" open>', html=False)
        self.assertContains(response, 'Activos')

    def test_almanaque_muestra_filtros_compactados(self):
        response = self.client.get('/almanaque/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'filter-panel')
        self.assertContains(response, 'Todo el almanaque')
        self.assertNotContains(response, '<details class="panel filter-panel" open>', html=False)

    def test_almanaque_abre_filtros_si_hay_filtro_activo(self):
        response = self.client.get('/almanaque/', {'grupo': 'A'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="panel filter-panel" open>', html=False)
        self.assertContains(response, 'Activos')

    def test_pagina_detalle_partido_muestra_informacion_ordenada(self):
        partido = Partido.objects.get(numero=1)

        response = self.client.get(f'/partidos/{partido.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Partido 1')
        self.assertContains(response, 'Mexico')
        self.assertContains(response, 'South Africa')
        self.assertContains(response, 'Fecha y hora Argentina')
        self.assertContains(response, 'TV Argentina')
        self.assertNotContains(response, 'Datos del evento')
        self.assertNotContains(response, 'Alineaciones')
        self.assertNotContains(response, 'ID Football-Data')
        self.assertNotContains(response, 'Etapa API')
        self.assertContains(response, 'Tabla Grupo A')
        self.assertContains(response, 'Proximos del Grupo A')
        self.assertContains(response, 'Korea Republic vs Czechia')
        self.assertContains(response, '--team-local: #006847')
        self.assertContains(response, '--team-visitor: #007a4d')

    def test_pagina_detalle_partido_precarga_prediccion_logueado(self):
        usuario = User.objects.create_user(username='detalle', password='clave-segura-123')
        partido = Partido.objects.get(numero=19)
        Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=2, goles_visitante=0)
        self.client.force_login(usuario)

        response = self.client.get(f'/partidos/{partido.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'value="0"')

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
        self.assertContains(response, 'live-indicator')
        self.assertContains(response, 'livePulse')

    def test_home_muestra_indicador_en_vivo_solo_en_partidos_en_vivo(self):
        partido = Partido.objects.get(numero=2)
        partido.estado = Partido.ESTADO_EN_VIVO
        partido.goles_local = 0
        partido.goles_visitante = 0
        partido.save(update_fields=['estado', 'goles_local', 'goles_visitante'])

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('aria-label="Partido en vivo"'), 2)
        self.assertEqual(response.content.decode().count('data-partido-id="2"'), 2)

    def test_home_incluye_partidos_en_vivo_en_seccion_proximos(self):
        partido = Partido.objects.get(numero=2)
        partido.estado = Partido.ESTADO_EN_VIVO
        partido.goles_local = 0
        partido.goles_visitante = 0
        partido.save(update_fields=['estado', 'goles_local', 'goles_visitante'])

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'En vivo y próximos')
        self.assertContains(response, 'Korea Republic')
        self.assertContains(response, 'Czechia')

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
                    'matchday': 1,
                    'stage': 'GROUP_STAGE',
                    'group': 'GROUP_A',
                    'lastUpdated': '2026-06-11T00:20:16Z',
                    'homeTeam': {'name': 'Mexico'},
                    'awayTeam': {'name': 'South Africa'},
                    'score': {'fullTime': {'home': 2, 'away': 1}},
                    'referees': [{'name': 'Wilton Sampaio', 'type': 'REFEREE', 'nationality': 'Brazil'}],
                }
            ],
        )

        partido.refresh_from_db()
        self.assertTrue(actualizado)
        self.assertEqual(partido.estado, Partido.ESTADO_FINALIZADO)
        self.assertEqual(partido.goles_local, 2)
        self.assertEqual(partido.goles_visitante, 1)
        self.assertEqual(partido.football_data_id, 537327)
        self.assertEqual(partido.jornada, 1)
        self.assertEqual(partido.etapa_api, 'GROUP_STAGE')
        self.assertEqual(partido.grupo_api, 'GROUP_A')
        self.assertEqual(partido.arbitro, 'Wilton Sampaio')
        self.assertEqual(partido.arbitro_nacionalidad, 'Brazil')

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

    def test_sync_due_matches_omite_partidos_antes_del_inicio(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        from core.api_integration import sync_due_matches_results

        ahora = datetime(2026, 6, 11, 15, 30, tzinfo=ZoneInfo('America/Argentina/Buenos_Aires'))

        with patch('core.api_integration.fetch_football_data_range', return_value=[]) as fetch:
            resultado = sync_due_matches_results(now=ahora)

        fetch.assert_not_called()
        self.assertEqual(resultado['consultados'], 0)
        self.assertEqual(resultado['actualizados'], 0)

    def test_sync_due_matches_consulta_y_actualiza_partido_en_curso(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        from core.api_integration import sync_due_matches_results

        ahora = datetime(2026, 6, 11, 16, 30, tzinfo=ZoneInfo('America/Argentina/Buenos_Aires'))
        matches = [
            {
                'id': 537327,
                'status': 'IN_PLAY',
                'homeTeam': {'name': 'Mexico'},
                'awayTeam': {'name': 'South Africa'},
                'score': {'fullTime': {'home': 1, 'away': 0}},
            }
        ]

        with patch('core.api_integration.fetch_football_data_range', return_value=matches) as fetch:
            resultado = sync_due_matches_results(now=ahora)

        partido = Partido.objects.get(numero=1)
        fetch.assert_called_once_with('2026-06-10', '2026-06-12')
        self.assertEqual(resultado['consultados'], 1)
        self.assertEqual(resultado['actualizados'], 1)
        self.assertEqual(partido.estado, Partido.ESTADO_EN_VIVO)
        self.assertEqual(partido.goles_local, 1)
        self.assertEqual(partido.goles_visitante, 0)

    def test_sync_due_matches_no_consulta_partidos_fuera_de_ventana(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        from core.api_integration import sync_due_matches_results

        ahora = datetime(2026, 6, 12, 10, 0, tzinfo=ZoneInfo('America/Argentina/Buenos_Aires'))

        with patch('core.api_integration.fetch_football_data_range', return_value=[]) as fetch:
            resultado = sync_due_matches_results(now=ahora, follow_hours=8)

        fetch.assert_not_called()
        self.assertEqual(resultado['consultados'], 0)

    def test_sync_due_matches_usa_fecha_utc_para_api(self):
        from datetime import datetime
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        from core.api_integration import sync_due_matches_results

        partido_1 = Partido.objects.get(numero=1)
        partido_1.estado = Partido.ESTADO_FINALIZADO
        partido_1.save(update_fields=['estado'])
        partido_2 = Partido.objects.get(numero=2)
        partido_2.fecha = '2026-06-11'
        partido_2.hora = '20:00'
        partido_2.ciudad = 'Mexico City'
        partido_2.save(update_fields=['fecha', 'hora', 'ciudad'])
        ahora = datetime(2026, 6, 11, 23, 30, tzinfo=ZoneInfo('America/Argentina/Buenos_Aires'))

        with patch('core.api_integration.fetch_football_data_range', return_value=[]) as fetch:
            resultado = sync_due_matches_results(now=ahora, follow_hours=12)

        fetch.assert_called_once_with('2026-06-11', '2026-06-13')
        self.assertEqual(resultado['consultados'], 1)

    def test_sync_results_command_acepta_fase_previa(self):
        from io import StringIO
        from unittest.mock import patch

        from core.management.commands.sync_results import Command

        with patch('core.management.commands.sync_results.sync_matches_results', return_value=72) as sync:
            command = Command()
            command.stdout = StringIO()
            command.handle(date_from='', date_to='', fase_previa=True)

        sync.assert_called_once_with(date_from='2026-06-11', date_to='2026-06-30')

    def test_poll_results_command_puede_ejecutar_una_vez(self):
        from io import StringIO
        from unittest.mock import patch

        from django.core.management import call_command

        with patch('core.management.commands.poll_results.sync_matches_results', return_value=3) as sync:
            output = StringIO()
            call_command('poll_results', '--fase-previa', '--once', stdout=output)

        sync.assert_called_once_with(date_from='2026-06-11', date_to='2026-06-30')
        self.assertIn('Partidos actualizados: 3', output.getvalue())

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

    def test_prediccion_compara_resultado_final(self):
        usuario = User.objects.create_user(username='comparador', password='clave-segura-123')
        partido = Partido.objects.get(numero=1)
        partido.estado = Partido.ESTADO_FINALIZADO
        partido.goles_local = 2
        partido.goles_visitante = 0
        partido.save(update_fields=['estado', 'goles_local', 'goles_visitante'])

        exacta = Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=2, goles_visitante=0)
        self.assertEqual(exacta.comparacion_estado, 'exacta')

        exacta.goles_local = 3
        exacta.goles_visitante = 1
        self.assertEqual(exacta.comparacion_estado, 'ganador')

        exacta.goles_local = 0
        exacta.goles_visitante = 1
        self.assertEqual(exacta.comparacion_estado, 'fallida')

    def test_home_pinta_badge_de_prediccion_finalizada(self):
        usuario = User.objects.create_user(username='badge-final', password='clave-segura-123')
        partido = Partido.objects.get(numero=1)
        partido.estado = Partido.ESTADO_FINALIZADO
        partido.goles_local = 2
        partido.goles_visitante = 0
        partido.save(update_fields=['estado', 'goles_local', 'goles_visitante'])
        Prediccion.objects.create(usuario=usuario, partido=partido, goles_local=3, goles_visitante=1)
        self.client.force_login(usuario)

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'compact-prediction-badge ganador')
        self.assertContains(response, 'Ganador acertado')

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

    def test_home_muestra_predicciones_guardadas_en_fase_final(self):
        usuario = User.objects.create_user(username='home-final', password='clave-segura-123')
        self.client.force_login(usuario)
        for numero, local, visitante in [(1, 3, 0), (28, 2, 0), (53, 0, 1)]:
            Prediccion.objects.create(
                usuario=usuario,
                partido=Partido.objects.get(numero=numero),
                goles_local=local,
                goles_visitante=visitante,
            )
        Prediccion.objects.create(
            usuario=usuario,
            partido=Partido.objects.get(numero=73),
            goles_local=2,
            goles_visitante=1,
        )

        response = self.client.get('/', {'fase': Partido.FASE_16AVOS})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Segun tus predicciones')
        self.assertContains(response, 'Mexico')
        self.assertContains(response, 'value="2"')
        self.assertContains(response, 'value="1"')
        self.assertContains(response, 'compact-prediction-badge')
        self.assertContains(response, '.projection-team img')
        self.assertContains(response, 'max-width: 1.25rem')

    def test_home_no_muestra_proyeccion_final_si_no_hay_clasificados(self):
        usuario = User.objects.create_user(username='home-final-empty', password='clave-segura-123')
        self.client.force_login(usuario)

        response = self.client.get('/', {'fase': Partido.FASE_CUARTOS})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Segun tus predicciones')

    def test_almanaque_muestra_proyeccion_final_con_predicciones(self):
        usuario = User.objects.create_user(username='almanaque-final', password='clave-segura-123')
        self.client.force_login(usuario)
        for numero, local, visitante in [(1, 3, 0), (28, 2, 0), (53, 0, 1)]:
            Prediccion.objects.create(
                usuario=usuario,
                partido=Partido.objects.get(numero=numero),
                goles_local=local,
                goles_visitante=visitante,
            )

        response = self.client.get('/almanaque/', {'fase': Partido.FASE_16AVOS})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Segun tus predicciones')
        self.assertContains(response, 'Mexico')

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
