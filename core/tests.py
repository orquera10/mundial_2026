from django.core.management import call_command
from django.db.models import Q
from django.test import TestCase
from django.contrib.auth.models import User

from .api_integration import sync_match_result
from .models import Equipo, EquipoFavorito, JugadorSeleccion, Partido, PartidoFavorito, Prediccion


class MundialHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_mundial_2026', verbosity=0)
        call_command('import_squad_data', verbosity=0)

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
        self.assertContains(response, 'summary-details-link')
        self.assertContains(response, 'card-bottom-arrow')
        self.assertContains(response, 'Ir al detalle del partido')
        self.assertContains(response, 'Mas detalles')

    def test_tarjetas_usan_colores_de_las_selecciones(self):
        partido = Partido.objects.get(numero=1)

        self.assertEqual(partido.color_local, '#006847')
        self.assertEqual(partido.color_visitante, '#007a4d')
        self.assertEqual(partido.color_local_secundario, '#ffffff')
        self.assertEqual(partido.color_local_terciario, '#ce1126')
        self.assertEqual(partido.color_visitante_secundario, '#ffb612')
        self.assertEqual(partido.color_visitante_terciario, '#de3831')

        response = self.client.get('/')

        self.assertContains(response, '--team-local: #006847')
        self.assertContains(response, '--team-visitor: #007a4d')
        self.assertContains(response, '--team-local-third: #ce1126')
        self.assertContains(response, '--team-visitor-third: #de3831')

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
        self.assertContains(response, 'href="/paises/"')
        self.assertContains(response, 'aria-label="Volver"')
        self.assertContains(response, 'background: #ce1126')
        self.assertContains(response, 'CONCACAF')
        self.assertContains(response, 'Javier Aguirre')
        self.assertContains(response, 'Raul Rangel')
        self.assertContains(response, 'Rangel')
        self.assertContains(response, 'Partidos')
        self.assertContains(response, 'squad-shirt')
        self.assertContains(response, 'Camiseta 1')
        self.assertContains(response, 'class="portero"')
        self.assertContains(response, 'class="defensa"')
        self.assertContains(response, 'class="mediocentro"')
        self.assertContains(response, 'class="delantero"')
        self.assertLess(
            response.content.decode().find('class="portero"'),
            response.content.decode().find('class="defensa"'),
        )
        self.assertContains(response, 'Partidos')
        self.assertContains(response, 'mini-flag')
        self.assertContains(response, 'match-expanded')

    def test_botones_volver_respetan_pagina_de_origen(self):
        mexico = Equipo.objects.get(nombre='Mexico')
        partido = Partido.objects.get(numero=1)

        response = self.client.get(
            f'/selecciones/{mexico.id}/',
            HTTP_REFERER='http://testserver/paises/?q=mex',
        )
        self.assertContains(response, 'href="http://testserver/paises/?q=mex"')

        response = self.client.get(
            f'/partidos/{partido.id}/',
            HTTP_REFERER='http://testserver/almanaque/?grupo=A',
        )
        self.assertContains(response, 'href="http://testserver/almanaque/?grupo=A"')

        response = self.client.get(
            f'/partidos/{partido.id}/',
            HTTP_REFERER='http://testserver/predicciones/?vista=final',
        )
        self.assertContains(response, 'href="http://testserver/predicciones/?vista=final"')

        response = self.client.get(
            f'/selecciones/{mexico.id}/',
            HTTP_REFERER=f'http://testserver/partidos/{partido.id}/',
        )
        self.assertContains(response, f'href="http://testserver/partidos/{partido.id}/"')

        response = self.client.get(
            '/estadios/mexico-city-stadium/',
            HTTP_REFERER='http://testserver/partidos/1/',
        )
        self.assertContains(response, 'href="/estadios/"')

    def test_nombre_de_camiseta_no_arrastra_apellido_pegado(self):
        argentina = Equipo.objects.get(nombre='Argentina')

        response = self.client.get(f'/selecciones/{argentina.id}/')

        self.assertContains(response, 'argentina-shirt')
        self.assertContains(response, 'Enzo Fernandez')
        self.assertContains(response, 'E. Fernandez')
        self.assertNotContains(response, 'Ndeze. Fernandez')
        self.assertContains(response, 'Lisandro Martinez')
        self.assertContains(response, 'Martinez')
        self.assertNotContains(response, 'Camiseta 6 Nez')
        self.assertContains(response, 'Nico Paz')
        self.assertNotContains(response, 'Neznico Paz')

    def test_importa_columnas_completas_del_pdf_fifa(self):
        cristiano = JugadorSeleccion.objects.get(equipo__nombre='Portugal', nombre='Cristiano Ronaldo')
        enzo = JugadorSeleccion.objects.get(equipo__nombre='Argentina', nombre='Enzo Fernandez')
        lisandro = JugadorSeleccion.objects.get(equipo__nombre='Argentina', nombre='Lisandro Martinez')
        portugal = Equipo.objects.get(nombre='Portugal')

        self.assertEqual(JugadorSeleccion.objects.count(), 1248)
        self.assertEqual(cristiano.nombre_tabla, 'CRISTIANO RONALDO')
        self.assertEqual(cristiano.nombres, 'Cristiano Ronaldo')
        self.assertEqual(cristiano.apellidos, 'Dos Santos Aveiro')
        self.assertEqual(cristiano.camiseta, 'Ronaldo')
        self.assertEqual(cristiano.nombre_camiseta, 'RONALDO')
        self.assertEqual(cristiano.club, 'Al Nassr FC (KSA)')
        self.assertEqual(cristiano.altura_cm, 185)
        self.assertEqual(cristiano.internacionalidades, 228)
        self.assertEqual(cristiano.goles, 143)
        self.assertEqual(enzo.nombre_tabla, 'FERNANDEZ Enzo')
        self.assertEqual(enzo.nombres, 'Enzo Jeremías')
        self.assertEqual(enzo.apellidos, 'Fernández')
        self.assertEqual(enzo.nombre_camiseta, 'E. FERNANDEZ')
        self.assertEqual(lisandro.apellidos, 'Martínez')
        self.assertEqual(lisandro.nombre_camiseta, 'MARTÍNEZ')
        self.assertEqual(portugal.tecnico_nombres, 'Roberto')
        self.assertEqual(portugal.tecnico_apellidos, 'Martínez Montoliu')
        self.assertEqual(portugal.tecnico_nacionalidad, 'Spain')

    def test_menu_y_pagina_paises_listan_selecciones(self):
        response = self.client.get('/')
        self.assertContains(response, 'Paises')
        self.assertContains(response, '/paises/')

        response = self.client.get('/paises/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paises')
        self.assertContains(response, 'Mexico')
        self.assertContains(response, 'Argentina')
        self.assertContains(response, 'aria-label="Ver seleccion Mexico"')

    def test_menu_y_pagina_estadios_listan_sedes(self):
        response = self.client.get('/')
        self.assertContains(response, 'Estadios')
        self.assertContains(response, '/estadios/')

        response = self.client.get('/estadios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estadios')
        self.assertContains(response, 'Fuente FIFA')
        self.assertContains(response, 'Mexico City Stadium')
        self.assertContains(response, 'Estadio Azteca')
        self.assertContains(response, 'New York New Jersey Stadium')
        self.assertContains(response, 'MetLife Stadium')
        self.assertContains(response, '16 estadios')
        self.assertContains(response, 'href="/estadios/mexico-city-stadium/"')
        self.assertContains(response, 'aria-label="Ver estadio Mexico City Stadium"')
        self.assertContains(response, 'core/img/stadiums/mexico-city-stadium.jpeg')
        self.assertContains(response, 'stadium-glyph')

    def test_pagina_detalle_estadio_muestra_data_del_word(self):
        response = self.client.get('/estadios/mexico-city-stadium/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mexico City Stadium')
        self.assertContains(response, 'Estadio Azteca')
        self.assertContains(response, 'core/img/stadiums/mexico-city-stadium.jpeg')
        self.assertContains(response, 'stadium-glyph')
        self.assertContains(response, '80.824')
        self.assertContains(response, '1966')
        self.assertContains(response, 'Partido 1')
        self.assertNotContains(response, 'Fixture FIFA del documento')
        self.assertContains(response, 'Un verdadero coliseo del fútbol mundial')
        self.assertNotContains(response, 'Partido 24 – Uzbekistán')

    def test_estadio_filadelfia_usa_imagen_agregada(self):
        response = self.client.get('/estadios/philadelphia-stadium/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Philadelphia Stadium')
        self.assertContains(response, 'core/img/stadiums/filadelfia_stadium.jpg')

    def test_usuario_puede_marcar_pais_favorito(self):
        usuario = User.objects.create_user(username='paises', password='clave-segura-123')
        mexico = Equipo.objects.get(nombre='Mexico')
        self.client.force_login(usuario)

        response = self.client.post(
            f'/selecciones/{mexico.id}/favorito/',
            {'next': '/paises/'},
            follow=True,
        )

        self.assertRedirects(response, '/paises/')
        self.assertTrue(EquipoFavorito.objects.filter(usuario=usuario, equipo=mexico).exists())
        partidos_mexico = Partido.objects.filter(Q(equipo_local=mexico) | Q(equipo_visitante=mexico))
        self.assertEqual(
            PartidoFavorito.objects.filter(usuario=usuario, partido__in=partidos_mexico).count(),
            partidos_mexico.count(),
        )
        self.assertContains(response, 'bi-star-fill')

        self.client.post(f'/selecciones/{mexico.id}/favorito/', {'next': '/paises/'})
        self.assertFalse(EquipoFavorito.objects.filter(usuario=usuario, equipo=mexico).exists())

    def test_home_muestra_favoritos_en_desplegable_cerrado(self):
        usuario = User.objects.create_user(username='favoritos', password='clave-segura-123')
        partido = Partido.objects.get(numero=1)
        PartidoFavorito.objects.create(usuario=usuario, partido=partido)
        self.client.force_login(usuario)

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<details class="panel filter-panel favorites-panel">', html=False)
        self.assertContains(response, 'favorite-compact')
        self.assertContains(response, 'Favoritos')
        self.assertContains(response, '1 partido')
        self.assertContains(response, 'Mexico')
        self.assertContains(response, 'South Africa')
        self.assertContains(response, f'href="/selecciones/{partido.equipo_local_id}/"')
        self.assertContains(response, f'href="/selecciones/{partido.equipo_visitante_id}/"')

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
        self.assertContains(response, partido.horario_argentina)
        self.assertContains(response, 'href="/estadios/mexico-city-stadium/"')
        self.assertContains(response, 'Mexico City Stadium')
        self.assertNotContains(response, 'Fecha y hora Argentina')
        self.assertNotContains(response, 'Fecha y hora local')
        self.assertNotContains(response, 'TV Argentina')
        self.assertNotContains(response, 'Streaming')
        self.assertNotContains(response, 'Datos del evento')
        self.assertNotContains(response, 'Alineaciones')
        self.assertNotContains(response, 'ID Football-Data')
        self.assertNotContains(response, 'Etapa API')
        self.assertContains(response, 'Grupo A')
        self.assertContains(response, f'href="/selecciones/{partido.equipo_local_id}/"')
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
        self.assertEqual(partido.horario, '18:00')
        self.assertEqual(partido.fecha_argentina.isoformat(), '2026-06-12')
        self.assertEqual(partido.horario_argentina, '22:00 ARG')

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
        partido.estado_api = 'IN_PLAY'
        partido.goles_local = 0
        partido.goles_visitante = 1
        partido.jornada = 1
        partido.etapa_api = 'GROUP_STAGE'
        partido.grupo_api = 'GROUP_A'
        partido.arbitro = 'Wilton Sampaio'
        partido.arbitro_nacionalidad = 'Brazil'
        partido.football_data_id = 537327
        partido.save(
            update_fields=[
                'estado',
                'estado_api',
                'goles_local',
                'goles_visitante',
                'jornada',
                'etapa_api',
                'grupo_api',
                'arbitro',
                'arbitro_nacionalidad',
                'football_data_id',
            ]
        )

        response = self.client.get('/api/partidos-vivo/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], partido.id)
        self.assertEqual(data[0]['goles_local'], 0)
        self.assertEqual(data[0]['goles_visitante'], 1)
        self.assertEqual(data[0]['marcador'], '0 - 1')
        self.assertEqual(data[0]['estado'], Partido.ESTADO_EN_VIVO)
        self.assertEqual(data[0]['estado_display'], 'En juego')
        self.assertNotIn('jornada', data[0])
        self.assertNotIn('etapa_api', data[0])
        self.assertNotIn('grupo_api', data[0])
        self.assertNotIn('football_data_id', data[0])

    def test_partido_detalle_muestra_datos_de_seguimiento(self):
        partido = Partido.objects.get(numero=1)
        partido.estado = Partido.ESTADO_EN_VIVO
        partido.estado_api = 'PAUSED'
        partido.goles_local = 2
        partido.goles_visitante = 1
        partido.jornada = 1
        partido.etapa_api = 'GROUP_STAGE'
        partido.grupo_api = 'GROUP_A'
        partido.arbitro = 'Wilton Sampaio'
        partido.arbitro_nacionalidad = 'Brazil'
        partido.football_data_id = 537327
        partido.save()

        response = self.client.get(f'/partidos/{partido.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seguimiento del partido')
        self.assertContains(response, 'href="/estadios/mexico-city-stadium/"')
        self.assertContains(response, 'Wilton Sampaio')
        self.assertNotContains(response, '<h2><span class="label-with-icon"><span class="icon" aria-hidden="true"><i class="bi bi-info-circle"></i></span>Informacion</span></h2>', html=True)
        self.assertNotContains(response, 'Fecha y hora local')
        self.assertNotContains(response, 'TV Argentina')
        self.assertNotContains(response, 'Streaming')
        self.assertNotContains(response, 'data-live-status-card')
        self.assertNotContains(response, 'data-scraper-event')
        self.assertNotContains(response, 'GROUP_STAGE')
        self.assertNotContains(response, 'GROUP_A')
        self.assertNotContains(response, '537327')

    def test_api_partido_seguimiento_usa_scraper(self):
        from unittest.mock import patch

        partido = Partido.objects.get(numero=1)
        scraped_match = {
            'event_id': 'abc123',
            'status': 'finalizado',
            'url': 'https://www.flashscore.com.ar/partido/futbol/mexico-a/south-africa-b/?mid=abc123',
            'score': {'home': '2', 'away': '0'},
        }
        lineups = {
            'teams': {
                'Mexico': {
                    'formation': '1-4-3-3',
                    'starters': [
                        {
                            'db_match': 'Raul Rangel',
                            'flashscore_name': 'Rangel R.',
                            'number': '1',
                            'db_position': 'Portero',
                            'rating': '7.1',
                            'substitution_minute': "70'",
                            'substitution_player': 'Ochoa G.',
                            'substitution_player_number': '13',
                            'substitution_kind': 'out',
                            'matched': True,
                        }
                    ],
                    'bench': [
                        {
                            'db_match': 'Guillermo Ochoa',
                            'flashscore_name': 'Ochoa G.',
                            'number': '13',
                            'db_position': 'Portero',
                            'rating': '6.9',
                            'substitution_minute': "70'",
                            'substitution_player': 'Rangel R.',
                            'substitution_player_number': '1',
                            'substitution_kind': 'in',
                            'matched': True,
                        }
                    ],
                    'coach': {},
                }
            }
        }
        statistics = {
            'status': 200,
            'event_id': 'abc123',
            'periods': [
                {
                    'name': 'Partido',
                    'groups': [
                        {
                            'name': 'Estadísticas principales',
                            'stats': [
                                {'label': 'Posesión', 'home': '55%', 'away': '45%'},
                            ],
                        }
                    ],
                }
            ],
        }
        summary = {
            'status': 200,
            'event_id': 'abc123',
            'periods': [
                {
                    'name': '1er Tiempo',
                    'score': {'home': '1', 'away': '0'},
                    'events': [
                        {'minute': "9'", 'type': 'Asistencia', 'player': 'Lira E.', 'team': 'Mexico'},
                    ],
                }
            ],
        }
        report = {
            'status': 200,
            'event_id': 'abc123',
            'title': 'Mexico gana en el debut',
            'credit': 'Flashscore Noticias',
            'paragraphs': ['Mexico fue superior de principio a fin.'],
        }

        with patch('core.views.find_flashscore_match_for_partido', return_value=scraped_match):
            with patch('core.views.build_flashscore_lineups_report', return_value=lineups):
                with patch('core.views.build_flashscore_statistics_report', return_value=statistics):
                    with patch('core.views.build_flashscore_summary_report', return_value=summary):
                        with patch('core.views.build_flashscore_report', return_value=report):
                            response = self.client.get(f'/api/partidos/{partido.id}/seguimiento/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['scraper']['found'])
        self.assertEqual(data['scraper']['event_id'], 'abc123')
        self.assertEqual(data['marcador'], '2 - 0')
        self.assertTrue(data['scraper']['lineups_available'])
        self.assertTrue(data['scraper']['statistics_available'])
        self.assertTrue(data['scraper']['summary_available'])
        self.assertTrue(data['scraper']['report_available'])
        self.assertEqual(data['scraper']['report']['title'], 'Mexico gana en el debut')
        self.assertEqual(data['scraper']['summary']['periods'][0]['events'][0]['player'], 'Lira E.')
        self.assertEqual(data['scraper']['statistics']['periods'][0]['groups'][0]['stats'][0]['label'], 'Posesión')
        self.assertEqual(
            data['scraper']['lineups']['Mexico']['starters'][0]['name'],
            'Raul Rangel',
        )
        self.assertEqual(
            data['scraper']['lineups']['Mexico']['starters'][0]['substitution_player_number'],
            '13',
        )
        self.assertEqual(data['scraper']['lineups']['Mexico']['bench'][0]['name'], 'Guillermo Ochoa')
        self.assertEqual(data['scraper']['lineups']['Mexico']['bench'][0]['substitution_kind'], 'in')

    def test_api_partido_seguimiento_oculta_error_de_conexion_scraper(self):
        from unittest.mock import patch

        partido = Partido.objects.get(numero=15)

        with patch('core.views.find_flashscore_match_for_partido', side_effect=ConnectionError('detalle interno')):
            response = self.client.get(f'/api/partidos/{partido.id}/seguimiento/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['scraper']['available'])
        self.assertFalse(data['scraper']['found'])
        self.assertEqual(data['scraper']['status'], 'sin_conexion')
        self.assertIn('No se pudo conectar con Flashscore', data['scraper']['message'])
        self.assertNotIn('detalle interno', data['scraper']['message'])

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
        self.assertEqual(partido.estado_api, 'IN_PLAY')
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
        self.assertEqual(partido.estado_api, 'FINISHED')
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

    def test_scraper_construye_url_desde_variable_de_entorno(self):
        from django.test import override_settings

        from core.site_scraper import build_scrape_url

        with override_settings(SCRAPER_BASE_URL='https://example.com/mundial/'):
            self.assertEqual(
                build_scrape_url('/partidos/1'),
                'https://example.com/mundial/partidos/1',
            )

        with override_settings(SCRAPER_BASE_URL='https://example.com/partido/demo?mid=abc'):
            self.assertEqual(
                build_scrape_url(''),
                'https://example.com/partido/demo?mid=abc',
            )

    def test_scraper_parsea_metadata_basica(self):
        from unittest.mock import patch

        from django.test import override_settings

        from core.site_scraper import scrape_page

        html = (
            '<html><head><title>Partido demo</title>'
            '<meta name="description" content="Resumen del partido"></head>'
            '<body><h1>Argentina vs Algeria</h1><a href="/lineups">Formaciones</a></body></html>'
        )

        with override_settings(SCRAPER_BASE_URL='https://example.com/'):
            with patch('core.site_scraper.fetch_html', return_value=(200, html)):
                page = scrape_page('/partidos/19')

        self.assertEqual(page.url, 'https://example.com/partidos/19')
        self.assertEqual(page.status, 200)
        self.assertEqual(page.title, 'Partido demo')
        self.assertEqual(page.description, 'Resumen del partido')
        self.assertEqual(page.h1, ['Argentina vs Algeria'])
        self.assertEqual(page.links[0]['href'], 'https://example.com/lineups')
        self.assertEqual(page.links[0]['text'], 'Formaciones')

    def test_scraper_extrae_meta_de_flashscore(self):
        from unittest.mock import patch

        from django.test import override_settings

        from core.site_scraper import scrape_page

        html = (
            '<html><head>'
            '<meta property="og:title" content="España - Cabo Verde 0-0">'
            '<meta property="og:description" content="MUNDIAL: Campeonato del Mundo - Jornada 1">'
            '</head><body><script>window.environment = {"event_id_c":"Iiqjm5Pq"}</script></body></html>'
        )

        with override_settings(SCRAPER_BASE_URL='https://example.com/'):
            with patch('core.site_scraper.fetch_html', return_value=(200, html)):
                page = scrape_page('/partido')

        self.assertEqual(page.event_id, 'Iiqjm5Pq')
        self.assertEqual(page.match['home'], 'España')
        self.assertEqual(page.match['away'], 'Cabo Verde')
        self.assertEqual(page.match['score'], '0-0')
        self.assertEqual(page.match['competition'], 'MUNDIAL')
        self.assertEqual(page.match['round'], 'Campeonato del Mundo - Jornada 1')

    def test_scraper_parsea_feed_de_formaciones_flashscore(self):
        from core.site_scraper import parse_flashscore_feed

        rows = parse_flashscore_feed('LD÷1-4-3-3¬LI÷Cubarsí P.¬LJ÷22¬LQ÷España¬LL÷3¬~')

        self.assertEqual(rows[0]['LD'], '1-4-3-3')
        self.assertEqual(rows[0]['LI'], 'Cubarsí P.')
        self.assertEqual(rows[0]['LJ'], '22')

    def test_scraper_asigna_entrenador_a_equipo_y_no_a_nacionalidad(self):
        from unittest.mock import patch

        from core.site_scraper import build_flashscore_lineups_report, summarize_lineups_for_tracking

        rows = [
            {'LC': '1'},
            {'LQ': 'Argentina', 'LD': '1-4-4-2', 'LI': 'Messi L.', 'LJ': '10', 'LL': '10'},
            {'LC': '2'},
            {'LQ': 'Argelia', 'LD': '1-4-3-3', 'LI': 'Mandi A.', 'LJ': '2', 'LL': '3'},
            {'LC': '1'},
            {'LQ': 'Argentina', 'LD': '1-4-4-2', 'LI': 'Scaloni L.', 'LJ': ''},
            {'LC': '2'},
            {'LQ': 'Suiza', 'LD': '1-4-3-3', 'LI': 'Petkovic V.', 'LJ': ''},
        ]

        with patch('core.site_scraper.fetch_flashscore_lineups', return_value=(200, rows)):
            report = build_flashscore_lineups_report('UP9bEsOr', 'https://example.com/partido')

        summarized = summarize_lineups_for_tracking(report)

        self.assertIn('Argentina', summarized)
        self.assertIn('Argelia', summarized)
        self.assertNotIn('Suiza', summarized)
        self.assertIn('Petkovi', summarized['Argelia']['coach']['name'])
        self.assertEqual(summarized['Argelia']['coach']['flashscore_name'], 'Petkovic V.')
        self.assertEqual(summarized['Argelia']['coach']['nationality'], 'Suiza')

    def test_scraper_ordena_formaciones_por_posicion_de_base(self):
        from core.site_scraper import summarize_lineups_for_tracking

        report = {
            'teams': {
                'Argentina': {
                    'formation': '1-4-4-2',
                    'starters': [
                        {'db_match': 'Lionel Messi', 'number': '10', 'db_position': 'Delantero'},
                        {'db_match': 'Cristian Romero', 'number': '13', 'db_position': 'Defensa'},
                        {'db_match': 'Emiliano Martinez', 'number': '23', 'db_position': 'Portero'},
                        {'db_match': 'Enzo Fernandez', 'number': '24', 'db_position': 'Mediocentro'},
                    ],
                    'bench': [
                        {'db_match': 'Julian Alvarez', 'number': '9', 'db_position': 'Delantero'},
                        {'db_match': 'Nicolas Otamendi', 'number': '19', 'db_position': 'Defensa'},
                    ],
                    'coach': {},
                }
            }
        }

        summarized = summarize_lineups_for_tracking(report)

        self.assertEqual(
            [player['name'] for player in summarized['Argentina']['starters']],
            ['Emiliano Martinez', 'Cristian Romero', 'Enzo Fernandez', 'Lionel Messi'],
        )
        self.assertEqual(
            [player['name'] for player in summarized['Argentina']['bench']],
            ['Nicolas Otamendi', 'Julian Alvarez'],
        )

    def test_scraper_parsea_estadisticas_flashscore(self):
        from core.site_scraper import parse_flashscore_statistics_rows

        rows = [
            {'SE': 'Partido'},
            {'SF': 'Estadísticas principales'},
            {'SD': '12', 'SG': 'Posesión', 'SH': '61%', 'SI': '39%'},
            {'SD': '34', 'SG': 'Remates totales', 'SH': '15', 'SI': '7'},
        ]

        report = parse_flashscore_statistics_rows(rows)

        self.assertEqual(report['periods'][0]['name'], 'Partido')
        self.assertEqual(report['periods'][0]['groups'][0]['name'], 'Estadísticas principales')
        self.assertEqual(report['periods'][0]['groups'][0]['stats'][0]['label'], 'Posesión')
        self.assertEqual(report['periods'][0]['groups'][0]['stats'][0]['home'], '61%')
        self.assertEqual(report['periods'][0]['groups'][0]['stats'][0]['away'], '39%')

    def test_scraper_parsea_resumen_flashscore(self):
        from core.site_scraper import parse_flashscore_summary_rows

        rows = [
            {'AC': '1er Tiempo', 'IG': '1', 'IH': '0'},
            {
                'III': 'GlbPo4ec',
                'IA': '1',
                'IB': "9'",
                'IE': '8',
                'INX': '1',
                'IOX': '0',
                'IF': 'Lira E.',
                'ICT': '',
                'IK': 'Asistencia',
                'IM': '2V4B2zM9',
            },
            {
                'III': 'card-yellow',
                'IA': '2',
                'IB': "31'",
                'IE': '1',
                'IF': 'Mokoena T.',
                'ICT': '',
                'IK': 'Tarjeta amarilla',
            },
            {
                'III': 'sub-one',
                'IA': '1',
                'IB': "70'",
                'IE': '7',
                'IF': 'Pineda O.',
                'ICT': 'Entra por Lira E.',
                'IK': 'Sustitucion - Entra',
            },
        ]
        commentary_rows = [
            {
                'MB': "9'",
                'MC': 'soccer-ball',
                'MD': 'Lira E. recibe un pase y define abajo para el 1:0.',
            }
        ]

        report = parse_flashscore_summary_rows(
            rows,
            home_team='Mexico',
            away_team='South Africa',
            commentary_rows=commentary_rows,
        )

        event = report['periods'][0]['events'][0]
        self.assertEqual(report['periods'][0]['name'], '1er Tiempo')
        self.assertEqual(report['periods'][0]['score']['home'], '1')
        self.assertEqual(event['team_side'], 'home')
        self.assertEqual(event['team'], 'Mexico')
        self.assertEqual(event['minute'], "9'")
        self.assertEqual(event['type'], 'Asistencia')
        self.assertEqual(event['display_type'], 'Gol')
        self.assertEqual(event['category'], 'goal')
        self.assertEqual(event['assist_player'], 'Lira E.')
        self.assertEqual(event['description'], 'Lira E. recibe un pase y define abajo para el 1:0.')
        self.assertEqual(event['score']['home'], '1')
        self.assertEqual(report['periods'][0]['events'][1]['category'], 'card')
        self.assertEqual(report['periods'][0]['events'][1]['card_color'], 'yellow')
        self.assertEqual(report['periods'][0]['events'][2]['category'], 'substitution')

    def test_scraper_parsea_informe_flashscore(self):
        from core.site_scraper import parse_flashscore_report_content

        content = (
            '[p][b]Argentina supero a [a href="/jugador/messi"]Lionel Messi[/a].[/b][/p]'
            '[p]El segundo tiempo tuvo control de la Albiceleste.[/p]'
        )

        self.assertEqual(
            parse_flashscore_report_content(content),
            [
                'Argentina supero a Lionel Messi.',
                'El segundo tiempo tuvo control de la Albiceleste.',
            ],
        )

    def test_scraper_extrae_feed_inicial_de_flashscore(self):
        from core.site_scraper import extract_flashscore_initial_feed

        html = '''
            <script>
                cjs.initialFeeds["fixtures"] = {
                    data: `SA÷1¬~ZA÷MUNDIAL: Campeonato del Mundo¬~AA÷8nrACRTs¬AD÷1781798400¬AB÷1¬AE÷República Checa¬AF÷Sudáfrica¬WU÷republica-checa¬WV÷sudafrica¬PX÷6LHwBDGU¬PY÷W2ijYvlr¬~`,
                    allEventsCount: 80,
                    seasonId: 2026
                };
            </script>
        '''

        feed = extract_flashscore_initial_feed(html, 'fixtures')

        self.assertEqual(feed['all_events_count'], 80)
        self.assertEqual(feed['season_id'], 2026)
        self.assertEqual(feed['rows'][2]['AA'], '8nrACRTs')
        self.assertEqual(feed['rows'][2]['AE'], 'República Checa')

    def test_scraper_extrae_links_del_mundial_desde_feed(self):
        from core.site_scraper import extract_flashscore_competition_matches

        rows = [
            {'ZA': 'MUNDIAL: Campeonato del Mundo', 'ZL': '/futbol/mundial/campeonato-del-mundo/'},
            {
                'AA': 'ALxYcMw2',
                'AB': '1',
                'AD': '1781636400',
                'AE': 'Francia',
                'AF': 'Senegal',
                'WU': 'francia',
                'WV': 'senegal',
                'PX': 'QkGeVG1n',
                'PY': 'hOIsJLJr',
            },
            {'ZA': 'MUNDIAL: Amistosos de Clubs'},
            {'AA': 'IRpyFfSF', 'AE': 'Pari NN', 'AF': 'Ufa'},
        ]

        matches = extract_flashscore_competition_matches(rows)

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['home'], 'Francia')
        self.assertEqual(matches[0]['away'], 'Senegal')
        self.assertEqual(matches[0]['status'], 'programado')
        self.assertEqual(
            matches[0]['url'],
            'https://www.flashscore.com.ar/partido/futbol/francia-QkGeVG1n/senegal-hOIsJLJr/?mid=ALxYcMw2',
        )

    def test_scraper_usa_base_url_para_partidos_del_mundial(self):
        from unittest.mock import patch

        from django.test import override_settings

        from core.site_scraper import fetch_flashscore_worldcup_matches

        html = '''
            <script>
                cjs.initialFeeds["fixtures"] = {
                    data: `SA÷1¬~ZA÷MUNDIAL: Campeonato del Mundo¬~AA÷8nrACRTs¬AD÷1781798400¬AB÷1¬AE÷República Checa¬AF÷Sudáfrica¬WU÷republica-checa¬WV÷sudafrica¬PX÷6LHwBDGU¬PY÷W2ijYvlr¬~`,
                    allEventsCount: 80,
                    seasonId: 2026
                };
            </script>
        '''

        with override_settings(SCRAPER_BASE_URL='https://www.flashscore.com.ar/futbol/mundial/campeonato-del-mundo/partidos/'):
            with patch('core.site_scraper.fetch_html', return_value=(200, html)):
                report = fetch_flashscore_worldcup_matches()

        self.assertEqual(report['source'], 'page')
        self.assertEqual(report['block'], 'fixtures')
        self.assertEqual(report['all_events_count'], 80)
        self.assertEqual(len(report['matches']), 1)
        self.assertEqual(report['matches'][0]['home'], 'República Checa')
        self.assertEqual(report['matches'][0]['away'], 'Sudáfrica')

    def test_scraper_empareja_partido_viejo_con_nombres_en_espanol(self):
        from core.site_scraper import flashscore_match_for_partido_in_matches

        partido = Partido.objects.get(numero=2)
        match = flashscore_match_for_partido_in_matches(
            partido,
            [
                {
                    'home': 'Corea del Sur',
                    'away': 'República Checa',
                    'event_id': 'CGdvIm6K',
                }
            ],
        )

        self.assertIsNotNone(match)
        self.assertEqual(match['event_id'], 'CGdvIm6K')

# Create your tests here.
