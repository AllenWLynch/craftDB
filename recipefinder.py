import re
from craftDB.models import *
from itertools import product
from django.urls import reverse
import craftDB.wikiparser as wp
from django.core.files import File
from urllib import request
import os

class new_DB_entry(wp.BadItemPageException):

    def __init__(self, newObj):
        self.newObj = newObj

    def __html__(self):
        return '<a href=\"{1}\" target="_blank">{2}</a>'.format(
            reverse('admin:craftDB_{}_change'.format(self.newObj.__class__.__name__.lower()), args = (self.newObj.id,), current_app='craftadmin'), 
            'Added {}: {}'.format(self.newObj.__class__.__name__, str(self.newObj)))
    
    def __str__(self):
        return 'Added {}: {}'.format(self.newObj.__class__.__name__, str(self.newObj))

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

def hitDB_or_wiki_for_item(display_name, mod, page_title, log_node, wikidata = None):
    try:
        return Item.find_item(display_name, mod)
    except Item.DoesNotExist:
        # try investigating wikidata
        if not wikidata:
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

def hitDB_or_wiki_for_oredict(name, log_node):
    try:
        return OreDict.objects.get(name = name)
    except OreDict.DoesNotExist:
        return get_oredict_from_wiki(name, log_node)
    
class ConstructRecipeException(Exception):
    
    def __init__(self, sub_error):
        self.sub_error = sub_error

def get_item_objects(input_info, log_node):
    item_set = set()
    try_both = 'display_name' in input_info and (not 'oredict' in input_info or not input_info['oredict'] == input_info['display_name'])
    if 'oredict' in input_info:
        #print('here')
        try:
            return hitDB_or_wiki_for_oredict(input_info['oredict'], log_node)
        except wp.NoOreDictException as err:
            if not try_both:
                raise ConstructRecipeException(err)
    # continue if oredict didn't work out (oredict is primary option)
    if try_both:
        try:
            return hitDB_or_wiki_for_item(input_info['display_name'], input_info['mod'], input_info['page_title'], log_node)
        except wp.BadItemPageException as err:
            try:
                return hitDB_or_wiki_for_oredict(input_info['display_name'], log_node)
            except wp.NoOreDictException:
                pass
            raise ConstructRecipeException(err)

    return item_set

class Potential_Recipe():
    def __init__(self, title, section_num, header):
        self.page_title = title
        self.section_num = section_num
        self.header = header

    def __str__(self):
        return 'Attempting to construct recipe from template:{}'.format(self.header)

    def __html__(self):
        'Attempting to construct from template: <a href=\"https://ftbwiki.org/index.php?action=edit&title={}&section={}\">{}</a>'.format(self.page_title, self.section_num, self.header)
    

def instantiate_recipe(page_title, log_node, output_item, header, grid, recipe_terms, section_num, modification):
    
    from_mod = output_item.mod
    if 'expert' in header.lower():
        from_mod = Mod.objects.get(name = 'Feed The Beast Infinity Evolved Expert Mode')
    elif not header == 'Recipe':
        try:
            from_mod = Mod.objects.get(abbreviations__contains = '|' + re.match(r'{{Mod[l|L]ink\|(\w+?)}}', header).group(1) +'|')
        except (Mod.DoesNotExist, AttributeError):
            pass

    dependencies = []
    if not modification == '':
        for match in re.findall(r'{{Mod[l|L]ink\|(\w+?)}}', modification, re.MULTILINE | re.DOTALL):
            dependencies.append(Mod.objects.get(abbreviations__contains = '|' + match + '|'))

    if grid == 'Crafting Table':
        inputs, output_info, byproducts = wp.getIO_crafting_recipe(recipe_terms)
        new_recipe = CraftingRecipe(output = output_item, amount = output_info['amount'], 
                        from_mod = from_mod)
    else:
        raise Exception('Cannot process machine recipes yet')

    return {
        'new_recipe' : new_recipe, 
        'parent_node' : log_node.add_node(Potential_Recipe(page_title, section_num, header)), 
        'inputs' : inputs, 
        'byproducts' : byproducts, 
        'dependencies' : dependencies,
    }


def parse_recipe(new_recipe, parent_node, inputs, byproducts, dependencies):
    
    db_item_objects = [ get_item_objects(input_info, parent_node) for input_info in inputs ]
    
    new_recipe.save()
    try:
        new_recipe.craftingrecipe
        for item_object, input_info in zip(db_item_objects, inputs):
            new_recipe.slotdata_set.create(slot = int(input_info['slot']), item_object = item_object)
    except Recipe.craftingrecipe.RelatedObjectDoesNotExist:
        try:
            Machine.objects.get(name = grid)
        except Machine.DoesNotExist:
            Machine.objects.create(name = grid)
    
    for mod in dependencies:
            new_recipe.dependencies.add(mod)

    #for byproduct in byproducts:
        #    new_recipe.byproduct_set.create(byproduct)
    parent_node.add_node(new_DB_entry(new_recipe))


