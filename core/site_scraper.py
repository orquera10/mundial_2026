from dataclasses import dataclass, field
from html.parser import HTMLParser
from html import unescape
import json
import re
import unicodedata
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from core.models import Equipo, JugadorSeleccion


class ScraperConfigError(ValueError):
    pass


@dataclass
class ScrapedPage:
    url: str
    status: int
    title: str = ''
    description: str = ''
    meta: dict = field(default_factory=dict)
    match: dict = field(default_factory=dict)
    event_id: str = ''
    h1: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    html: str = ''

    def as_dict(self, include_html=False):
        data = {
            'url': self.url,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'meta': self.meta,
            'match': self.match,
            'event_id': self.event_id,
            'h1': self.h1,
            'links': self.links,
        }
        if include_html:
            data['html'] = self.html
        return data


class BasicPageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ''
        self.description = ''
        self.meta = {}
        self.h1 = []
        self.links = []
        self._current_tag = None
        self._buffer = []
        self._current_link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {'title', 'h1', 'a'}:
            self._current_tag = tag
            self._buffer = []

        if tag == 'meta':
            name = (attrs.get('name') or attrs.get('property') or '').lower()
            content = attrs.get('content', '').strip()
            if name and content:
                self.meta[name] = content
            if name in {'description', 'og:description'} and content:
                self.description = self.description or content

        if tag == 'a':
            href = attrs.get('href', '').strip()
            self._current_link = {
                'href': urljoin(self.base_url, href) if href else '',
                'text': '',
            }

    def handle_data(self, data):
        if self._current_tag:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag != self._current_tag:
            return

        text = ' '.join(''.join(self._buffer).split())
        if tag == 'title':
            self.title = self.title or text
        elif tag == 'h1' and text:
            self.h1.append(text)
        elif tag == 'a' and self._current_link:
            self._current_link['text'] = text
            if self._current_link['href']:
                self.links.append(self._current_link)

        self._current_tag = None
        self._buffer = []
        self._current_link = None


def build_scrape_url(path_or_url=''):
    base_url = getattr(settings, 'SCRAPER_BASE_URL', '').strip()
    candidate = (path_or_url or '').strip()

    if candidate.startswith(('http://', 'https://')):
        url = candidate
    else:
        if not base_url:
            raise ScraperConfigError('Configura SCRAPER_BASE_URL antes de usar el scraper.')
        if not candidate:
            url = base_url
        else:
            url = urljoin(base_url.rstrip('/') + '/', candidate.lstrip('/'))

    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ScraperConfigError(f'URL invalida para scraping: {url}')

    return url


def fetch_html(url):
    request = Request(
        url,
        headers={
            'Accept': 'text/html,application/xhtml+xml',
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
        },
    )
    timeout = getattr(settings, 'SCRAPER_TIMEOUT_SECONDS', 15)
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        html = response.read().decode(charset, errors='replace')
        return response.status, html


def fetch_text(url, headers=None):
    request = Request(url, headers=headers or {})
    timeout = getattr(settings, 'SCRAPER_TIMEOUT_SECONDS', 15)
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return response.status, response.read().decode(charset, errors='replace')


def extract_event_id(html):
    match = re.search(r'"event_id_c"\s*:\s*"([^"]+)"', html)
    return match.group(1) if match else ''


def parse_match_meta(meta):
    og_title = meta.get('og:title', '')
    og_description = meta.get('og:description', '')
    match = {
        'competition': '',
        'round': '',
        'home': '',
        'away': '',
        'score': '',
    }

    if ':' in og_description:
        competition, round_name = og_description.split(':', 1)
        match['competition'] = competition.strip()
        match['round'] = round_name.strip()

    parsed_title = re.match(r'(.+?)\s+-\s+(.+?)\s+(\d+)-(\d+)$', og_title)
    if parsed_title:
        match['home'] = parsed_title.group(1).strip()
        match['away'] = parsed_title.group(2).strip()
        match['score'] = f'{parsed_title.group(3)}-{parsed_title.group(4)}'

    return {key: value for key, value in match.items() if value}


