import re
import requests
import json
from craftDB.models import Mod, Item, OreDict
from django.urls import reverse

#infobox_exp = re.complile(r'^{{Infobox/(?:(?:Block)|(?:Item)).+?\|(.+?)^}}')
parse_item_re = r'(.+?)(?: *\((.+)\))?$'
wiki_url = 'https://ftbwiki.org/'
api_endpoint = 'https://ftbwiki.org/api.php'

def parse_pagetitle(title):
    r = re.search(parse_item_re, title)
    assert(r), 'Failed to parse page title'
    return r.groups()


class BadItemPageException(Exception):
    def __init__(self, value, start_sublist = False, end_sublist = False):
        self.value = value
        self.start_sublist = start_sublist
        self.end_sublist = end_sublist

    def __str__(self):
        return str(self.value)

class NoInfoboxException(BadItemPageException):
    pass 

class IncompletePageException(BadItemPageException):
    def __init__(self, page_title, scraped_data, start_sublist = False, end_sublist = False):
        self.page_title = page_title
        self.start_sublist = start_sublist
        self.end_sublist = end_sublist
        self.scraped_data = scraped_data

    def __str__(self):
        create_item_url = reverse('admin:craftDB_item_add', current_app='craftadmin') + '?' + '&'.join([str(key) + '=' + str(value) for key, value in self.scraped_data.items()])
        return '{0}Page: <a href=\"{1}\" target="_blank">{2}</a> contained incomplete data for item record <a href=\"{3}\" target="_blank">(Create Manually)</a>{4}'.format(
        '<ul>' if self.start_sublist else '',
        'https://ftbwiki.org/{}'.format(self.page_title), 
        self.page_title,
        create_item_url,
        '</ul>' if self.end_sublist else '')

class NoWikiTextException(BadItemPageException):
    pass

class NoRecipesException(Exception):
    pass

def get_wikitext(page_name):
    parse_params = {
        'action' : 'parse',
        'page' : page_name,
        'format': 'json',
        'prop' : 'wikitext'
    }
    r = requests.get(api_endpoint, parse_params)
    assert(r.status_code == 200), 'Page "' + pageName + '" does not exist'
    return json.loads(r.text)['parse']['wikitext']['*']
    

class PageParser():

    def __init__(self, page_name):
        self.page_name = page_name
        try:
            self.content = get_wikitext(page_name)
        except KeyError:
            raise NoWikiTextException('This page: {} does not contain wikitext'.format(page_name))
        #except HTTP error:

    def scrape_infobox(self):

        infobox_search = re.search(r'^{{Infobox/(?:(?:Block)|(?:Item)).+?\|(.+?)^}}', self.content, re.MULTILINE | re.DOTALL)
        if not infobox_search:
            raise NoInfoboxException('Page: {} does not contain wikitext defining item'.format(self.page_name))
        infobox = infobox_search.group(1)
        
        fields = {}

        try:
            fields['itemid'] = re.search(r'\|idname *= *([\w:\|\d\.]+?)\n', infobox.replace('{{!}}', '|')).group(1)
        except:
            pass
        
        try:
            fields['stack'] = re.search(r'\|stack *= *(\d{1,2})\n', infobox).group(1)
        except:
            pass
        
        try:
            fields['mod'] = re.search(r'\|mod * = *(.+?)\n', infobox).group(1)
        except: pass

        try:
            display_name = re.search(r"'''(.+?)'''",self.content).group(1)
            if display_name == '{{PAGENAME}}':
                fields['display_name'] = self.page_name
            else:
                fields['display_name'] = display_name
        except: pass

        #ore_search = re.search(r'\|oredict *= *([\w,;]+?)\n', infobox)
        #fields['oredict'] = ore_search.group(1).split(';') if ore_search else {}
            
        return fields
    
    def scrape_recipes(self):
        try:
            recipes = []
            section_num = 1
            for section_name, section in re.findall(r'==+ *(.+?) *==+\n(.+?)^(?===+)', self.content, re.MULTILINE | re.DOTALL):
                for grid_type, recipe in re.findall(r'^{{Grid/(.+?)\n\|(.+?)}}$', section, re.MULTILINE | re.DOTALL):
                    recipes.append({'header': 'Mod:' + re.match(r'{{ModLink\|(.+?)}}', section_name).group(1) if re.match(r'{{ModLink\|(.+?)}}', section_name) else section_name,
                    'grid': grid_type, 'recipe_terms': recipe, 'section_num' : section_num})
                section_num += 1
            return recipes
        except:
            raise NoRecipesException('Page: {} does not contain recipes'.format(self.page_name))

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
            inputs.append({'display_name' : display_name, 'mod' : mod, 'amount' : 1, 'slot' : slot_dict[slot_code], 'page_title' : title})
        elif re.match(r'Output *= *', term):
            output['display_name'], output['mod'] = re.search(r'Output *= *' + parse_item_re, term).groups()
            output['page_title'] = re.search(r'Output *= *(.+?)$', term).group(1)
        elif re.match(r'OA *= *', term):
            output['amount'] = re.search(r'OA *= *(\d+)', term).group(1)
    return inputs, output, []

def extract_machineing_recipe(recipe_text):
    pass

class NoOreDictException(Exception):
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
    except KeyError:
        raise NoOreDictException('OreDict {} is not defined'.format(dict_name))
    else:
        if len(results) == 0:
            raise NoOreDictException('OreDict {} contains no items'.format(dict_name))
        return results.keys()

