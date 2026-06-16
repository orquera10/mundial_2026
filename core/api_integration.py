import json
import unicodedata
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from core.models import Partido


SPORTMONKS_LIVE_URL = 'https://worldcup.sportmonksapi.com/api/v2.0/live-scores'
FOOTBALL_DATA_MATCHES_URL = 'https://api.football-data.org/v4/matches'

TEAM_ALIASES = {
    'bosnia herzegovina': 'bosnia and herzegovina',
    'cape verde islands': 'cabo verde',
    'ivory coast': "cote d'ivoire",
    'iran': 'ir iran',
    'south korea': 'korea republic',
    'turkey': 'turkiye',
    'united states': 'usa',
}


def fetch_json(url, headers=None, params=None):
    if params:
        url = f'{url}?{urlencode(params)}'
    request = Request(url, headers=headers or {'Accept': 'application/json'})
    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            return {}
        return json.loads(response.read().decode('utf-8'))


def fetch_worldcup_matches():
    try:
        data = fetch_json(SPORTMONKS_LIVE_URL)
    except Exception:
        return []
    return data.get('data', [])


def fetch_from_football_data(date_from=None, date_to=None):
    api_key = getattr(settings, 'FOOTBALL_DATA_API_KEY', '')
    if not api_key:
        return []

    date_from = date_from or getattr(settings, 'FOOTBALL_DATA_DATE_FROM', '')
    date_to = date_to or getattr(settings, 'FOOTBALL_DATA_DATE_TO', '')
    if not date_from or not date_to:
        today = timezone.localdate()
        date_from = date_from or today.isoformat()
        date_to = date_to or (today + timedelta(days=7)).isoformat()

    try:
        data = fetch_json(
            FOOTBALL_DATA_MATCHES_URL,
            headers={'Accept': 'application/json', 'X-Auth-Token': api_key},
            params={'competitions': 'WC', 'dateFrom': date_from, 'dateTo': date_to},
        )
    except Exception:
        return []
    return data.get('matches', [])


