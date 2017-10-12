import re
from datetime import datetime
from urllib import parse

import peewee
from discord import Embed, Colour

from modules.base.command import Command, Message
from modules.base.database import BaseModel


class MacroSet(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.name = 'set'
        self.help = 'Agrega o actualiza un macro'
        self.owner_only = True
        self.db_models = [Meme]

    async def handle(self, message, cmd):
        if len(cmd.args) < 2:
            await cmd.answer('Formato: !set <nombre> <contenido>')
            return

        meme_name = cmd.args[0]
        meme_value = ' '.join(cmd.args[1:])

        meme, created = Meme.get_or_create(name=meme_name)
        meme.content = meme_value
        meme.save()

        if created:
            msg = 'Macro **{name}** creado'.format(name=meme_name)
            self.bot.log.info('Macro %s creado con valor: "%s"', meme_name, meme_value)
        else:
            msg = 'Macro **{name}** actualizado'.format(name=meme_name)
            self.bot.log.info('Macro %s actualizado a: "%s"', meme_name, meme_value)

        await cmd.answer(msg)


class MacroUnset(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.name = 'unset'
        self.help = 'Elimina un macro'
        self.owner_only = True

    async def handle(self, message, cmd):
        if len(cmd.args) < 1:
            await cmd.answer('Formato: !unset <nombre>')
            return

        meme_name = cmd.args[0]

        try:
            meme = Meme.get(name=meme_name)
            meme.delete_instance()
            msg = 'Macro **{name}** eliminado'.format(name=meme_name)
            await cmd.answer(msg)
            self.bot.log.info('Macro %s eliminado', meme_name)
        except Meme.DoesNotExist:
            msg = 'El macro **{name}** no existe'.format(name=meme_name)
            await cmd.answer(msg)


class MacroList(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.name = 'list'
        self.help = 'Muestra una lista de los nombres de los macros guardados'
        self.rx_mention = re.compile('^<@!?[0-9]+>$')

    async def handle(self, message, cmd):
        namelist = []
        for item in Meme.select().iterator():
            if re.match(self.rx_mention, item.name):
                name = item.name.replace('!', '')
                member_id = name[2:-1]
                member = cmd.member_by_id(member_id)
                name = '*\\@{}*'.format(Command.final_name(member))
            else:
                name = item.name
            namelist.append(name)

        word = 'macros' if len(namelist) == 1 else 'macros'
        resp = 'Hay {} {}: {}'.format(len(namelist), word, ', '.join(namelist))
        await cmd.answer(resp)


class MacroSuperList(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.name = bot.config['command_prefix'] + 'list'
        self.help = 'Muestra una lista completa de los macros con sus valores'
        self.owner_only = True
        self.rx_mention = re.compile('^<@!?[0-9]+>$')
        self.rx_blob = re.compile('^<:[a-zA-Z\-_]+:[0-9]+>$')

    async def handle(self, message, cmd):
        memelist = []
        for item in Meme.select().iterator():
            if re.match(self.rx_mention, item.name):
                name = item.name.replace('!', '')
                member_id = name[2:-1]
                member = cmd.member_by_id(member_id)
                name = '@' + Command.final_name(member)
            elif re.match(self.rx_blob, item.name):
                name = ':{}:'.format(item.name.split(':')[1])
            else:
                name = item.name
            memelist.append("- {}: {}".format(name, item.content))

        num_memes = len(memelist)
        if num_memes == 0:
            await cmd.answer('No hay macros disponibles')
            return

        word = 'macro' if num_memes == 1 else 'macros'
        resp = 'Hay {} {}:'.format(num_memes, word)
        await cmd.answer(resp)

        # Separar lista de memes en mensajes con menos de 2000 carácteres
        resp_list = ''
        for meme in memelist:
            if len('```{}\n{}```'.format(resp_list, meme)) > 2000:
                await cmd.answer('```{}```'.format(resp_list))
                resp_list = ''
            else:
                resp_list = '{}\n{}'.format(resp_list, meme)

        # Enviar lista restante
        if resp_list != '':
            await cmd.answer('```{}```'.format(resp_list))


class MacroUse(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.swhandler = [bot.config['command_prefix'] + ' ', '¡']
        self.first_use = True

    async def handle(self, message, cmd):
        # Inicializar macros por defecto
        if self.first_use:
            num_memes = len(self.bot.config['default_memes'])
            if num_memes > 0:
                self.log.info('Inicializando base de datos...')
                for meme_name, meme_cont in self.bot.config['default_memes'].items():
                    Meme.get_or_create(name=meme_name, content=meme_cont)
                self.log.info('Base de datos inicializada')
            self.first_use = False

        # Actualizar el id de la última persona que usó el comando, omitiendo al mismo bot
        if self.bot.last_author is None or not cmd.own:
            self.bot.last_author = message.author.id

        meme_query = cmd.args[0] if message.content.startswith('! ') else message.content[1:].split(' ')[0]

        try:
            server_id = 'global' if cmd.is_pm else message.server.id
            macro = EmbedMacro.get(EmbedMacro.name == meme_query, EmbedMacro.server == server_id)
            embed = Embed()
            if macro.image_url != '':
                embed.set_image(url=macro.image_url)
            if macro.title != '':
                embed.title = macro.title
            if macro.description != '':
                embed.description = macro.description
            await cmd.answer(embed=embed)
            return
        except EmbedMacro.DoesNotExist:
            pass

        try:
            meme = Meme.get(Meme.name == meme_query)
            await cmd.answer(meme.content)
            return
        except Meme.DoesNotExist:
            pass


class EmbedMacroSet(Command):
    def __init__(self, bot):
        super().__init__(bot)
        self.name = 'iset'
        self.help = 'Define un embed macro'
        self.owner_only = True
        self.db_models = [EmbedMacro]
        self.rx_colour = re.compile('#?[0-9a-fA-F]{6}')
        self.colour_list = ['default', 'teal', 'dark_teal', 'green', 'dark_green', 'blue', 'dark_blue', 'purple',
                            'dark_purple', 'gold', 'dark_gold', 'orange', 'dark_orange', 'red', 'dark_red',
                            'lighter_grey', 'dark_grey', 'light_grey', 'darker_grey']

    async def handle(self, message, cmd):
        if len(cmd.args) < 2:
            await cmd.answer('Formato: !iset <nombre> [url_imagen]|[título]|[descripción]|[color_embed]')
            return

        name = cmd.args[0]
        subargs = ' '.join(cmd.args[1:]).split('|')
        self.log.info('subargs: ' + str(subargs))
        image_url = ''
        title = ''
        description = ''
        embed_color = Colour.default()

        if subargs[0].strip() != '':
            image_url = subargs[0].strip()

        if len(subargs) > 1 and subargs[1].strip() != '':
            title = subargs[1].strip()

        if len(subargs) > 2 and subargs[2].strip() != '':
            description = subargs[2].strip()

        if len(subargs) > 3 and subargs[3].strip() != '':
            embed_color = subargs[3].strip()
            if re.match(self.rx_colour, embed_color):
                if embed_color.startswith("#"):
                    embed_color = embed_color[1:]
                embed_color = Colour(int(embed_color, 16))
            else:
                embed_color = embed_color.lower().replace(' ', '_')
                if embed_color in self.colour_list:
                    embed_color = getattr(Colour, embed_color)()
                else:
                    await cmd.answer('Color inválido')
                    return

        if image_url == '' and title == '' and description == '':
            await cmd.answer('Al menos la imagen, el titulo o la descripción deben ser ingresados')
            return

        server_id = 'global' if cmd.is_pm else message.server.id
        macro, created = EmbedMacro.get_or_create(name=name, server=server_id)
        macro.image_url = image_url
        macro.title = title
        macro.description = description
        macro.embed_color = embed_color.value
        macro.save()

        if created:
            await cmd.answer('Macro **{}** creado'.format(name))
        else:
            await cmd.answer('Macro **{}** actualizado'.format(name))


class Meme(BaseModel):
    name = peewee.TextField(primary_key=True)
    content = peewee.TextField(null=True)


class EmbedMacro(BaseModel):
    name = peewee.TextField()
    server = peewee.TextField()
    image_url = peewee.TextField(null=True)
    title = peewee.TextField(null=True)
    description = peewee.TextField(null=True)
    embed_color = peewee.IntegerField(default=Colour.default().value)
    created = peewee.DateTimeField(default=datetime.now)
