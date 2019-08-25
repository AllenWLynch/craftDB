import re
import requests
import json
from craftDB.models import Mod, Item, OreDict

#infobox_exp = re.complile(r'^{{Infobox/(?:(?:Block)|(?:Item)).+?\|(.+?)^}}')
parse_item_re = r'(.+?)(?: *\((.+)\))?$'

wiki_url = 'https://ftbwiki.org/'
api_endpoint = 'https://ftbwiki.org/api.php'

def parse_pagetitle(title):
    r = re.search(parse_item_re, title)
    assert(r), 'Failed to parse page title'
    return r


def get_wikitext(page_name):
    parse_params = {
        'action' : 'parse',
        'page' : page_name,
        'format': 'json',
        'prop' : 'wikitext'
    }
    r = requests.get(api_endpoint, parse_params)
    assert(r.status_code == 200), 'Page "' + pageName + '" does not exist'
    try:
        return json.loads(r.text)['parse']['wikitext']['*']
    except KeyError as err:
        raise Exception('This page does not contain wikitext')
    except Exception as err:
        raise Exception('An unexpected error occured while parsing wikidata.')


class NoIDException(Exception):
    pass

class NoInfoboxException(Exception):
    pass

class IncompletePageException(Exception):
    pass

class NoOreDictException(Exception):
    pass

def get_infobox(wikitext):
    infobox = re.search(r'^{{Infobox/(?:(?:Block)|(?:Item)).+?\|(.+?)^}}', wikitext, re.MULTILINE | re.DOTALL)
    assert(infobox), 'No infobox found on this page.'
    return infobox.group(1)

def scrape_infobox(wikitext):
    try:
        infobox = get_infobox(wikitext)
    except AssertionError:
        raise NoInfoboxException('Invalid Page Error')
    
    try:
        item_id = re.search(r'\|idname *= *([\w:\|\d\.]+?)\n', infobox.replace('{{!}}', '|')).group(1)
    except:
        raise NoIDException('This may contain information for multiple items (Oredict).')
    
    try:
        stack = re.search(r'\|stack *= *(\d{1,2})\n', infobox).group(1)
        mod = re.search(r'\|mod * = *(.+?)\n', infobox).group(1)
        display_name = re.search(r"'''([\w\|\s]+?)'''",wikitext).group(1)

        ore_search = re.search(r'\|oredict *= *([\w,;]+?)\n', infobox)
        oredict = ore_search.group(1).split(';') if ore_search else {}
        
    except Exception as err:
        raise IncompletePageException('Incomplete information on page.', err)
    else:
        return {
            'itemid' : item_id,
            'stack' : stack,
            'mod' : mod,
            'oredict': oredict,
            'display_name' : display_name,
        }

## implement
def get_oredict_field(wikitext):
    try:
        infobox = get_infobox(wikitext)
    except AssertionError:
        raise NoInfoboxException('Invalid Page Error')
    try:
        ore_search = re.search(r'\|oredict *= *([\w,;]+?)\n', infobox)
        oredict = ore_search.group(1).split(';') if ore_search else {}
    except:
        raise NoOreDictException('Incomplete information on page.')
    return oredict

class NoRecipesException(Exception):
    pass

def scrape_recipes(wikitext):
    try:
        return [ 
            {'header': 'Mod:' + re.match(r'{{ModLink\|(.+?)}}', section_name).group(1) if re.match(r'{{ModLink\|(.+?)}}', section_name) else section_name,
            'grid': grid_type, 'recipe_terms': recipe}
            for section_name, section in re.findall(r'==+ *(.+?) *==+\n(.+?)^(?===+)', wikitext, re.MULTILINE | re.DOTALL)
            for grid_type, recipe in re.findall(r'^{{Grid/(.+?)\n\|(.+?)}}$', section, re.MULTILINE | re.DOTALL)
        ]
    except:
        raise NoRecipesException('No recipes detected on this page.')
    
def getIO_crafting_recipe(recipe_text):
    inputs = []
    output = {'amount' : 1}
    slot_dict = {
        value : index + 1 for index, value in enumerate(str(letter) + str(num) for num in range(1,4) for letter in 'ABC')
    }
    for term in re.split(r' *\|', recipe_text.replace('\n','')):
        if re.match(r'[A-C][1-3] *= *.+', term):
            slot_code, title = re.search(r'([A-C][1-3]) *= *(.+)',term).groups()
            display_name, mod = re.search(parse_item_re, title).groups()
            inputs.append({'display_name' : display_name, 'mod' : mod, 'amount' : 1, 'slot' : slot_dict[slot_code], 'title' : title})
        elif re.match(r'Output *= *', term):
            output['display_name'], output['mod'] = re.search(r'Output *= *' + parse_item_re, term).groups()
            output['title'] = re.search(r'Output *= *(.+?)$', term).group(1)
        elif re.match(r'OA *= *', term):
            output['amount'] = re.search(r'OA *= *(\d+)', term).group(1)
    return inputs, [output]

def extract_machineing_recipe(recipe_text):
    pass

def scrape_oredict(dict_name):
    params = {
        'format' : 'json',
        'action' : 'ask',
        'query' : '[[Ore Dictionary name::{}]]|format=json|template=Itemref|link=none'.format(dict_name)
    }
    r = requests.get(api_endpoint, params)
    assert(r.status_code == 200), 'Page does not exist.'
    try:
        results = json.loads(r.text)['query']['results']
    except Exception as err:
        raise AssertionError('Page yielded unexpected results.', err)
    else:
        assert(len(results) > 0), 'OreDict {} does not exist'.format(dict_name)
        return results.keys()