def fetch_football_data_range(date_from, date_to, chunk_days=8):
    current = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    matches = []

    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        matches.extend(fetch_from_football_data(current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)

    return matches


def first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def match_number(match):
    return first_present(match.get('number'), match.get('matchNumber'), match.get('match_number'))


def normalize_name(value):
    value = value or ''
    value = unicodedata.normalize('NFKD', value)
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = value.lower().replace('&', 'and').replace('.', '').replace('-', ' ').strip()
    value = ' '.join(value.split())
    return TEAM_ALIASES.get(value, value)


def team_name(match, side):
    team = match.get(f'{side}Team') or {}
    return first_present(team.get('name'), team.get('shortName'), match.get(f'{side}_team'))


def team_crest(match, side):
    team = match.get(f'{side}Team') or {}
    return team.get('crest') or ''


def same_match(partido, match):
    numero = match_number(match)
    if numero == partido.numero:
        return True

    home = normalize_name(team_name(match, 'home'))
    away = normalize_name(team_name(match, 'away'))
    local = normalize_name(partido.local_nombre)
    visitante = normalize_name(partido.visitante_nombre)
    return home == local and away == visitante


def extract_score(match):
    score = match.get('score') or {}
    full_time = score.get('fullTime') or {}
    goals = match.get('goals') or {}
    home_score = match.get('homeScore') or {}
    away_score = match.get('awayScore') or {}

    goles_local = first_present(
        full_time.get('home'),
        goals.get('home'),
        home_score.get('current'),
        match.get('home_score'),
    )
    goles_visitante = first_present(
        full_time.get('away'),
        goals.get('away'),
        away_score.get('current'),
        match.get('away_score'),
    )
    return goles_local, goles_visitante


def extract_utc_datetime(match):
    value = match.get('utcDate')
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def parse_api_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def main_referee(match):
    referees = match.get('referees') or []
    if not referees:
        return None
    referee = next((item for item in referees if item.get('type') == 'REFEREE'), referees[0])
    return referee


def normalize_estado(match):
    estado_raw = str(match.get('status') or match.get('state') or '').upper()
    if any(token in estado_raw for token in ('LIVE', 'IN_PLAY', 'PAUSED', 'HALF_TIME')):
        return Partido.ESTADO_EN_VIVO
    if any(token in estado_raw for token in ('FINISHED', 'FT', 'ENDED')):
        return Partido.ESTADO_FINALIZADO
    if any(token in estado_raw for token in ('SCHEDULED', 'TIMED')):
        return Partido.ESTADO_PROGRAMADO
    return None


def sync_match_result(partido, matches=None):
    matches = matches if matches is not None else (fetch_worldcup_matches() or fetch_from_football_data())

    for match in matches:
        if not same_match(partido, match):
            continue

        update_fields = []
        mapping = {
            'football_data_id': match.get('id'),
            'jornada': match.get('matchday'),
            'estado_api': match.get('status') or match.get('state') or '',
            'etapa_api': match.get('stage') or '',
            'grupo_api': match.get('group') or '',
            'escudo_local_url': team_crest(match, 'home'),
            'escudo_visitante_url': team_crest(match, 'away'),
        }
        referee = main_referee(match)
        if referee:
            mapping['arbitro'] = referee.get('name') or ''
            mapping['arbitro_nacionalidad'] = referee.get('nationality') or ''

        last_updated = parse_api_datetime(match.get('lastUpdated'))
        if last_updated:
            mapping['evento_actualizado'] = last_updated

        for field, value in mapping.items():
            if value is not None and getattr(partido, field) != value:
                setattr(partido, field, value)
                update_fields.append(field)

        estado = normalize_estado(match)
        if estado and partido.estado != estado:
            partido.estado = estado
            update_fields.append('estado')

        goles_local, goles_visitante = extract_score(match)
        if goles_local is not None and goles_visitante is not None:
            partido.goles_local = int(goles_local)
            partido.goles_visitante = int(goles_visitante)
            update_fields.extend(['goles_local', 'goles_visitante'])

        inicio_utc = extract_utc_datetime(match)
        if inicio_utc:
            inicio_sede = inicio_utc.astimezone(ZoneInfo(partido.zona_horaria_sede))
            if partido.fecha != inicio_sede.date():
                partido.fecha = inicio_sede.date()
                update_fields.append('fecha')
            if partido.hora != inicio_sede.time().replace(tzinfo=None):
                partido.hora = inicio_sede.time().replace(tzinfo=None)
                update_fields.append('hora')

        if update_fields:
            partido.save(update_fields=sorted(set(update_fields)))
            return True
        return False

    return False


def sync_matches_results(matches=None, date_from=None, date_to=None):
    if matches is None and date_from and date_to:
        matches = fetch_football_data_range(date_from, date_to)
    matches = matches if matches is not None else (fetch_worldcup_matches() or fetch_from_football_data())
    actualizados = 0
    for partido in Partido.objects.all():
        if sync_match_result(partido, matches):
            actualizados += 1
    return actualizados


def partidos_listos_para_sincronizar(now=None, follow_hours=12):
    now = now or timezone.localtime(timezone.now())
    inicio_ventana = now - timedelta(hours=follow_hours)
    partidos = []

    for partido in Partido.objects.exclude(estado=Partido.ESTADO_FINALIZADO):
        inicio = partido.inicio_argentina
        if inicio and inicio_ventana <= inicio <= now:
            partidos.append(partido)

    return partidos


def sync_due_matches_results(now=None, follow_hours=12):
    partidos = partidos_listos_para_sincronizar(
        now=now,
        follow_hours=follow_hours,
    )
    if not partidos:
        return {'consultados': 0, 'actualizados': 0, 'mensaje': 'Sin partidos listos para consultar.'}

    fechas = [
        partido.inicio_argentina.astimezone(ZoneInfo('UTC')).date()
        for partido in partidos
        if partido.inicio_argentina
    ]
    date_from = (min(fechas) - timedelta(days=1)).isoformat()
    date_to = (max(fechas) + timedelta(days=1)).isoformat()
    matches = fetch_football_data_range(date_from, date_to)

    actualizados = 0
    for partido in partidos:
        if sync_match_result(partido, matches):
            actualizados += 1

    return {
        'consultados': len(partidos),
        'actualizados': actualizados,
        'date_from': date_from,
        'date_to': date_to,
    }
