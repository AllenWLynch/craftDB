import re
from craftDB.models import *
from itertools import product
from django.urls import reverse
import craftDB.wikiparser as wp

def result_dbEntry(newObj, start_sublist = False, end_sublist = False):
    return '{0}<a href=\"{1}\" target="_blank">{2}</a>{3}'.format(
        '<ul>' if start_sublist else '',
        reverse('admin:craftDB_{}_change'.format(newObj.__class__.__name__.lower()), args = (newObj.id,), current_app='craftadmin'), 
        'Added {}: {}'.format(newObj.__class__.__name__, str(newObj)),
        '</ul>' if end_sublist else '')

def get_oredict_from_wiki(name):
    contained_items = set()
    log = []
    
    for item_page in wp.scrape_oredict(name):
        try:
            display_name, mod = wp.parse_pagetitle(item_page)
            new_item = hitDB_or_wiki_for_item(display_name, mod, item_page)
            contained_items.add( new_item )
        except wp.BadItemPageException as err:
            log.append(err)
    
    if len(contained_items) == 0:
        raise wp.NoOreDictException()

    new_dict = OreDict.objects.create(name = name)
    log.append(result_dbEntry(new_dict))
    for contained_item in contained_items:
        new_dict.item_set.add(contained_item)
        log.append(result_dbEntry(contained_item))
    
    log.append('Adding recipes using Oredict subsitutions</ul>')
    return contained_items, log

def hitDB_or_wiki_for_item(display_name, mod, page_title):
    try:
        return Item.find_item(display_name, mod), False
    except Item.DoesNotExist:
        # try investigating wikidata
        wikidata = wp.PageParser(page_title)
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

        return item_form.save(), True
    except:
        raise wp.BadItemPageException('Multiple DB entries for {}, make your search more specific'.format(page_title))

def hitDB_or_wiki_for_oredict(name):
    try:
        return set(OreDict.objects.get(name = name).item_set.all()), []
    except OreDict.DoesNotExist:
        return get_oredict_from_wiki(name)
    
class ConstructRecipeException(Exception):
    pass

def get_itemset(input_info, log):
    item_set = set()
    try_both = 'display_name' in input_info and (not 'oredict' in input_info or not input_info['oredict'] == input_info['display_name'])
    if 'oredict' in input_info:
        for dict_name in input_info['oredict']:
            try:
                new_items, sublog = hitDB_or_wiki_for_oredict(dict_name)
                item_set = item_set | new_items
                log.extend(sublog)
            except wp.NoOreDictException as err:
                if not try_both:
                    log.append(err)
                    raise ConstructRecipeException()
    # continue if oredict didn't work out (oredict is primary option)
    if try_both:
        try:
            new_items, sublog = hitDB_or_wiki_for_oredict(input_info['display_name'])
            item_set = item_set | new_items
            log.extend(sublog)
        except wp.NoOreDictException:
            pass
        try:
            new_item, added_to_DB = hitDB_or_wiki_for_item(input_info['display_name'], input_info['mod'], input_info['page_title'])
            item_set.add(new_item)
            if added_to_DB:
                log.append(result_dbEntry(new_item))
        except wp.BadItemPageException as err:
            log.append(err)
            raise ConstructRecipeException()

    return item_set
    
def parse_recipe(log, page_title, output_item, header, grid, recipe_terms, section_num):
   
    if grid == 'Crafting Table':
        inputs, output_info, byproducts = wp.getIO_crafting_recipe(recipe_terms)
    else:
        raise Exception('Cannot process machine recipes yet')

    log.append('<b>Attempting to construct from template: <a href=\"https://ftbwiki.org/index.php?action=edit&title={}&section={}\">{}</a></b><ul>'.format(page_title, section_num, header))

    try:
        recipes_made = 0
        item_sets = [ get_itemset(input_info, log) for input_info in inputs ]
        item_combos = product(*item_sets)

        for combo in item_combos:
            recipes_made += 1
            if grid == 'Crafting Table':
                new_recipe = CraftingRecipe.objects.create(output = output_item, amount = output_info['amount'])
                for item, input_info in zip(combo, inputs):
                    new_recipe.slotdata_set.create(slot = int(input_info['slot']), item = item)
                for byproduct in byproducts:
                    new_recipe.byproduct_set.create(byproduct)
            log.append(result_dbEntry(new_recipe, end_sublist= True))

    except ConstructRecipeException:
        log.append('Failed to construct recipe: {}</ul>'.format(header))