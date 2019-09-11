from django.core.management.base import BaseCommand, CommandError
from craftDB.models import Mod
import json

class Command(BaseCommand):

    help = 'Adds mods from mod_abbreviations.txt'

    def handle(self, *args, **options):

        with open('./mod_abbreviations.txt', 'r') as handle:
            abbreviations = handle.read()
            d = json.loads(abbreviations).items()

        for mod_name, abbrevs in d:
            try:
                mod = Mod.objects.get(name = mod_name)
            except Mod.DoesNotExist as err:
                mod = Mod.objects.create(name = mod_name)
            mod.abbreviations = ''
            for abbrev in abbrevs.values():
                if mod.abbreviations == '':
                    mod.abbreviations = '|' + abbrev + '|'
                else:
                    mod.abbreviations = mod.abbreviations + abbrev + '|'
            mod.save()
            print('Found mod:', mod)

        try:
            Mod.objects.get(name = 'Minecraft')
        except Mod.DoesNotExist:
            Mod.objects.create(name = 'Minecraft')
        
        try:
            Mod.objects.get(name = 'Feed The Beast Infinity Evolved Expert Mode')
        except Mod.DoesNotExist:
            Mod.objects.create(name = 'Feed The Beast Infinity Evolved Expert Mode')





    