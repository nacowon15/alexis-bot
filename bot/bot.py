import platform
import sys
import aiohttp
import discord

from bot import Language, StaticConfig, Configuration, Manager
from bot import defaults, get_database, init_db, log
from bot.utils import destination_repr


class AlexisBot(discord.Client):
    __author__ = 'ibk (github.com/santisteban), makzk (github.com/jkcgs)'
    __license__ = 'MIT'
    __version__ = '1.0.0-dev.53~ref_cmdevent+1'
    name = 'AlexisBot'

    def __init__(self, **options):
        """
        Inicializa la configuración, el log, una sesión aiohttp y atributos de la clase.
        :param options: Las opciones correspondientes de discord.Client
        """
        super().__init__(**options)

        self.db = None
        self.sv_config = None
        self.last_author = None
        self.initialized = False

        self.lang = {}
        self.deleted_messages = []

        self.log = log
        self.manager = Manager(self)
        self.config = StaticConfig()

        # Cliente HTTP disponible para los módulos
        headers = {'User-Agent': '{}/{} +discord.cl/alexis'.format(AlexisBot.name, AlexisBot.__version__)}
        self.http_session = aiohttp.ClientSession(
            loop=self.loop, headers=headers, cookie_jar=aiohttp.CookieJar(unsafe=True)
        )

    def init(self):
        """
        Carga la configuración, se conecta a la base de datos, y luego se conecta con Discord.
        :return:
        """
        log.info('%s v%s, discord.py v%s', AlexisBot.name, AlexisBot.__version__, discord.__version__)
        log.info('Python %s en %s.', sys.version.replace('\n', ''), sys.platform)
        log.info(platform.uname())
        log.info('------')

        # Cargar configuración
        self.load_config()
        if self.config.get('token', '') == '':
            raise RuntimeError('No se ha definido el tóken de Discord. Debe estar en e')

        # Cargar base de datos
        log.info('Conectando con la base de datos...')
        self.connect_db()
        self.sv_config = Configuration()

        # Cargar instancias de las clases de comandos cargadas en bots.modules
        log.info('Cargando comandos...')
        self.manager.load_instances()
        self.manager.dispatch_sync('on_loaded', force=True)

        # Conectar con Discord
        try:
            log.info('Conectando...')
            self.run(self.config['token'])
        except discord.errors.LoginFailure:
            raise RuntimeError('El token de Discord es incorrecto!')
        except Exception as ex:
            log.exception(ex)
            raise

    async def on_ready(self):
        """Esto se ejecuta cuando el bot está conectado y listo"""

        self.log.info('Conectado como "%s", ID %s', self.user.name, self.user.id)
        self.log.info('------')
        await self.change_presence(game=discord.Game(name=self.config['playing']))

        self.initialized = True
        await self.manager.dispatch('on_ready')

    async def send_message(self, destination, content=None, **kwargs):
        """
        Sobrecarga la llamada original de discord.Client para enviar mensajes para accionar otras llamadas
        como handlers de modificación de mensajes y registros del bot. Soporta los mismos parámetros del
        método original.
        :param destination: Dónde enviar un mensaje, como discord.Channel, discord.User, discord.Object, entre otros.
        :param content: El contenido textual a enviar
        :param kwargs: El resto de parámetros del método original.
        :return:
        """
        # Call pre_send_message handlers, append destination
        kwargs = {'destination': destination, 'content': content, **kwargs}
        self.manager.dispatch_ref('pre_send_message', kwargs)

        # Log the message
        dest = destination_repr(kwargs['destination'])
        msg = 'Sending message "{}" to {} '.format(kwargs['content'], dest)
        if isinstance(kwargs.get('embed'), discord.Embed):
            msg += ' (with embed: {})'.format(kwargs.get('embed').to_dict())
        self.log.debug(msg)

        # Send the actual message
        return await super(AlexisBot, self).send_message(**kwargs)

    async def delete_message(self, message):
        """
        Elimina un mensaje, y además registra los IDs de los últimos 20 mensajes guardados
        :param message: El mensaje a eliminar
        """
        self.deleted_messages.append(message.id)

        try:
            await super().delete_message(message)
        except discord.Forbidden as e:
            del self.deleted_messages[-1]
            raise e

        if len(self.deleted_messages) > 20:
            del self.deleted_messages[0]

    def connect_db(self):
        """
        Ejecuta la conexión a la base de datos
        """
        self.db = get_database()
        init_db()
        log.info('Conectado correctamente a la base de datos mediante %s', self.db.__class__.__name__)

    def load_config(self):
        """
        Carga la configuración estática y de idioma
        :return: Un valor booleano dependiente del éxito de la carga de los datos.
        """
        try:
            log.info('Cargando configuración...')
            self.config.load(defaults.config)
            self.lang = Language('lang', default=self.config['default_lang'], autoload=True)
            log.info('Configuración cargada')
            return True
        except Exception as ex:
            self.log.exception(ex)
            return False

    async def close(self):
        super().close()
        await self.http_session.close()
        await self.http.close()
        self.manager.cancel_tasks()

    """
    ===== EVENT HANDLERS =====
    """

    async def on_message(self, message):
        await self.manager.dispatch('on_message', message=message)

    async def on_reaction_add(self, reaction, user):
        await self.manager.dispatch('on_reaction_add', reaction=reaction, user=user)

    async def on_reaction_remove(self, reaction, user):
        await self.manager.dispatch('on_reaction_remove', reaction=reaction, user=user)

    async def on_reaction_clear(self, message, reactions):
        await self.manager.dispatch('on_reaction_clear', message=message, reactions=reactions)

    async def on_member_join(self, member):
        await self.manager.dispatch('on_member_join', member=member)

    async def on_member_remove(self, member):
        await self.manager.dispatch('on_member_remove', member=member)

    async def on_member_update(self, before, after):
        await self.manager.dispatch('on_member_update', before=before, after=after)

    async def on_message_delete(self, message):
        await self.manager.dispatch('on_message_delete', message=message)

    async def on_message_edit(self, before, after):
        await self.manager.dispatch('on_message_edit', before=before, after=after)

    async def on_server_join(self, server):
        await self.manager.dispatch('on_server_join', server=server)

    async def on_server_remove(self, server):
        await self.manager.dispatch('on_server_remove', server=server)

    async def on_member_ban(self, member):
        await self.manager.dispatch('on_member_ban', member=member)

    async def on_member_unban(self, member):
        await self.manager.dispatch('on_member_unban', member=member)

    async def on_typing(self, channel, user, when):
        await self.manager.dispatch('on_server_remove', channel=channel, user=user, when=when)
