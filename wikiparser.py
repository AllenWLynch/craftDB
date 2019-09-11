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

class Log_Node():

    def __init__(self, value):
        self.value = value
        self.children = []
    
    def render_as_html(self):
        try:
            return '<li>{}</li>'.format(self.value.__html__())
        except AttributeError:
            return '<li>{}</li>'.format(str(self.value))
    
    def has_children(self):
        return len(self.children) > 0

    def recurse_log(self, to_level, counter = 0):
        if counter == to_level:
            return self
        else:
            assert(self.has_children()),' Level {} does not exist'.format(to_level)
            return self.children[-1].recurse_log(to_level, counter + 1)
    
    def add_node(self, value, level = 1):
        assert(level > 0), 'Cannot add to level 0 of Log_Node'
        parent_node = self.recurse_log(level - 1)
        new_node = Log_Node(value)
        parent_node.children.append(new_node)
        return new_node   

    def connect_nodes(self, other_node, level):
        assert(level > 0), 'Cannot add to level 0 of Log_Node'
        parent_node = self.recurse_log(level - 1)
        parent_node.children.append(other_node)

    def set(self, value):
        self.value = value      

    def get_last_level(self, counter = 0):
        if self.has_children():
            return self.children[-1].get_last_level(counter + 1)
        else:
            return counter

    def render_html(self, counter = 0):
        try:
            render_str = '\n' + '\t' * counter + '<li>{}</li>'.format(self.value.__html__())
        except AttributeError:
            render_str = '\n' + '\t' * counter + '<li>{}</li>'.format(str(self.value))

        if self.has_children():
            render_str += ('<ul>')
            for child in self.children:
                render_str += child.render_html(counter + 1)
            render_str += '</ul>'

        return render_str


    def render_string(self, counter = 0):
        render_str = '\n' + '\t' * counter + '* ' + str(self.value)
        for child in self.children:
            render_str += child.render_string(counter + 1)
        
        return render_str


    def render(self, format = 'string'):
        if format == 'string':
            return self.render_string()
        elif format == 'html':
            return self.render_html()
        raise AssertionError('Render format must be "string" or "html"')

class BadItemPageException(Exception):
    def __init__(self, value):
        self.value = value
        self.children = []

    def __str__(self):
        return str(self.value)

    def __html__(self):
        return str(self)

class NoInfoboxException(BadItemPageException):
    pass 

class IncompletePageException(BadItemPageException):
    def __init__(self, page_title, scraped_data):
        self.page_title = page_title
        self.children = []
        self.scraped_data = scraped_data
        self.create_item_url = reverse('admin:craftDB_item_add', current_app='craftadmin') + '?' + '&'.join([str(key) + '=' + str(value) for key, value in scraped_data.items()])
    
    def __html__(self):
        return 'Page: <a href=\"{0}\" target="_blank">{1}</a> contained incomplete data for item record <a href=\"{2}\" target="_blank">(Create Manually)</a>'.format(
        'https://ftbwiki.org/{}'.format(self.page_title), 
        self.page_title,
        self.create_item_url)

    def __str__(self):
        return 'Page: {} contained incomplete data for item record.'.format(self.page_title)

class NoWikiTextException(BadItemPageException):
    pass

class NoRecipesException(Exception):
    pass

class NoImageException(Exception):
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
        self.item_type = None
        try:
            self.content = get_wikitext(page_name)
        except KeyError:
            raise NoWikiTextException('This page: {} does not contain wikitext'.format(page_name))
        #except HTTP error:

    def scrape_infobox(self):

        infobox_search = re.search(r'^{{Infobox/((?:Block)|(?:Item))\n\|(.+?)^}}', self.content, re.MULTILINE | re.DOTALL)
        if not infobox_search:
            raise NoInfoboxException('Page: {} does not contain wikitext defining item'.format(self.page_name))
        item_type, infobox = infobox_search.groups()
        
        fields = {}
        
        self.item_type = item_type

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
                for modification, grid_type, recipe in re.findall(r'(?:^\*\+({{ModLink\|.+?}}\n))?^{{Grid/(.+?)\n\|(.+?)}}$', section, re.MULTILINE | re.DOTALL):
                    recipes.append({'header': section_name,
                                    'grid': grid_type, 
                                    'recipe_terms': recipe, 
                                    'section_num' : section_num, 
                                    'modification' : modification})
                section_num += 1
            return recipes
        except:
            raise NoRecipesException('Page: {} does not contain recipes'.format(self.page_name))

    def get_main_image(self):
        
        assert(self.item_type), 'Must scrape infobox before getting image so that page Item/Block type is assigned'
        find_image_titled = 'File:{}_{}.png'.format(self.item_type, self.page_name).replace(' ', '_')
        #print(find_image_titled)
        response = requests.get('https://ftbwiki.org/api.php?action=query&format=json&prop=imageinfo&titles={}&iiprop=url'.format(find_image_titled))
        try:
            raw_url = re.search(r'\[\{\"url\":\"(.+?)\"',response.text).group(1)
        except Exception:
            raise NoImageException('Page: {} contains no images'.format(self.page_name))
        
        return find_image_titled, raw_url
        

def getIO_crafting_recipe(recipe_text):
    inputs = {}
    output = {'amount' : 1}
    slot_dict = {
        value : index + 1 for index, value in enumerate(str(letter) + str(num) for num in range(1,4) for letter in 'ABC')
    }
    for term in re.split(r' *\|', recipe_text.replace('\n','')):
        if re.match(r'[A-C][1-3] *= *.+', term):
            slot_code, title = re.search(r'([A-C][1-3]) *= *(.+)',term).groups()
            display_name, mod = re.search(parse_item_re, title).groups()
            if slot_code in inputs:
                inputs[slot_code]['display_name'] = display_name
                inputs[slot_code]['mod'] = mod
            else:
                inputs[slot_code] = {'display_name' : display_name, 'mod' : mod, 'amount' : 1, 'slot' : slot_dict[slot_code], 'page_title' : title}
        elif re.match(r'Output *= *', term):
            output['display_name'], output['mod'] = re.search(r'Output *= *' + parse_item_re, term).groups()
            output['page_title'] = re.search(r'Output *= *(.+?)$', term).group(1)
        elif re.match(r'OA *= *', term):
            output['amount'] = re.search(r'OA *= *(\d+)', term).group(1)
        elif re.match(r'[A-C][1-3]-dict *= *', term):
            slot_code, title = re.search(r'([A-C][1-3])-dict *= *(.+)',term).groups()
            if slot_code in inputs:
                inputs[slot_code]['oredict'] = title
            else:
                inputs[slot_code] = {'oredict': title, 'amount' : 1, 'slot' : slot_dict[slot_code], 'page_title' : title}

    return inputs.values(), output, []

def extract_machining_recipe(recipe_text):
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

