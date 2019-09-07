import re
from craftDB.models import *
from itertools import product
from django.urls import reverse
import craftDB.wikiparser as wp
from django.core.files import File
from urllib import request
import os

def result_dbEntry(newObj, start_sublist = False, end_sublist = False):
    return '{0}<a href=\"{1}\" target="_blank">{2}</a>{3}'.format(
        '<ul>' if start_sublist else '',
        reverse('admin:craftDB_{}_change'.format(newObj.__class__.__name__.lower()), args = (newObj.id,), current_app='craftadmin'), 
        'Added {}: {}'.format(newObj.__class__.__name__, str(newObj)),
        '</ul>' if end_sublist else '')

def get_oredict_from_wiki(name, log):
    contained_items = set()
    
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
    return new_dict

def hitDB_or_wiki_for_item(display_name, mod, page_title, log = []):
    try:
        return Item.find_item(display_name, mod)
    except Item.DoesNotExist:
        # try investigating wikidata
        wikidata = wp.PageParser(page_title)
        infobox_data = wikidata.scrape_infobox()

        try:
            infobox_data['mod'] = Mod.objects.get(name = infobox_data['mod']).id
        except KeyError:
            raise wp.IncompletePageException(page_title, infobox_data)
        except Mod.DoesNotExist:
            newmod = Mod.objects.create(name = infobox_data['mod'])
            infobox_data['mod'] = newmod.id
        
        item_form = ItemForm(infobox_data)
        if not item_form.is_valid():
            raise wp.IncompletePageException(page_title, infobox_data)

        new_item = item_form.save()
        log.append(result_dbEntry(new_item))

        try:
            image_filename, image_url = wikidata.get_main_image()
            result = request.urlretrieve(image_url) # image_url is a URL to an image
            new_item.sprite.save(
                os.path.basename(image_filename),
                File(open(result[0], 'rb'))
                )

            new_item.save()
        except wp.NoImageException:
            pass

        return new_item
    except:
        raise wp.BadItemPageException('Multiple DB entries for {}, make your search more specific'.format(page_title))

def hitDB_or_wiki_for_oredict(name, log):
    try:
        return OreDict.objects.get(name = name)
    except OreDict.DoesNotExist:
        return get_oredict_from_wiki(name, log)
    
class ConstructRecipeException(Exception):
    pass

def get_item_objects(input_info, log):
    item_set = set()
    try_both = 'display_name' in input_info and (not 'oredict' in input_info or not input_info['oredict'] == input_info['display_name'])
    if 'oredict' in input_info:
        #print('here')
        try:
            return hitDB_or_wiki_for_oredict(input_info['oredict'], log)
        except wp.NoOreDictException as err:
            if not try_both:
                log.append(err)
                raise ConstructRecipeException()
    # continue if oredict didn't work out (oredict is primary option)
    if try_both:
        try:
            return hitDB_or_wiki_for_item(input_info['display_name'], input_info['mod'], input_info['page_title'], log)
        except wp.BadItemPageException as err:
            try:
                return hitDB_or_wiki_for_oredict(input_info['display_name'], log)
            except wp.NoOreDictException:
                pass
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
        db_item_objects = [ get_item_objects(input_info, log) for input_info in inputs ]

        if grid == 'Crafting Table':
            new_recipe = CraftingRecipe.objects.create(output = output_item, amount = output_info['amount'])
            
            for item_object, input_info in zip(db_item_objects, inputs):
                new_recipe.slotdata_set.create(slot = int(input_info['slot']), item_object = item_object)
            #for byproduct in byproducts:
            #    new_recipe.byproduct_set.create(byproduct)
        log.append(result_dbEntry(new_recipe, end_sublist= True))

    except ConstructRecipeException:
        log.append('Failed to construct recipe: {}</ul>'.format(header))