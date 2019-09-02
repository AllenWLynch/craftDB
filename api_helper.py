import numpy as np
import pandas as pd
from collections import Counter, OrderedDict
from math import ceil
from craftDB.models import *

def key_format(key):
    if type(key) == int:
        return str(key)
    else:
        return '"{}"'.format(str(key))

def dict_to_lua(input):
    if type(input) in {float, int}:
        return str(input)
    elif type(input) == bool:
        return str(input).lower()
    elif type(input) == str:
        return '"{}"'.format(str(input))
    elif type(input) == dict:
        if len(input) == 0:
            return '{}'
        else:
            return '{' + ', '.join([ '[{}] = {}'.format(key_format(key), dict_to_lua(value)) for (key, value) in input.items()]) + '}'
    else:
        assert(False), "Cannot process " + str(type(input)) + " (datatypes other than dict of dict with literals)"

def convert_recipe_to_lua(recipe):
    translation_dict = {}
    translation_dict['output'] = recipe.output.itemid
    translation_dict['amount'] = recipe.amount
    translation_dict['display_name'] = str(recipe.output)
    translation_dict['by_products'] = {
        item : quantity for (item, quantity) in recipe.byproducts_set.all()
    }
    try:
        sub_object = recipe.craftingrecipe
        translation_dict['is_crafted'] = True
        translation_dict['slotdata'] = {
            index : {'itemid' : slotdata.item.itemid, 'amount' : 1, 'slot' : slotdata.slot}
            for index, slotdata in enumerate(sub_object.slotdata_set.all())
        }
        translation_dict['required_resources'] = dict(sub_object.required_resources())
        translation_dict['min_stack'] = sub_object.min_stack()
        return dict_to_lua(translation_dict)
    except recipe.craftingrecipe.RelatedObjectDoesNotExist:
        try:
            sub_object = recipe.machinerecipe
            # implement this
        except recipe.machinerecipe.RelatedObjectDoesNotExist:
            raise AssertionError('Recipe is neither crafting nor machining type')

#revamped: YES
def instructions(request):
    if not request.method == 'GET':
        print('Request for instructions did not include GET method')
        return HttpResponse(status = 400)
        
    try:
        if not 'HTTP_INVENTORY' in request.META:
            inventory = Counter()
        else:
            inventory = Counter(json.loads(request.META['HTTP_INVENTORY']))
        
        if not 'HTTP_MACHINES' in request.META:
            machines = set()
        else:
            machines = set([machine_name for color, machine_name in json.loads(request.META['HTTP_MACHINES']).items()])
            
        recurse_item = get_object_or_404(Item, display_name = request.GET['for'])
        inventory[recurse_item.item_id] = 0
        tree_summary = Item_Node(recurse_item, int(request.GET['quantity']), inventory, set(), machines)
    except:
        return HttpResponse(status == 500)
    #write methods for tree_summary printing
    return HttpResponse(tree_summary.lua_output(), content_type = 'text/plain')


class OrderedCounter(Counter, OrderedDict):
     #'Counter that remembers the order elements are first encountered'
     def __repr__(self):
         return '%s(%r)' % (self.__class__.__name__, OrderedDict(self))

     def __reduce__(self):
         return self.__class__, (OrderedDict(self),)

     def __str__(self):
         return '{' + ', '.join(['{}: {}'.format(key,value) for key, value in self.items()]) + '}'


def Item_Node(item, order_quantity, available_resources = Counter(), parent_set = set(), machines = set()):
    
    #print('Enter name node: ', search_name)
    # define an order for this name node
    order = Craft_Order()
    parent_set.add(item.itemid)
    # if there is this stuff in the inventory, subtract
    recipe_options = item.recipe_set.all()

    if available_resources[item.itemid] >= order_quantity:
        available_resources[item.itemid] -= order_quantity
        order.used_resources[item.itemid] += order_quantity
        return order
    else:
        # else decrement the order quanitity and continue
        num_availabe = available_resources[item.itemid]
        if len(recipe_options) == 0:
            order.missing_resources[item.itemid] += order_quantity - num_availabe
            order.is_leaf = True
            order.used_resources = Counter()
            return order
        else:
            order.used_resources[item.itemid] += num_availabe
            available_resources[item.itemid] = 0
            order_quantity -= num_availabe

    # else add leaves 
    children = [
        Recipe_Node(recipe, order_quantity, available_resources.copy(),parent_set.copy(), machines)
        for recipe in recipe_options
    ]
   
    score_columns = ['machines_attached', 'missing_resources','used_resources','num_steps']
    #print(*[craftorder.score() for craftorder in children])
    score_df = pd.DataFrame([craftorder.score() for craftorder in children], columns = score_columns)
    score_df.sort_values(score_columns, inplace = True)

    #print(str(score_df))
    best_recipe_path = children[score_df.iloc[0].name]

    if not best_recipe_path.can_craft() and item.base_resource:
        order.missing_resources[item.itemid] += order_quantity
        order.is_leaf = True
        order.used_resources = Counter()
        return order
        
    return Craft_Order.union([best_recipe_path, order])