def parse_flashscore_feed(feed_text):
    rows = []
    for raw_row in feed_text.split('¬~'):
        row = {}
        for part in raw_row.split('¬'):
            if '÷' not in part:
                continue
            key, value = part.split('÷', 1)
            row[key] = value
        if row:
            rows.append(row)
    return rows


def parse_flashscore_feed(feed_text):
    feed_text = (feed_text or '').replace('Ź', '¬').replace('Ã·', '÷').replace('Â¬', '¬')
    rows = []
    for raw_row in feed_text.split('¬~'):
        row = {}
        for part in raw_row.split('¬'):
            if '÷' not in part:
                continue
            key, value = part.split('÷', 1)
            row[key] = value
        if row:
            rows.append(row)
    return rows


def extract_flashscore_initial_feed(html, block_name='fixtures'):
    pattern = (
        r'cjs\.initialFeeds\["'
        + re.escape(block_name)
        + r'"\]\s*=\s*\{\s*data:\s*`(?P<data>.*?)`\s*,?(?P<meta>.*?)\};'
    )
    match = re.search(pattern, html or '', flags=re.DOTALL)
    if not match:
        return {'data': '', 'rows': [], 'all_events_count': 0, 'season_id': 0}

    meta = match.group('meta') or ''
    all_events_match = re.search(r'allEventsCount:\s*(\d+)', meta)
    season_match = re.search(r'seasonId:\s*(\d+)', meta)
    return {
        'data': match.group('data'),
        'rows': parse_flashscore_feed(match.group('data')),
        'all_events_count': int(all_events_match.group(1)) if all_events_match else 0,
        'season_id': int(season_match.group(1)) if season_match else 0,
    }


def fetch_flashscore_lineups(event_id, referer_url):
    endpoint = f'https://www.flashscore.com.ar/x/feed/df_li_1_{event_id}'
    status, feed = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, parse_flashscore_feed(feed)


def fetch_flashscore_statistics(event_id, referer_url):
    endpoint = f'https://www.flashscore.com.ar/x/feed/df_st_1_{event_id}'
    status, feed = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, parse_flashscore_feed(feed)


def fetch_flashscore_report(event_id, referer_url):
    endpoint = f'https://www.flashscore.com.ar/x/feed/df_rr_{event_id}/'
    status, body = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, json.loads(body or '{}')


def fetch_flashscore_summary(event_id, referer_url):
    endpoint = f'https://www.flashscore.com.ar/x/feed/df_sui_1_{event_id}'
    status, feed = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, parse_flashscore_feed(feed)


def fetch_flashscore_live_commentary(event_id, referer_url):
    endpoint = f'https://www.flashscore.com.ar/x/feed/df_lc_1_{event_id}'
    status, feed = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, parse_flashscore_feed(feed)


def fetch_flashscore_feed(feed_name, referer_url='https://www.flashscore.com.ar/'):
    endpoint = f'https://www.flashscore.com.ar/x/feed/{feed_name}'
    status, feed = fetch_text(
        endpoint,
        headers={
            'Accept': '*/*',
            'Referer': referer_url,
            'User-Agent': getattr(settings, 'SCRAPER_USER_AGENT', ''),
            'x-fsign': getattr(settings, 'SCRAPER_FLASHSCORE_FSIGN', 'SW9D1eZo'),
        },
    )
    return status, parse_flashscore_feed(feed)


