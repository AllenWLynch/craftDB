from django.shortcuts import render
import craftDB.wikiparser as wp
from django.http import HttpResponse
import re
from craftDB.models import *
from itertools import product
from django.urls import reverse
import requests
from craftDB.recipefinder import hitDB_or_wiki_for_item, parse_recipe
from django.shortcuts import get_object_or_404
import craftDB.api_helper as api


def index(request):
    return render(request, 'craftDB/index.html')

def get_item_names(request):
    if request.method == 'GET':
        modpack = get_object_or_404(ModPack, name = request.GET['modpack'])
        item_names = set([
            str(item) for mod in modpack.mods.all() for item in mod.item_set.all()
        ])
        return HttpResponse('\n'.join(item_names), content_type='text/plain')
    else:
        return HttpResponse(status = 404)

def get_recipe_info(request, id):
    if request.method == 'GET':
        recipe = get_object_or_404(Recipe, pk = id)
        try:
            translation_dict = api.convert_recipe_to_lua(recipe)
        except AssertionError:
            return HttpResponse(status = 500)
        
        return HttpResponse(translation_dict, content_type = 'text/plain')
    else:
        return HttpResponse(status = 404)

def addRecipeForm(request):
    return render(request, 'craftDB/addRecipeForm.html')

def disambiguation(request):
    #https://ftbwiki.org/api.php?action=query&list=search&srsearch=Conveyor+Belt&srwhat=title
    if request.method == 'POST':
        search_title = request.POST['search_title']
        if not search_title or search_title == '':
            return render(request, 'craftDB/addRecipeForm.html', {'pre_fill' :search_title})
        
        params = {
            'action':'query',
            'list':'search',
            'srsearch':search_title,
            'srwhat':'title',
            'format':'json'
        }
        try:
            response = requests.get('https://ftbwiki.org/api.php',params= params)
        except:
            return render(request, 'craftDB/addRecipeForm.html', {'pre_fill' :search_title, 'error_message' : 'Could not connect to wiki'})
        if not response.status_code == 200:
            print(response.status_code)
            return render(request, 'craftDB/addRecipeForm.html', {'pre_fill' :search_title, 'error_message' : 'No results for this search'})
        
        try:
            results =  response.json()['query']['search']
        except KeyError as err:
            return render(request, 'craftDB/addRecipeForm.html', {'pre_fill' :search_title, 'error_message' : 'No results for this search'})
        
        pages = [ result['title'] for result in results ]
        request.session['pages'] = pages
        return render(request, 'craftDB/disambiguation.html', {'pages': pages})

def scrapeData(request, page_title = None):
    # validate pagename     
    if (request.method == 'POST' and 'page_selection' in request.POST) or page_title:
        
        if not page_title:
            page_title = request.POST['page_selection']


        display_name, mod = wp.parse_pagetitle(page_title)
        try:
            wikidata = wp.PageParser(page_title)
        except wp.NoWikiTextException as err:
            return render(request, 'craftDB/disambiguation.html', {'pages' : request.session['pages'], 'error_message' : str(err)})

        item = None
        try:
            item = Item.find_item(display_name, mod)
        except Item.DoesNotExist:
            try:
                infobox_data = wikidata.scrape_infobox()

                try:
                    infobox_data['mod'] = Mod.objects.get(name = infobox_data['mod']).id
                except KeyError:
                    raise wp.IncompletePageException(page_title, infobox_data)
                except Mod.DoesNotExist:
                    raise wp.BadItemPageException('Item: {} is not in your modpack'.format(page_title))

                item_form = ItemForm(infobox_data)
                if not item_form.is_valid():
                    raise wp.IncompletePageException(page_title, infobox_data)
            
                item = item_form.save()
            except wp.BadItemPageException as err:
                return render(request, 'craftDB/disambiguation.html', {'pages' : request.session['pages'], 'error_message' : str(err)})

        request.session['output_item'] = item.id
        try:
            recipes_on_page = wikidata.scrape_recipes()
        except wp.NoRecipesException as err:
                return render(request, 'craftDB/disambiguation.html', {'pages' : request.session['pages'], 'error_message' : str(err)})
        request.session['scraped_data'] = recipes_on_page
        request.session['page_title'] = page_title
        return render(request, 'craftDB/chooseRecipeForm.html', {'output' : page_title, 'recipes' : recipes_on_page})
    else:
        return render(request, 'craftDB/disambiguation.html', {'pages' : request.session['pages']})

def testview(request):
    log = [str( dbEntryObj(item) ) for item in Item.objects.all()]
    return render(request, 'craftDB/showLogForm.html', {'log' : log})

def saveRecipes(request):
    recipes_to_save = request.POST.getlist('recipes')
    big_log = []
    for save_index in recipes_to_save:
        save_recipe = request.session['scraped_data'][int(save_index) -1]
        parse_recipe(big_log, request.session['page_title'], Item.objects.get(pk = request.session['output_item']), **save_recipe)
    
    return render(request, 'craftDB/showLogForm.html', {'log' : [str(x) for x in big_log], 'search_page': request.session['page_title']})