# gotta fix this up to include: new datatypes allowances, base_resource stuff, ore_dict allowances?
def Recipe_Node(recipe, order_quantity, available_resources, parent_set, machines):

    #print('Enter recipe node: ', recipe_name)
    #print(parent_set)
    # instantiate a craftorder for this recipe
    this_order = Craft_Order()
    # query to obtain recipe

    required_resources = recipe.required_resources()
        
    #if no recipe, add to missing
    if len(required_resources) == 0:
        this_order.missing_resources[recipe.recipe_name.itemid] = order_quantity
        return this_order
    
    #recipe = pd.DataFrame(db_recipe_data, columns = ['slot','item','quantity'])
    
    # check for cycles
    if len(parent_set & set(required_resources.keys())) > 0:
        #print('recipe name: ', recipe_name)
        #print(*zip(recipe['item'].values, [parent_name in parent_set for parent_name in recipe['item'].values]))
        this_order.missing_resources[recipe.output.itemid] = order_quantity
        return this_order

    # adjust for makes, stuff like that
    num_operations_required = ceil(order_quantity / recipe.amount)
    # for each component, grouped:
    children = []
    #for (component_name, num_required) in recipe[['item','quantity']].groupby('item').sum().iterrows():
    for itemid, amount in required_resources:
        # new node for every component type
        subtree_order = Item_Node(Item.objects.get(itemid = itemid), amount * num_operations_required, available_resources.copy(), parent_set)
        # subtract used resources from the pool of available resources
        available_resources -= subtree_order.used_resources
        # add the child node
        children.append(subtree_order)
    
    # consolidate the craftorders with this order
    this_order = Craft_Order.union([*children, this_order])

    # if this crafting is successful, add a step, if not
    if this_order.can_craft():
        # compensate for overflow
        overflow = (recipe.amount * num_operations_required) - order_quantity
        this_order.used_resources[recipe.recipe_name.itemid] = -1 * overflow
        # add the step
        this_order.add_step(recipe.id, num_operations_required)
        #this_order.has_all_machines = recipe.machine_with.name == 'Crafter' or len(set(recipe.machine_with.all_possible_machines()) & machines) > 0
        try:
            recipe.craftingrecipe
        except Recipe.craftingrecipe.RelatedObjectDoesNotExist:
            this_order.has_all_machines = len(set(recipe.machine.all_possible_machines()) & machines) > 0
        else:
            this_order.has_all_machines = True
            
    return this_order

class Craft_Order:
    def __init__(self):
        self.used_resources = Counter()
        self.missing_resources = Counter()
        self.queue = OrderedCounter()
        self.is_leaf = True
        self.has_all_machines = True

    def add_step(self, execute_id, quantity):
        self.queue[execute_id] += quantity
        self.is_leaf = False
    
    @staticmethod
    def union(orders):
        sum_order = Craft_Order()
        for order in orders:
            sum_order.used_resources += order.used_resources
            sum_order.missing_resources += order.missing_resources
            sum_order.queue += order.queue
            sum_order.has_all_machines = sum_order.has_all_machines & order.has_all_machines
        return sum_order

    def can_craft(self):
        return sum(self.missing_resources.values()) == 0
    
    def get_summary(self):
        return self.queue

    def score(self):
        return (not self.has_all_machines, sum(self.missing_resources.values()),sum(self.used_resources.values()), len(self.queue))

    # implement!
    def lua_output(self):
        output_dict = {
            'missing_resouces': {
                Item.objects.get(item_id = item_rawname).display_name : quantity for (item_rawname, quantity) in self.missing_resources.items()
            },
            'craft_queue' : {
                i + 1 : {'id' : recipe_id, 'quantity' : self.queue[recipe_id], 'name' : Recipe.objects.get(pk = recipe_id).recipe_name.item_id} for i, recipe_id in enumerate(self.queue)
            },
            'resources_used': dict(self.used_resources),
        }
        return dict_to_lua(output_dict)

    def __str__(self):
        new_dict = {
            str(key) : val for (key,val) in self.queue.items()
        }
        return counter_pretty_print(new_dict, 'Queue') +'\n' + counter_pretty_print(self.used_resources,'Used') + '\n' + counter_pretty_print(self.missing_resources, 'Missing')