def flashscore_team_name(value):
    aliases = {
        'Alemania': 'Germany',
        'Arabia Saudí': 'Saudi Arabia',
        'Argelia': 'Algeria',
        'Bélgica': 'Belgium',
        'Bosnia-Herzegovina': 'Bosnia and Herzegovina',
        'Brasil': 'Brazil',
        'Cabo Verde': 'Cabo Verde',
        'Canadá': 'Canada',
        'Catar': 'Qatar',
        'Corea del Sur': 'Korea Republic',
        'Costa de Marfil': "Cote d'Ivoire",
        'Croacia': 'Croatia',
        'Curazao': 'Curacao',
        'EE. UU.': 'USA',
        'Egipto': 'Egypt',
        'Escocia': 'Scotland',
        'España': 'Spain',
        'Estados Unidos': 'USA',
        'Haití': 'Haiti',
        'Inglaterra': 'England',
        'Irán': 'IR Iran',
        'Irak': 'Iraq',
        'Japón': 'Japan',
        'Jordania': 'Jordan',
        'Marruecos': 'Morocco',
        'México': 'Mexico',
        'Francia': 'France',
        'Nueva Zelanda': 'New Zealand',
        'Noruega': 'Norway',
        'Países Bajos': 'Netherlands',
        'Panamá': 'Panama',
        'RD Congo': 'Congo DR',
        'República Checa': 'Czechia',
        'Senegal': 'Senegal',
        'Sudáfrica': 'South Africa',
        'Suecia': 'Sweden',
        'Suiza': 'Switzerland',
        'Túnez': 'Tunisia',
        'Turquía': 'Turkiye',
        'Uruguay': 'Uruguay',
        'Uzbekistán': 'Uzbekistan',
    }
    return aliases.get(value, value)


def normalize_scraper_name(value):
    value = unicodedata.normalize('NFKD', value or '')
    value = ''.join(char for char in value if not unicodedata.combining(char))
    value = value.lower().replace('&', 'and').replace('.', '').replace('-', ' ')
    value = re.sub(r'[^a-z0-9 ]+', ' ', value)
    return ' '.join(value.split())


def roster_match_by_team_and_number(team_name, number):
    if not number or not str(number).isdigit():
        return None
    return (
        JugadorSeleccion.objects.select_related('equipo')
        .filter(equipo__nombre=team_name, orden=int(number))
        .first()
    )


def team_coach_name(team_name):
    equipo = Equipo.objects.filter(nombre=team_name).first()
    if not equipo:
        return ''
    return f'{equipo.tecnico_nombres} {equipo.tecnico_apellidos}'.strip()


def flashscore_match_status(row):
    code = row.get('AB') or row.get('AC') or ''
    if code == '1':
        return 'programado'
    if code == '2':
        return 'en_vivo'
    if code == '3':
        return 'finalizado'
    return code or 'desconocido'


def flashscore_match_url(row):
    event_id = row.get('AA', '')
    home_slug = row.get('WU', '')
    home_id = row.get('PX', '')
    away_slug = row.get('WV', '')
    away_id = row.get('PY', '')
    if not all([event_id, home_slug, home_id, away_slug, away_id]):
        return ''
    return (
        'https://www.flashscore.com.ar/partido/futbol/'
        f'{home_slug}-{home_id}/{away_slug}-{away_id}/?mid={event_id}'
    )


def extract_flashscore_competition_matches(rows, competition_title='MUNDIAL: Campeonato del Mundo'):
    matches = []
    in_competition = False
    competition = {}

    for row in rows:
        if row.get('ZA'):
            in_competition = row.get('ZA') == competition_title
            competition = row if in_competition else {}
            continue

        if not in_competition or not row.get('AA'):
            continue

        home = row.get('AE') or row.get('CX') or ''
        away = row.get('AF') or ''
        matches.append(
            {
                'event_id': row.get('AA', ''),
                'competition': competition.get('ZA', competition_title),
                'home': home,
                'away': away,
                'timestamp': row.get('AD', ''),
                'status': flashscore_match_status(row),
                'score': {
                    'home': row.get('AG', ''),
                    'away': row.get('AH', ''),
                    'home_half_time': row.get('AT', ''),
                    'away_half_time': row.get('AU', ''),
                },
                'home_slug': row.get('WU', ''),
                'away_slug': row.get('WV', ''),
                'url': flashscore_match_url(row),
                'has_audio': bool(row.get('QQ')),
            }
        )

    return matches


