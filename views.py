from django.shortcuts import render
import craftDB.wikiparser as wp
from django.http import HttpResponse
import re
from craftDB.models import *
from itertools import product

def index(request):
    return HttpResponse("Welcome to your CraftDB")

def addRecipeForm(request):
    return render(request, 'craftDB/addRecipeForm.html')

def scrapeData(request):

    # validate pagename
    if not 'pagename' in request.POST or request.POST['pagename'] == '':
        return render(request, 'craftDB/addRecipeForm.html', {'error_message' : 'Must provide valid wiki URL.',})
    
    if not re.search(r'ftbwiki.org', request.POST['pagename']):
        return render(request, 'craftDB/addRecipeForm.html', {'error_message' : 'URL must be for ftbwiki.org',
                                                              'pre_fill' : request.POST['pagename']})

    try:
        title = re.match(r'(?:https://)?ftbwiki.org/([\w\d_]+)', request.POST['pagename']).group(1)
    except Exception as msg:
        return render(request, 'craftDB/addRecipeForm.html', {'error_message' : 'Invalid page URL', 'pre_fill' : request.POST['pagename']})
    
    try:
        wikidata = wp.get_wikitext(title)
    
        item_info = wp.scrape_infobox(wikidata)
    
        Item.define_from_infobox(item_info)
    
        recipes_on_page = wp.scrape_recipes(wikidata)

    except Exception as msg:
        return render(request, 'craftDB/addRecipeForm.html', {'error_message' : str(msg), 'pre_fill' : request.POST['pagename']})
    
    return render(request, 'craftDB/chooseRecipeForm.html', {'output' : title, 'recipes' : recipes_on_page})

def saveRecipes(request, recipes_on_page):
    recipes_to_save = request.POST.getlist('recipes')

def investigate_oredict(name):
    contained_items = set()
    log = []
    for item_page in wp.scrape_oredict(name):
        try:
            display_name, mod = wp.parse_pagetitle(item_page).groups()
            new_item = hitDB_or_wiki_for_item(display_name, mod, item_page)
            contained_items.add( new_item )
            log.append('Added item: {}'.format(item_page))
        except Exception as err:
            log.append(err)
    
    new_dict = OreDict.objects.create(name = name)
    for contained_item in contained_items:
        new_dict.item_set.add(contained_item)

    return contained_items, log

def hitDB_or_wiki_for_item(display_name, mod, page_title):
    try:
        return Item.find_item(display_name, mod)
    except Item.DoesNotExist:
        wikidata = wp.get_wikitext(page_title)
        return Item.define_from_infobox(wp.scrape_infobox(wikidata))
    except:
        raise Exception('Multiple DB entries for {}, make your search more specific'.format(page_title))

class BadItemException(Exception):
    pass

def investigate_itemname(name, mod, page_title, is_oredict = False):
    if not is_oredict:
        try:
            return set([Item.find_item(name, mod)]), []
        except Item.DoesNotExist:
            pass
            
    try:
        return set(OreDict.objects.get(name = name).item_set.all()), []
    except OreDict.DoesNotExist:
        pass

    if not is_oredict:
        try:
            wikidata = wp.get_wikitext(page_title)
            return set([Item.define_from_infobox(wp.scrape_infobox(wikidata))]), ['Added item: {}'.format(page_title)]
        except (wp.NoInfoboxException, wp.NoIDException):
            pass
    
    try:
        item_set, log = investigate_oredict(name)
        return item_set, ['Added Oredict: {}'.format(name), *log]
    except AssertionError:
        if not is_oredict:
            raise BadItemException('Failed to get info for item: {}'.format(page_title))
    
def parse_recipe(recipe_on_page):
    
    #1. get inputs and outputs from recipe
    if recipe_on_page['grid'] == 'Crafting Table':
        inputs, outputs = wp.getIO_crafting_recipe(recipe_on_page['recipe_terms'])
    else:
        raise Exception('Cannot process machine recipes yet')

    log = []

    item_sets = []
    for input_info in inputs:
        input_set = set()
        if 'oredict' in input_info:
            for dict_name in input_info['oredict']:
                try:
                    item_set, sub_log = investigate_itemname(dict_name, None, None, True)
                    input_set.add(item_set)
                    log.extend(sub_log)
                except AssertionError as err:
                    pass
        
        if 'display_name' in input_info and (not 'oredict' in input_info or not input_info['oredict'] == input_info['display_name']):
            try:
                item_set, sub_log = investigate_itemname(input_info['display_name'], input_info['mod'], input_info['title'], False)
                input_set = input_set | item_set
                log.extend(sub_log)
            except (BadItemException, AssertionError) as err:
                log.append(err)

        if len(input_set) > 0:
            item_sets.append(input_set)
        else:
            return log

    for output_info in outputs:
        try:
            output_info['item'] = hitDB_or_wiki_for_item(output_info['display_name'], output_info['mod'], output_info['title'])
        except (BadItemException, AssertionError) as err:
            log.append(err)


    for combo in product(*item_sets):
        for index, item in enumerate(combo):

    ## continue with process
    
    return log, item_sets