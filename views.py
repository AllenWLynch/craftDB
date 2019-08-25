from django.shortcuts import render
import craftDB.wikiparser as wp
from django.http import HttpResponse
import re
from craftDB.models import *
from itertools import product
from django.urls import reverse

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
        item_info = wp.scrape_infobox(wikidata, title)
        Item.define_from_infobox(item_info)
        recipes_on_page = wp.scrape_recipes(wikidata)
    except Exception as msg:
        return render(request, 'craftDB/addRecipeForm.html', {'error_message' : str(msg), 'pre_fill' : request.POST['pagename']})
    
    request.session['scraped_data'] = recipes_on_page
    request.session['search_page'] = title
    return render(request, 'craftDB/chooseRecipeForm.html', {'output' : title, 'recipes' : recipes_on_page})

def testview(request):
    log = [str( dbEntryObj(item) ) for item in Item.objects.all()]
    return render(request, 'craftDB/showLogForm.html', {'log' : log})

def investigate_oredict(name):
    contained_items = set()
    log = []
    for item_page in wp.scrape_oredict(name):
        try:
            display_name, mod = wp.parse_pagetitle(item_page).groups()
            new_item = hitDB_or_wiki_for_item(display_name, mod, item_page)
            contained_items.add( new_item )
        except Exception as err:
            log.append(err)
    
    new_dict = OreDict.objects.create(name = name)
    log.append(dbEntryObj(new_dict))
    for contained_item in contained_items:
        new_dict.item_set.add(contained_item)
        log.append(dbEntryObj(contained_item))

    return contained_items, log

def hitDB_or_wiki_for_item(display_name, mod, page_title):
    try:
        return Item.find_item(display_name, mod)
    except Item.DoesNotExist:
        wikidata = wp.get_wikitext(page_title)
        return Item.define_from_infobox(wp.scrape_infobox(wikidata, page_title))
    except:
        raise Exception('Multiple DB entries for {}, make your search more specific'.format(page_title))

class BadItemException(Exception):
    pass

class dbEntryObj():
    def __init__(self, newEntry, end_level = False):
        self.msg = 'Added {}: {}'.format(newEntry.__class__.__name__, str(newEntry))
        self.redir_url = reverse('admin:craftDB_{}_change'.format(newEntry.__class__.__name__.lower()), args = (newEntry.id,), current_app='craftadmin')
        self.end_level = end_level

    def __str__(self):
        return '<a href=\"{0}\" target="_blank">{1}</a>{2}'.format(self.redir_url, self.msg, '</ul>' if self.end_level else '')

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
            new_item = Item.define_from_infobox(wp.scrape_infobox(wikidata, page_title))
            return set([new_item]), [dbEntryObj(new_item)]
        except (wp.NoInfoboxException, wp.NoIDException):
            pass
        except wp.NoDataException as err:
            raise BadItemException(err)
        except wp.IncompletePageException as err:
            raise BadItemException('Page: {} has incomplete information.'.format(page_title))
    try:
        return investigate_oredict(name)
    except AssertionError:
        if not is_oredict:
            raise BadItemException('Failed to get info for item: {}'.format(page_title))
    

def parse_recipe(recipe_name, gridtype, template_str, edit_url):
    
    if gridtype == 'Crafting Table':
        inputs, outputs = wp.getIO_crafting_recipe(template_str)
    else:
        raise Exception('Cannot process machine recipes yet')

    log = ['<b>Attempting to construct from template: <a href=\"{}\">{}</a></b><ul>'.format(edit_url, recipe_name)]

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
            log.append('Failed to construct recipe: {}</ul>'.format(recipe_name))
            return log

    item_combos = product(*item_sets)

    for output_info in outputs:
        if output_info['amount'] > 0:
            try:
                print(':', output_info['title'], ':')
                output_item = hitDB_or_wiki_for_item(output_info['display_name'], output_info['mod'], output_info['title'])
                
                if gridtype == 'Crafting Table':
                    # check for dups
                    new_recipe = CraftingRecipe.objects.create(output = output_item, amount = output_info['amount'])
                    for combo in item_combos:
                        for index, item in enumerate(combo):
                            input_info = inputs[index]
                            new_recipe.slotdata_set.create(slot = int(input_info['slot']), item = item)
                            
                log.append(dbEntryObj(new_recipe, True))
            except (BadItemException, AssertionError) as err:
                log.append(err)
                log.append('Failed to construct recipe: {}</ul>'.format(recipe_name))
        
    return log

def saveRecipes(request):
    recipes_to_save = request.POST.getlist('recipes')
    big_log = []
    for save_index in recipes_to_save:
        save_recipe = request.session['scraped_data'][int(save_index) -1]
        edit_url = 'https://ftbwiki.org/index.php?title={}&action=edit&section={}'.format(request.session['search_page'], str(save_recipe['section_num']))
        big_log.extend( parse_recipe(save_recipe['header'], save_recipe['grid'], save_recipe['recipe_terms'], edit_url))
    
    return render(request, 'craftDB/showLogForm.html', {'log' : [str(x) for x in big_log], 'search_page': request.session['search_page']})