def fetch_flashscore_worldcup_matches(feed_name=None, source_url=None, block_name=None):
    if source_url is None:
        source_url = getattr(settings, 'SCRAPER_BASE_URL', '')
    source_url = source_url.strip()
    block_names = [block_name] if block_name else ['fixtures', 'summary-fixtures']

    if source_url:
        url = build_scrape_url(source_url)
        status, html = fetch_html(url)
        for current_block in block_names:
            initial_feed = extract_flashscore_initial_feed(html, current_block)
            if initial_feed['rows']:
                return {
                    'status': status,
                    'source': 'page',
                    'url': url,
                    'block': current_block,
                    'all_events_count': initial_feed['all_events_count'],
                    'season_id': initial_feed['season_id'],
                    'matches': extract_flashscore_competition_matches(initial_feed['rows']),
                }

    feed_name = feed_name or getattr(settings, 'SCRAPER_FLASHSCORE_TODAY_FEED', 'f_1_0_2_es-ar_1')
    status, rows = fetch_flashscore_feed(feed_name, referer_url=source_url or 'https://www.flashscore.com.ar/')
    return {
        'status': status,
        'source': 'feed',
        'feed': feed_name,
        'matches': extract_flashscore_competition_matches(rows),
    }


def flashscore_daily_feed_name(day_offset):
    return f'f_1_{day_offset}_2_es-ar_1'


def flashscore_match_for_partido_in_matches(partido, matches):
    local = normalize_scraper_name(partido.local_nombre)
    visitante = normalize_scraper_name(partido.visitante_nombre)

    for match in matches:
        home = normalize_scraper_name(flashscore_team_name(match.get('home', '')))
        away = normalize_scraper_name(flashscore_team_name(match.get('away', '')))
        if home == local and away == visitante:
            return match
        if home == visitante and away == local:
            return match

    return None


def find_flashscore_match_for_partido(partido, feed_name=None):
    report = fetch_flashscore_worldcup_matches(feed_name)
    found = flashscore_match_for_partido_in_matches(partido, report['matches'])
    if found:
        return found

    target_date = partido.fecha_argentina
    day_offset = (target_date - timezone.localdate()).days
    for offset in (day_offset, day_offset + 1, day_offset - 1):
        daily_report = fetch_flashscore_worldcup_matches(
            feed_name=flashscore_daily_feed_name(offset),
            source_url='',
        )
        found = flashscore_match_for_partido_in_matches(partido, daily_report['matches'])
        if found:
            return found

    return None


def summarize_lineups_for_tracking(lineups_report):
    position_order = {
        'Portero': 1,
        'Defensa': 2,
        'Mediocentro': 3,
        'Delantero': 4,
    }

    def format_lineup_minute(value):
        value = str(value or '').strip()
        if value and value[-1].isdigit():
            return f"{value}'"
        return value

    def player_payload(item):
        return {
            'name': item.get('db_match') or item.get('flashscore_name', ''),
            'flashscore_name': item.get('flashscore_name', ''),
            'number': item.get('number', ''),
            'position': item.get('db_position', ''),
            'rating': item.get('rating', ''),
            'substitution_minute': format_lineup_minute(item.get('substitution_minute', '')),
            'substitution_player': item.get('substitution_player', ''),
            'substitution_player_number': item.get('substitution_player_number', ''),
            'substitution_kind': item.get('substitution_kind', ''),
            'matched': item.get('matched', False),
        }

    def player_sort_key(item):
        position = item.get('db_position', '')
        position_code = item.get('position_code', '')
        number = item.get('number', '')
        return (
            position_order.get(position, 9),
            int(position_code) if str(position_code).isdigit() else 99,
            int(number) if str(number).isdigit() else 99,
            item.get('db_match') or item.get('flashscore_name', ''),
        )

    teams = {}
    for flashscore_team, team in lineups_report.get('teams', {}).items():
        coach = team.get('coach') or {}
        starters = sorted(team.get('starters', []), key=player_sort_key)
        bench = sorted(team.get('bench', []), key=player_sort_key)
        teams[flashscore_team] = {
            'db_team': team.get('db_team', ''),
            'formation': team.get('formation', ''),
            'starters': [player_payload(item) for item in starters],
            'bench': [player_payload(item) for item in bench],
            'coach': {
                'name': coach.get('db_coach') or coach.get('flashscore_name', ''),
                'flashscore_name': coach.get('flashscore_name', ''),
                'nationality': coach.get('coach_nationality', ''),
                'matched': bool(coach.get('db_coach')),
            }
            if coach
            else {},
        }
    return teams


