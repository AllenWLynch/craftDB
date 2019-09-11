import webbrowser
import requests
import json
from django.core.management.base import BaseCommand, CommandError
from craftDB.models import ModPack, Mod, Item
from craftDB_site.settings import DOMAIN_NAME
import collect_library as collectLib

modpack_endpoint = 'https://ftbwiki.org/api.php?action=ask&query=[[Category:Modpacks]][[{}]]|format=list|?Has%20mod&format=json'

class Command(BaseCommand):

    help = 'Links mods with modpack, adds recipes for that modpack with user input'

    def add_arguments(self, parser):
        parser.add_argument('modpack_name', type=str)

    def handle(self, *args, **options):
              
        modpack_name = options['modpack_name']
        try:
            new_modpack = ModPack.objects.get(name = modpack_name)
        except ModPack.DoesNotExist:
            new_modpack = ModPack.objects.create(name = modpack_name)
        
        r = requests.get(modpack_endpoint.format(modpack_name))
        try:
            #print(r.text)
            mods = json.loads(r.text)['query']['results'][modpack_name]['printouts']['Has mod']
        except KeyError:
            raise Exception('Returned invalid results. Check modpack name')
        
        for mod_data in mods:
            try:
                mod = Mod.objects.get(name = mod_data['fulltext'])
                new_modpack.mods.add(mod)

                collectLib.collect_mod(mod_data['fulltext'])

            except Mod.DoesNotExist:
                print('Failed to find mod: {}'.format(mod_data['fulltext']))

            break