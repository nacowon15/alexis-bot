import discord
import re
from discord import Embed

from alexis.libs.configuration import ServerConfigMgrSingle


pat_tag = re.compile('^<(@!?|#|a?:([a-zA-Z0-9\-_]+):)(\d{10,19})>$')
pat_usertag = re.compile('^<@!?(\d{10,19})>$')
pat_channel = re.compile('^<#\d{10,19}>$')
pat_subreddit = re.compile('^[a-zA-Z0-9_\-]{2,25}$')
pat_emoji = re.compile('<a?(:([a-zA-Z0-9\-_]+):)([0-9]+)>')
pat_normal_emoji = re.compile('^:[a-zA-Z\-_]+:$')


def is_int(val):
    try:
        int(val)
        return True
    except (IndexError, ValueError):
        return False


def is_float(val):
    try:
        float(val)
        return True
    except (IndexError, ValueError):
        return False


def is_owner(bot, member, server):
    if server is None or not isinstance(member, discord.Member):
        return False

    if member.server_permissions.administrator:
        return True

    cfg = ServerConfigMgrSingle(bot.sv_config, server.id)

    owner_roles = cfg.get('owner_roles', bot.config['owner_role'])
    if owner_roles == '':
        owner_roles = []
    else:
        owner_roles = owner_roles.split('\n')

    for role in member.roles:
        if role.id in owner_roles \
                or role.name in owner_roles \
                or member.id in owner_roles:
            return True

    return False


def get_server_role(server, role):
    """
    Obtiene la instancia de un rol de un servidor
    :param server: La instancia de servidor en la que se buscará
    :param role: El nombre o ID del rol
    :return: La instancia del rol, o None si no ha sido encontrado
    """
    if not isinstance(server, discord.Server):
        raise RuntimeError('"server" argument must be a discord.Server instance')

    for role_ins in server.roles:
        if role_ins.name == role or role_ins.id == role:
            return role_ins

    return None


def member_has_role(member, role):
    """
    Verifica si un miembro dado tiene un rol
    :param member: El miembro de un servidor
    :param role: El nombre, ID del rol o el rol
    :return:
    """
    if not isinstance(member, discord.Member):
        raise RuntimeError('"member" argument must be a discord.Member instance')

    for member_role in member.roles:
        if isinstance(role, discord.Role) and member_role == role:
            return True
        if member_role.name == role or member_role.id == role:
            return True

    return False


def img_embed(url, title=''):
    embed = Embed()
    embed.set_image(url=url)
    if title != '':
        embed.title = title
    return embed


def text_cut(text, limit, cutter='…'):
    """
    Corta un texto y agrega un texto al final en caso de que el texto sea mayor que el tamaño límite
    :param text: El texto a cortar
    :param limit: El límite de texto
    :param cutter: El texto que se colocará al final en caso de ser cortado
    :return: El texto cortado, si corresponde, o el texto completo, si no supera el límite.
    """
    if len(text) > limit:
        return text[:limit-len(cutter)-1] + cutter
    else:
        return text


def parse_tag(text):
    if not pat_tag.match(text):
        return None

    if pat_channel.match(text):
        return {'type': 'channel', 'id': text[2:-1]}

    emoji = pat_emoji.match(text)
    if emoji is not None:
        return {'type': 'emoji', 'name': emoji.group(2), 'animated': text.startswith('<a'), 'id': emoji.group(3)}

    user = pat_usertag.match(text)
    if user is not None:
        return {'type': 'user', 'id': user.group(0), 'with_nick': text.startswith('<@!')}
    
    return None


def unserialize_avail(avails):
    return '|'.join([v + k for k, v in avails.items()])


def serialize_avail(avails):
    return {c[1:]: c[0] for c in avails.split('|') if c != ''}


def deltatime_to_str(deltatime):
    result = []
    if deltatime.days > 0:
        result.append(str(deltatime.days) + ' día{}'.format('' if deltatime.days == 1 else 's'))
    m, s = divmod(deltatime.seconds, 60)
    h, m = divmod(m, 60)

    if h > 0:
        result.append(str(h) + ' hora{}'.format('' if h == 1 else 's'))
    if m > 0:
        result.append(str(m) + ' minuto{}'.format('' if m == 1 else 's'))
    if s > 0:
        result.append(str(s) + ' segundo{}'.format('' if s == 1 else 's'))

    return ', '.join(result)