def parse_flashscore_statistics_rows(rows):
    report = {'periods': [], 'raw_rows': len(rows)}
    current_period = None
    current_group = None

    for row in rows:
        if row.get('SE'):
            current_period = {
                'name': row.get('SE', ''),
                'groups': [],
            }
            report['periods'].append(current_period)
            current_group = None
            continue

        if row.get('SF'):
            if current_period is None:
                current_period = {'name': 'Partido', 'groups': []}
                report['periods'].append(current_period)
            current_group = {
                'name': row.get('SF', ''),
                'stats': [],
            }
            current_period['groups'].append(current_group)
            continue

        if not row.get('SG'):
            continue

        if current_period is None:
            current_period = {'name': 'Partido', 'groups': []}
            report['periods'].append(current_period)
        if current_group is None:
            current_group = {'name': 'Estadisticas', 'stats': []}
            current_period['groups'].append(current_group)

        current_group['stats'].append(
            {
                'code': row.get('SD', ''),
                'label': row.get('SG', ''),
                'home': row.get('SH', ''),
                'away': row.get('SI', ''),
            }
        )

    return report


def summary_row_value(row, key):
    return row.get(key) or row.get(f'{key}X') or ''


def normalize_summary_minute(value):
    return str(value or '').strip().replace('’', "'")


def summary_event_kind(event_type, type_code, has_score=False):
    value = normalize_scraper_name(event_type)
    if 'sustitucion' in value or type_code == '7':
        return 'substitution', ''
    if 'amarilla' in value or type_code == '1':
        return 'card', 'yellow'
    if 'roja' in value or type_code == '2':
        return 'card', 'red'
    if 'gol anulado' in value:
        return 'goal_cancelled', ''
    if 'gol' in value or type_code == '3' or (has_score and type_code == '8'):
        return 'goal', ''
    return 'event', ''


def parse_flashscore_commentary_rows(rows):
    commentary = []
    for row in rows:
        minute = normalize_summary_minute(row.get('MB'))
        description = row.get('MD', '')
        if not minute and not description:
            continue
        commentary.append(
            {
                'minute': minute,
                'icon': row.get('MC', ''),
                'title': row.get('MK', ''),
                'description': description,
            }
        )
    return commentary


def commentary_by_minute_and_icon(commentary_rows, icon):
    by_minute = {}
    for item in parse_flashscore_commentary_rows(commentary_rows):
        if item.get('icon') != icon or not item.get('description'):
            continue
        by_minute.setdefault(item.get('minute'), []).append(item)
    return by_minute


