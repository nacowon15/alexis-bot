import asyncio
import aiohttp
import discord

from . import SingleLanguage
from .logger import log
from .libs.configuration import ServerConfiguration


class Command:
    def __init__(self, bot):
        self.bot = bot
        self.log = log
        self.name = ''
        self.aliases = []
        self.swhandler = []
        self.swhandler_break = False
        self.mention_handler = False
        self.help = '$[missing-help]'
        self.allow_pm = True
        self.allow_nsfw = True  # TODO
        self.nsfw_only = False  # TODO
        self.pm_error = '$[disallowed-via-pm]'
        self.bot_owner_only = False
        self.owner_only = False
        self.owner_error = 'no puedes usar este comando'
        self.format = ''  # TODO
        self.default_enabled = True
        self.default_config = None

        self.user_delay = 0
        self.users_delay = {}
        self.user_delay_error = 'aún no puedes usar este comando'
        self.db_models = []

        headers = {'User-Agent': '{}/{} +discord.cl/alexis'.format(bot.__class__.name, bot.__class__.__version__)}
        self.http = aiohttp.ClientSession(
            loop=asyncio.get_event_loop(), headers=headers, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )

    def can_manage_roles(self, server):
        self_member = server.get_member(self.bot.user.id)
        return self_member.server_permissions.manage_roles

    def config_mgr(self, serverid):
        return ServerConfiguration(self.bot.sv_config, serverid)

    def right_cmd(self, cmd):
        return cmd.is_cmd and cmd.cmdname == self.name or cmd.cmdname in self.aliases

    def handle(self, cmd):
        pass

    def get_lang(self, svid=None):
        """
        Genera una instancia de SingleLanguage para un servidor en específico o con el idioma predeterminado.
        :param svid: El ID del servidor para obtener el idioma. Si es None, se devuelve una instancia con el idioma
        predeterminado.
        :return: La instancia de SingleLanguage con el idioma obtenido.
        """
        if svid is None:
            lang_code = self.bot.config['default_lang']
        else:
            svid = svid if not isinstance(svid, discord.Server) else svid.id
            lang_code = self.bot.sv_config.get(svid, 'lang', self.bot.config['default_lang'])

        return SingleLanguage(self.bot.lang, lang_code)
