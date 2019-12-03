# craftDB -> Website for scraping, managing, and calculating recipes for modded Minecraft

## Web Scraping

See <i>wikiparser.py</i> for regex-based scraping of wikidata on recipes. Based on URL input, scrapes and formulates context, then instantiates a new recipe in the Django database.

## craftDB, the Database

Uses Django's built-in SQL api to store recipedata scraped from the wiki in relational format.

## Callable API

Call craftDB's API to generate information on how to build stored recipes in the most resource-efficient manner.