def parse_flashscore_summary_rows(rows, home_team='', away_team='', commentary_rows=None):
    report = {'periods': [], 'raw_rows': len(rows)}
    current_period = None
    goal_commentary = commentary_by_minute_and_icon(commentary_rows or [], 'soccer-ball')

    for row in rows:
        if row.get('AC'):
            current_period = {
                'name': row.get('AC', ''),
                'score': {
                    'home': row.get('IG', ''),
                    'away': row.get('IH', ''),
                },
                'events': [],
            }
            report['periods'].append(current_period)
            continue

        event_id = summary_row_value(row, 'III')
        event_type = summary_row_value(row, 'IK')
        player = summary_row_value(row, 'IF')
        minute = summary_row_value(row, 'IB')
        if not any([event_id, event_type, player, minute]):
            continue

        if current_period is None:
            current_period = {'name': 'Partido', 'score': {}, 'events': []}
            report['periods'].append(current_period)

        side = summary_row_value(row, 'IA')
        score = {
            'home': summary_row_value(row, 'INX'),
            'away': summary_row_value(row, 'IOX'),
        }
        has_score = score['home'] != '' and score['away'] != ''
        type_code = summary_row_value(row, 'IE')
        category, card_color = summary_event_kind(event_type, type_code, has_score=has_score)
        description = summary_row_value(row, 'ICT')
        assist_player = player if category == 'goal' and normalize_scraper_name(event_type) == 'asistencia' else ''
        if category == 'goal' and not description:
            for commentary in goal_commentary.get(normalize_summary_minute(minute), []):
                description = commentary.get('description', '')
                if description:
                    break

        current_period['events'].append(
            {
                'id': event_id,
                'minute': normalize_summary_minute(minute),
                'team_side': 'home' if side == '1' else 'away' if side == '2' else '',
                'team': home_team if side == '1' else away_team if side == '2' else '',
                'type': event_type,
                'display_type': 'Gol' if category == 'goal' and assist_player else event_type,
                'category': category,
                'card_color': card_color,
                'type_code': type_code,
                'player': player,
                'player_url': urljoin('https://www.flashscore.com.ar/', row.get('IU', '')),
                'description': description,
                'score': score,
                'reason': summary_row_value(row, 'IL'),
                'assist_player': assist_player,
            }
        )

    return report


def parse_flashscore_report_content(content):
    content = content or ''
    paragraphs = re.findall(r'\[p\](.*?)\[/p\]', content, flags=re.DOTALL | re.IGNORECASE)
    if not paragraphs and content.strip():
        paragraphs = [content]

    parsed = []
    for paragraph in paragraphs:
        text = re.sub(r'\[(?:/?(?:b|i|strong|em)|a\b[^\]]*|/a)\]', '', paragraph, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]+\]', '', text)
        text = unescape(' '.join(text.split()))
        if text:
            parsed.append(text)
    return parsed


def build_flashscore_report(event_id, referer_url):
    status, data = fetch_flashscore_report(event_id, referer_url)
    return {
        'status': status,
        'event_id': event_id,
        'title': data.get('title', ''),
        'credit': data.get('credit', ''),
        'published_at': data.get('publishedAt', ''),
        'edited_at': data.get('editedAt', ''),
        'paragraphs': parse_flashscore_report_content(data.get('content', '')),
        'images': data.get('images') or [],
        'raw_id': data.get('id', ''),
    }


def build_flashscore_statistics_report(event_id, referer_url):
    status, rows = fetch_flashscore_statistics(event_id, referer_url)
    report = parse_flashscore_statistics_rows(rows)
    report.update(
        {
            'status': status,
            'event_id': event_id,
        }
    )
    return report


def build_flashscore_summary_report(event_id, referer_url, home_team='', away_team=''):
    status, rows = fetch_flashscore_summary(event_id, referer_url)
    commentary_rows = []
    try:
        _, commentary_rows = fetch_flashscore_live_commentary(event_id, referer_url)
    except Exception:
        commentary_rows = []
    report = parse_flashscore_summary_rows(
        rows,
        home_team=home_team,
        away_team=away_team,
        commentary_rows=commentary_rows,
    )
    report.update(
        {
            'status': status,
            'event_id': event_id,
        }
    )
    return report


def build_flashscore_lineups_report(event_id, referer_url):
    status, rows = fetch_flashscore_lineups(event_id, referer_url)
    report = {
        'status': status,
        'event_id': event_id,
        'teams': {},
        'raw_rows': len(rows),
    }
    current_side = ''
    teams_by_side = {}

    def ensure_team(flashscore_team):
        team_name = flashscore_team_name(flashscore_team)
        return report['teams'].setdefault(
            flashscore_team,
            {
                'db_team': team_name,
                'formation': '',
                'starters': [],
                'bench': [],
                'coach': None,
            },
        )

    for row in rows:
        if row.get('LC') in {'1', '2'}:
            current_side = row['LC']

        player_name = row.get('LI', '')
        if not player_name:
            continue

        number = row.get('LJ', '')
        raw_team = row.get('LQ', '')
        flashscore_team = raw_team
        if not number and current_side in teams_by_side:
            flashscore_team = teams_by_side[current_side]
        if not flashscore_team:
            continue

        if number and current_side:
            teams_by_side[current_side] = flashscore_team

        team = ensure_team(flashscore_team)
        team_name = team.get('db_team', flashscore_team_name(flashscore_team))
        if row.get('LD') and (number or not team.get('formation')):
            team['formation'] = row['LD']

        player = roster_match_by_team_and_number(team_name, number)
        item = {
            'flashscore_name': player_name,
            'number': number,
            'position_code': row.get('LL', ''),
            'rating': row.get('LPR', ''),
            'flashscore_url': row.get('NU', ''),
            'substitution_minute': row.get('LIE') or row.get('LIT', ''),
            'substitution_player': row.get('LIN', '') if row.get('LII') in {'6', '7'} else '',
            'substitution_kind': 'out' if row.get('LII') == '6' else 'in' if row.get('LII') == '7' else '',
            'db_match': player.nombre if player else '',
            'db_position': player.posicion if player else '',
            'db_club': player.club if player else '',
            'matched': bool(player),
        }

        if not number:
            item['coach_nationality'] = raw_team if raw_team and raw_team != flashscore_team else ''
            item['db_coach'] = team_coach_name(team_name)
            team['coach'] = item
        elif row.get('LL'):
            team['starters'].append(item)
        else:
            team['bench'].append(item)

    for team in report['teams'].values():
        players = team.get('starters', []) + team.get('bench', [])
        numbers_by_name = {}
        players_by_name = {}
        for player in players:
            number = player.get('number', '')
            for name in (player.get('flashscore_name', ''), player.get('db_match', '')):
                normalized = normalize_scraper_name(name)
                if not normalized:
                    continue
                players_by_name[normalized] = player
                if number:
                    numbers_by_name[normalized] = number

        for player in players:
            replacement = normalize_scraper_name(player.get('substitution_player', ''))
            player['substitution_player_number'] = numbers_by_name.get(replacement, '')
            if player.get('substitution_kind') != 'out' or not replacement:
                continue
            replacement_player = players_by_name.get(replacement)
            if not replacement_player or replacement_player.get('substitution_kind') == 'in':
                continue
            replacement_player['substitution_kind'] = 'in'
            replacement_player['substitution_minute'] = player.get('substitution_minute', '')
            replacement_player['substitution_player'] = player.get('flashscore_name', '')
            replacement_player['substitution_player_number'] = player.get('number', '')

    return report


def scrape_page(path_or_url='', include_html=False):
    url = build_scrape_url(path_or_url)
    status, html = fetch_html(url)
    parser = BasicPageParser(url)
    parser.feed(html)
    meta = parser.meta
    return ScrapedPage(
        url=url,
        status=status,
        title=parser.title,
        description=parser.description,
        meta={key: value for key, value in meta.items() if key.startswith('og:') or key == 'description'},
        match=parse_match_meta(meta),
        event_id=extract_event_id(html),
        h1=parser.h1,
        links=parser.links[:50],
        html=html if include_html else '',
    )
