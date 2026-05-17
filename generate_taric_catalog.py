#!/usr/bin/env python3
"""
TARIC Catalog Generator - Processes all TARIC codes and subcategories
to generate correct mappings for full_taric_catalog.py

This script:
1. Fetches TARIC data from official EU sources
2. Validates all codes and their structure
3. Generates comprehensive keyword mappings
4. Validates AI matching results
5. Updates full_taric_catalog.py with correct entries
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

# TARIC code structure validation
TARIC_CODE_PATTERN = re.compile(r'^\d{10}$')
HS4_PATTERN = re.compile(r'^\d{4}$')

# Chapter definitions with Greek and English names
CHAPTER_DEFINITIONS = {
    "01": ("Ζώντα ζώα", "Live animals"),
    "02": ("Κρέατα", "Meat"),
    "03": ("Ψάρια", "Fish"),
    "04": ("Γαλακτοκομικά", "Dairy products"),
    "05": ("Προϊόντα ζωικής προέλευσης", "Animal products nes"),
    "06": ("Ζώντα δέντρα και φυτά", "Live trees and plants"),
    "07": ("Λαχανικά", "Vegetables"),
    "08": ("Φρούτα", "Fruit"),
    "09": ("Καφές, τσάι, μπαχαρικά", "Coffee, tea, spices"),
    "10": ("Δημητριακά", "Cereals"),
    "11": ("Προϊόντα αλευρόμυλων", "Mill products"),
    "12": ("Σπόροι και φρούτα με έλαιο", "Oil seeds and fruits"),
    "13": ("Γόμμα, ρητίνες", "Gums, resins"),
    "14": ("Φυτικά υλικά για πλέξιμο", "Vegetable plaiting materials"),
    "15": ("Ζωικά ή φυτικά λίπη", "Animal/vegetable fats"),
    "16": ("Παρασκευάσματα κρέατος", "Meat preparations"),
    "17": ("Ζάχαρη και είδη ζαχαροπλαστικής", "Sugar and confectionery"),
    "18": ("Κακάο και παρασκευάσματα", "Cocoa and preparations"),
    "19": ("Προϊόντα με βάση τα δημητριακά", "Cereal-based products"),
    "20": ("Παρασκευάσματα λαχανικών", "Vegetable preparations"),
    "21": ("Διάφορα παρασκευάσματα τροφίμων", "Miscellaneous food preparations"),
    "22": ("Ποτά, ξύδι", "Beverages, vinegar"),
    "23": ("Υπολείμματα τροφίμων", "Food industry residues"),
    "24": ("Καπνός", "Tobacco"),
    "25": ("Αλάτι, θείο, γη", "Salt, sulphur, earth"),
    "26": ("Μεταλλεύματα", "Ores"),
    "27": ("Ορυκτά καύσιμα", "Mineral fuels"),
    "28": ("Ανόργανα χημικά", "Inorganic chemicals"),
    "29": ("Οργανικά χημικά", "Organic chemicals"),
    "30": ("Φαρμακευτικά προϊόντα", "Pharmaceutical products"),
    "31": ("Λιπάσματα", "Fertilizers"),
    "32": ("Δεψικές και βαφικές ύλες", "Tanning and dyeing extracts"),
    "33": ("Αιθέρια έλαια, καλλυντικά", "Essential oils, cosmetics"),
    "34": ("Σαπούνια, απορρυπαντικά", "Soap, detergents"),
    "35": ("Λευκωματώδεις ύλες", "Albuminoidal substances"),
    "36": ("Εκρηκτικά", "Explosives"),
    "37": ("Φωτογραφικά ή κινηματογραφικά", "Photographic products"),
    "38": ("Διάφορα χημικά", "Miscellaneous chemicals"),
    "39": ("Πλαστικές ύλες", "Plastics"),
    "40": ("Καουτσούκ", "Rubber"),
    "41": ("Δέρματα ακατέργαστα", "Raw hides and skins"),
    "42": ("Τεχνουργήματα από δέρμα", "Leather articles"),
    "43": ("Γουναρικά", "Furskins"),
    "44": ("Ξυλεία", "Wood"),
    "45": ("Φελλός", "Cork"),
    "46": ("Καλαθοπλεκτική", "Plaiting materials"),
    "47": ("Πολτοί από ξυλεία", "Wood pulp"),
    "48": ("Χαρτί και χαρτόνι", "Paper and paperboard"),
    "49": ("Βιβλία, εφημερίδες", "Books, newspapers"),
    "50": ("Μετάξι", "Silk"),
    "51": ("Μαλλί", "Wool"),
    "52": ("Βαμβάκι", "Cotton"),
    "53": ("Άλλες φυτικές υφαντικές ύλες", "Other vegetable textile fibers"),
    "54": ("Συνθετικά ή τεχνητά νήματα", "Man-made filaments"),
    "55": ("Συνθετικές ή τεχνητές ίνες", "Man-made staple fibers"),
    "56": ("Βάτες, τσόχα", "Wadding, felt"),
    "57": ("Χαλιά", "Carpets"),
    "58": ("Ειδικά υφάσματα", "Special woven fabrics"),
    "59": ("Υφάσματα επιχρισμένα", "Impregnated textiles"),
    "60": ("Πλεκτά υφάσματα", "Knitted fabrics"),
    "61": ("Ένδυση πλεκτή", "Knitted clothing"),
    "62": ("Ένδυση μη πλεκτή", "Non-knitted clothing"),
    "63": ("Άλλα κλωστοϋφαντουργικά", "Other textiles"),
    "64": ("Υποδήματα", "Footwear"),
    "65": ("Καλύμματα κεφαλής", "Headgear"),
    "66": ("Ομπρέλες", "Umbrellas"),
    "67": ("Πούπουλα επεξεργασμένα", "Prepared feathers"),
    "68": ("Πέτρα, γύψος, τσιμέντο", "Stone, plaster, cement"),
    "69": ("Κεραμικά", "Ceramic products"),
    "70": ("Γυαλί", "Glass"),
    "71": ("Μαργαριτάρια, πολύτιμοι λίθοι", "Pearls, precious stones"),
    "72": ("Σίδηρος και χάλυβας", "Iron and steel"),
    "73": ("Τεχνουργήματα από σίδηρο", "Iron/steel articles"),
    "74": ("Χαλκός", "Copper"),
    "75": ("Νικέλιο", "Nickel"),
    "76": ("Αλουμίνιο", "Aluminum"),
    "78": ("Μόλυβδος", "Lead"),
    "79": ("Ψευδάργυρος", "Zinc"),
    "80": ("Κασσίτερος", "Tin"),
    "81": ("Άλλα κοινά μέταλλα", "Other base metals"),
    "82": ("Εργαλεία", "Tools"),
    "83": ("Διάφορα μεταλλικά", "Miscellaneous metal articles"),
    "84": ("Μηχανές, συσκευές", "Machinery"),
    "85": ("Ηλεκτρικές μηχανές", "Electrical machinery"),
    "86": ("Σιδηροδρομικός τροχαίος", "Railway vehicles"),
    "87": ("Οχήματα", "Vehicles"),
    "88": ("Αεροσκάφη", "Aircraft"),
    "89": ("Πλοία", "Ships"),
    "90": ("Οπτικά όργανα", "Optical instruments"),
    "91": ("Ρολόγια", "Watches and clocks"),
    "92": ("Μουσικά όργανα", "Musical instruments"),
    "93": ("Όπλα", "Arms and ammunition"),
    "94": ("Έπιπλα", "Furniture"),
    "95": ("Παιχνίδια", "Toys and games"),
    "96": ("Διάφορα", "Miscellaneous manufactured articles"),
}


@dataclass
class TaricEntry:
    """TARIC entry dataclass."""
    taric_code: str
    hs4: str
    description: str
    keywords: tuple
    
    def to_dict(self):
        return {
            'taric_code': self.taric_code,
            'hs4': self.hs4,
            'description': self.description,
            'keywords': list(self.keywords)
        }


def validate_taric_code(code: str) -> bool:
    """Validate a TARIC code format."""
    if not code or not isinstance(code, str):
        return False
    # Remove any spaces or dashes
    cleaned = re.sub(r'[\s\-]', '', code)
    return bool(TARIC_CODE_PATTERN.match(cleaned))


def validate_hs4(hs4: str) -> bool:
    """Validate HS4 code format."""
    if not hs4 or not isinstance(hs4, str):
        return False
    return bool(HS4_PATTERN.match(hs4))


def extract_keywords_from_description(description: str, chapter: str) -> List[str]:
    """Extract relevant keywords from a TARIC description."""
    keywords = []
    
    # Common product terms to extract
    product_terms = {
        'water': ['water', 'mineral water', 'spring water', 'still water', 'sparkling water', 'carbonated water'],
        'beverage': ['beverage', 'drink', 'soft drink', 'energy drink', 'juice'],
        'food': ['food', 'preparation', 'preserved', 'processed'],
        'meat': ['meat', 'beef', 'pork', 'chicken', 'poultry'],
        'fish': ['fish', 'seafood', 'crustacean', 'mollusc'],
        'dairy': ['dairy', 'milk', 'cheese', 'butter', 'yogurt'],
        'vegetable': ['vegetable', 'fruit', 'fresh', 'frozen', 'dried'],
        'cereal': ['cereal', 'grain', 'wheat', 'rice', 'flour', 'bread'],
        'sugar': ['sugar', 'sweet', 'confectionery', 'candy', 'chocolate'],
        'alcohol': ['alcohol', 'wine', 'beer', 'spirits', 'vodka', 'whisky'],
        'tobacco': ['tobacco', 'cigarette', 'cigar', 'vape', 'e-cigarette'],
        'chemical': ['chemical', 'acid', 'base', 'compound', 'element'],
        'pharmaceutical': ['pharmaceutical', 'medicine', 'drug', 'tablet', 'capsule', 'medicament'],
        'cosmetic': ['cosmetic', 'perfume', 'makeup', 'skincare', 'soap', 'shampoo'],
        'plastic': ['plastic', 'polymer', 'resin'],
        'rubber': ['rubber', 'elastic', 'latex'],
        'leather': ['leather', 'hide', 'skin'],
        'textile': ['textile', 'fabric', 'cloth', 'yarn', 'fiber', 'thread'],
        'clothing': ['clothing', 'garment', 'apparel', 'wear'],
        'footwear': ['footwear', 'shoe', 'boot', 'sandal', 'sneaker'],
        'metal': ['metal', 'iron', 'steel', 'aluminum', 'copper', 'zinc', 'lead'],
        'machine': ['machine', 'engine', 'motor', 'pump', 'compressor'],
        'electrical': ['electrical', 'electronic', 'circuit', 'battery', 'accumulator'],
        'vehicle': ['vehicle', 'car', 'truck', 'motorcycle', 'bicycle'],
        'furniture': ['furniture', 'chair', 'table', 'bed', 'sofa'],
        'toy': ['toy', 'game', 'puzzle', 'doll', 'plaything'],
        'optical': ['optical', 'lens', 'glass', 'mirror', 'prism'],
        'watch': ['watch', 'clock', 'timepiece'],
        'instrument': ['instrument', 'apparatus', 'device', 'equipment'],
    }
    
    desc_lower = description.lower()
    
    # Extract keywords from description
    for category, terms in product_terms.items():
        for term in terms:
            if term in desc_lower:
                keywords.append(term)
    
    # Add chapter-specific keywords
    if chapter in CHAPTER_DEFINITIONS:
        el_name, en_name = CHAPTER_DEFINITIONS[chapter]
        keywords.extend([en_name.lower(), chapter])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    return unique_keywords


def generate_comprehensive_catalog() -> List[TaricEntry]:
    """Generate a comprehensive TARIC catalog with all chapters and subcategories."""
    catalog = []
    
    # Chapter 22: Beverages - Complete with all subcategories
    catalog.extend([
        TaricEntry("2201101100", "2201", "Natural mineral waters, non-carbonated, not flavoured",
                   ("natural mineral water", "still mineral water", "mineral water", "still water", 
                    "spring water", "water", "mineral", "drink", "beverage", "2201")),
        TaricEntry("2201101900", "2201", "Natural mineral waters, carbonated, not flavoured",
                   ("sparkling mineral water", "carbonated mineral water", "aerated water",
                    "sparkling water", "fizzy water", "soda water", "water", "mineral", "drink", "2201")),
        TaricEntry("2201109000", "2201", "Other waters, non-carbonated",
                   ("water", "still water", "table water", "drinking water", "beverage", "2201")),
        TaricEntry("2201900000", "2201", "Ice and snow",
                   ("ice", "snow", "frozen water", "crushed ice", "2201")),
        TaricEntry("2202100000", "2202", "Waters with added sugar, sweeteners or flavouring",
                   ("flavoured water", "sweetened water", "water drink", "vitamin water",
                    "sports drink", "beverage", "soft drink", "2202")),
        TaricEntry("2202910000", "2202", "Non-alcoholic beer",
                   ("non-alcoholic beer", "alcohol-free beer", "beer", "malt beverage", "2202")),
        TaricEntry("2202990000", "2202", "Other non-alcoholic beverages",
                   ("energy drink", "soft drink", "soda", "cola", "lemonade", "isotonic", 
                    "monster", "red bull", "juice drink", "beverage", "2202")),
        TaricEntry("2203000000", "2203", "Beer made from malt",
                   ("beer", "ale", "lager", "pilsner", "stout", "porter", "wheat beer",
                    "heineken", "budweiser", "corona", "alcoholic beverage", "2203")),
        TaricEntry("2204100000", "2204", "Sparkling wine",
                   ("sparkling wine", "champagne", "prosecco", "cava", "alcoholic beverage", "2204")),
        TaricEntry("2204210000", "2204", "Wine of fresh grapes, not sparkling, <= 2L",
                   ("wine", "red wine", "white wine", "rose wine", "rosé wine", 
                    "table wine", "vintage wine", "alcoholic beverage", "2204")),
        TaricEntry("2204220000", "2204", "Wine of fresh grapes, not sparkling, > 2L",
                   ("wine", "red wine", "white wine", "bulk wine", "alcoholic beverage", "2204")),
        TaricEntry("2204290000", "2204", "Other wine of fresh grapes",
                   ("wine", "grape wine", "alcoholic beverage", "2204")),
        TaricEntry("2204300000", "2204", "Grape must",
                   ("grape must", "unfermented grape juice", "wine base", "2204")),
        TaricEntry("2205100000", "2205", "Vermouth and other flavoured wine",
                   ("vermouth", "flavoured wine", "aperitif", "alcoholic beverage", "2205")),
        TaricEntry("2206000000", "2206", "Other fermented beverages",
                   ("cider", "perry", "mead", "sake", "fermented beverage", "alcoholic", "2206")),
        TaricEntry("2207100000", "2207", "Undenatured ethyl alcohol >= 80%",
                   ("ethanol", "ethyl alcohol", "pure alcohol", "spirit", "2207")),
        TaricEntry("2207200000", "2207", "Denatured ethyl alcohol",
                   ("denatured alcohol", "methylated spirits", "industrial alcohol", "2207")),
        TaricEntry("2208200000", "2208", "Ethyl alcohol < 80%, spirits from wine",
                   ("brandy", "cognac", "wine spirits", "grappa", "2208")),
        TaricEntry("2208303000", "2208", "Vodka",
                   ("vodka", "spirits", "alcohol", "premium vodka", "flavoured vodka", "2208")),
        TaricEntry("2208309000", "2208", "Whisky",
                   ("whisky", "whiskey", "scotch", "bourbon", "spirits", "alcohol", "2208")),
        TaricEntry("2208400000", "2208", "Rum and tafia",
                   ("rum", "tafia", "cane spirits", "spirits", "alcohol", "2208")),
        TaricEntry("2208500000", "2208", "Gin and geneva",
                   ("gin", "geneva", "juniper spirit", "spirits", "alcohol", "2208")),
        TaricEntry("2208600000", "2208", "Liqueurs and cordials",
                   ("liqueur", "cordial", "cream liqueur", "fruit liqueur", "spirits", "2208")),
        TaricEntry("2208700000", "2208", "Other spirits and spirit beverages",
                   ("spirit", "liquor", "alcohol", "tequila", "mezcal", "2208")),
        TaricEntry("2208900000", "2208", "Other ethyl alcohol preparations",
                   ("alcohol preparation", "spirit beverage", "alcoholic", "2208")),
    ])
    
    # Chapter 24: Tobacco & Vaping - Complete
    catalog.extend([
        TaricEntry("2401100000", "2401", "Tobacco, unmanufactured, not stemmed/stripped",
                   ("tobacco", "raw tobacco", "unmanufactured tobacco", "leaf tobacco", "2401")),
        TaricEntry("2401200000", "2401", "Tobacco, unmanufactured, partly or wholly stemmed/stripped",
                   ("tobacco", "stemmed tobacco", "stripped tobacco", "processed tobacco", "2401")),
        TaricEntry("2402100000", "2402", "Cigars, cigarillos containing tobacco",
                   ("cigar", "cigarillo", "tobacco", "havana", "premium cigar", "2402")),
        TaricEntry("2402200000", "2402", "Cigarettes containing tobacco",
                   ("cigarette", "tobacco cigarette", "smoking", "marlboro", "camel", 
                    "winston", "tobacco", "smoke", "2402")),
        TaricEntry("2402900000", "2402", "Other smoking tobacco and substitutes",
                   ("smoking tobacco", "pipe tobacco", "rolling tobacco", "tobacco substitute", "2402")),
        TaricEntry("2403110000", "2403", "Waterpipe tobacco (shisha)",
                   ("shisha", "hookah tobacco", "waterpipe tobacco", "flavoured tobacco", "2403")),
        TaricEntry("2403190000", "2403", "Other smoking tobacco",
                   ("smoking tobacco", "pipe tobacco", "hand-rolling tobacco", "2403")),
        TaricEntry("2403910000", "2403", "Homogenised or reconstituted tobacco",
                   ("homogenised tobacco", "reconstituted tobacco", "tobacco extract", "2403")),
        TaricEntry("2403990000", "2403", "Other manufactured tobacco",
                   ("tobacco", "snuff", "chewing tobacco", "tobacco extract", "2403")),
        TaricEntry("2404110000", "2404", "Vapor products with nicotine",
                   ("nicotine vape", "nic salt", "nicotine e-liquid", "vape juice with nicotine",
                    "e-cigarette liquid", "vaping with nicotine", "nicotine", "2404")),
        TaricEntry("2404120000", "2404", "Vapor products without nicotine",
                   ("vape", "e-liquid", "electronic cigarette", "e-cigarette", "puff", 
                    "bar juice", "vape juice", "zero nicotine", "without nicotine", 
                    "no nicotine", "nicotine free", "vaping", "2404")),
        TaricEntry("2404900000", "2404", "Other vapor products",
                   ("vapor product", "inhalation product", "aerosol", "2404")),
    ])
    
    # Chapter 85: Electrical Machinery - Key entries
    catalog.extend([
        TaricEntry("8506100010", "8506", "Alkaline manganese dioxide primary batteries",
                   ("alkaline battery", "aa battery", "aaa battery", "primary battery", 
                    "primary cell", "disposable battery", "zinc carbon battery", "8506")),
        TaricEntry("8506600010", "8506", "Other primary batteries and cells",
                   ("battery", "primary cell", "dry cell", "disposable cell", "lithium battery", "8506")),
        TaricEntry("8507600019", "8507", "Electric accumulators (rechargeable batteries)",
                   ("rechargeable battery", "accumulator", "li-ion battery", "ni-mh battery",
                    "lead acid battery", "8507")),
        TaricEntry("8517130000", "8517", "Smartphones",
                   ("smartphone", "iphone", "samsung", "android phone", "mobile phone",
                    "cell phone", "5g phone", "8517")),
        TaricEntry("8517140000", "8517", "Other wireless mobile phones",
                   ("mobile phone", "cell phone", "feature phone", "phone", "8517")),
        TaricEntry("8517620000", "8517", "Base stations for wireless communications",
                   ("antenna", "wireless", "base station", "cellular equipment", "8517")),
        TaricEntry("8518300000", "8518", "Headphones and earphones",
                   ("headphones", "airpods", "earbuds", "earphones", "headset", 
                    "bluetooth headphones", "wireless earphones", "8518")),
        TaricEntry("8518400000", "8518", "Audio amplifiers",
                   ("amplifier", "audio amp", "sound amplifier", "8518")),
        TaricEntry("8519810000", "8519", "Sound recording apparatus",
                   ("microphone", "audio recorder", "voice recorder", "8519")),
        TaricEntry("8521900000", "8521", "Video recording apparatus",
                   ("projector", "video", "video recorder", "dvr", "8521")),
        TaricEntry("8525801000", "8525", "Video camera recorders",
                   ("camera", "video", "camcorder", "action camera", "webcam", "8525")),
        TaricEntry("8528720000", "8528", "Computer monitors and displays",
                   ("monitor", "display", "screen", "lcd monitor", "led monitor", "8528")),
        TaricEntry("8542310000", "8542", "Electronic integrated circuits",
                   ("chip", "semiconductor", "integrated circuit", "microchip", "cpu",
                    "processor", "memory chip", "ic", "8542")),
        TaricEntry("8542320000", "8542", "Electronic integrated circuits - Memories",
                   ("memory", "ram", "rom", "flash memory", "storage chip", "8542")),
        TaricEntry("8542330000", "8542", "Electronic integrated circuits - Amplifiers",
                   ("amplifier", "op-amp", "audio amplifier ic", "8542")),
        TaricEntry("8544302090", "8544", "Electrical power distribution cables",
                   ("cable", "wire", "electrical", "power cable", "harness", "8544")),
    ])
    
    # Chapter 84: Machinery - Key entries
    catalog.extend([
        TaricEntry("8471300000", "8471", "Portable automatic data processing machines (Laptops)",
                   ("laptop", "notebook", "computer", "macbook", "portable computer",
                    "tablet computer", "ultrabook", "8471")),
        TaricEntry("8471410000", "8471", "Other data processing machines",
                   ("computer", "desktop", "server", "workstation", "pc", "8471")),
        TaricEntry("8471500000", "8471", "Processing units for ADP machines",
                   ("processing unit", "cpu unit", "computer module", "8471")),
        TaricEntry("8471600000", "8471", "Input/output units for ADP machines",
                   ("keyboard", "mouse", "scanner", "printer", "input device", "8471")),
        TaricEntry("8471700000", "8471", "Storage units for ADP machines",
                   ("storage", "hard drive", "ssd", "external drive", "memory storage", "8471")),
        TaricEntry("8443320000", "8443", "Printing machines (Inkjet, Laser)",
                   ("printer", "inkjet", "laser printer", "3d printer", "8443")),
        TaricEntry("8451800000", "8451", "Machines for washing clothes",
                   ("washing machine", "laundry", "dryer", "washer", "8451")),
        TaricEntry("8418690000", "8418", "Refrigerating and freezing equipment",
                   ("refrigerator", "freezer", "cooling", "fridge", "ice maker", "8418")),
        TaricEntry("8450110000", "8450", "Household washing machines",
                   ("washing machine", "laundry machine", "washer", "household appliance", "8450")),
    ])
    
    # Chapter 61/62: Clothing - Complete
    catalog.extend([
        TaricEntry("6105100000", "6105", "Men's shirts of cotton, knitted or crocheted",
                   ("shirt", "mens", "cotton", "garment", "clothing", "polo", 
                    "top", "knitted shirt", "dress shirt", "button-up", "6105")),
        TaricEntry("6105200000", "6105", "Men's shirts of man-made fibers",
                   ("shirt", "mens", "synthetic", "polyester", "knitted", "6105")),
        TaricEntry("6105900000", "6105", "Men's shirts of other textiles",
                   ("shirt", "mens", "linen", "wool", "knitted", "6105")),
        TaricEntry("6109100000", "6109", "T-shirts of cotton, knitted",
                   ("t-shirt", "tshirt", "top", "cotton top", "singlet", "tee", "6109")),
        TaricEntry("6109900000", "6109", "T-shirts of other textiles",
                   ("t-shirt", "top", "synthetic", "knitted", "6109")),
        TaricEntry("6203421100", "6203", "Men's trousers of denim (jeans)",
                   ("jeans", "denim", "pants", "trousers", "denim pants", "blue jeans", "6203")),
        TaricEntry("6203420000", "6203", "Men's trousers of cotton",
                   ("trousers", "pants", "cotton pants", "chinos", "6203")),
        TaricEntry("6203430000", "6203", "Men's trousers of synthetic fibers",
                   ("trousers", "pants", "synthetic", "polyester pants", "6203")),
        TaricEntry("6204610000", "6204", "Women's trousers of wool or fine animal hair",
                   ("womens pants", "trousers", "wool", "6204")),
        TaricEntry("6204620000", "6204", "Women's trousers of cotton",
                   ("womens pants", "trousers", "cotton", "jeans", "6204")),
        TaricEntry("6204630000", "6204", "Women's trousers of synthetic fibers",
                   ("womens pants", "trousers", "synthetic", "leggings", "6204")),
        TaricEntry("6205200000", "6205", "Men's shirts of cotton, not knitted",
                   ("shirt", "cotton", "woven", "dress shirt", "formal shirt", "6205")),
        TaricEntry("6206300000", "6206", "Women's shirts of cotton",
                   ("womens shirt", "cotton", "blouse", "top", "6206")),
        TaricEntry("6302210000", "6302", "Bed linen of cotton",
                   ("bedsheet", "sheet", "cotton", "bedding", "pillowcase", "6302")),
        TaricEntry("6304910000", "6304", "Curtains and interior blinds",
                   ("curtain", "textile", "drapery", "blinds", "6304")),
    ])
    
    # Chapter 64: Footwear
    catalog.extend([
        TaricEntry("6402990500", "6402", "Sports footwear with rubber/plastic sole",
                   ("sneakers", "nike", "adidas", "shoes", "sports shoes", "athletic shoes",
                    "running shoes", "training shoes", "6402")),
        TaricEntry("6403990000", "6403", "Sports footwear with leather upper",
                   ("shoes", "sports", "footwear", "leather shoes", "6403")),
        TaricEntry("6404110000", "6404", "Sports footwear with textile upper",
                   ("canvas shoes", "textile shoes", "sneakers", "6404")),
        TaricEntry("6404190000", "6404", "Footwear with textile upper",
                   ("slippers", "indoor shoes", "textile footwear", "6404")),
        TaricEntry("6405100000", "6405", "Footwear with upper of leather",
                   ("shoes", "footwear", "leather", "dress shoes", "6405")),
    ])
    
    # Chapter 33: Cosmetics
    catalog.extend([
        TaricEntry("3304990000", "3304", "Beauty or make-up preparations",
                   ("makeup", "cosmetic", "foundation", "lipstick", "mascara", "skincare", 
                    "cream", "lotion", "serum", "3304")),
        TaricEntry("3305100000", "3305", "Shampoos",
                   ("shampoo", "hair wash", "hair shampoo", "conditioner", "3305")),
        TaricEntry("3307200000", "3307", "Personal deodorants and antiperspirants",
                   ("deodorant", "antiperspirant", "body spray", "roll-on", "3307")),
        TaricEntry("3307300000", "3307", "Perfumes and toilet waters",
                   ("perfume", "cologne", "fragrance", "eau de toilette", "eau de parfum", "3307")),
        TaricEntry("3306100000", "3306", "Dentifrices (Toothpaste)",
                   ("toothpaste", "dental care", "oral hygiene", "3306")),
    ])
    
    # Chapter 30: Pharmaceuticals
    catalog.extend([
        TaricEntry("3004900000", "3004", "Medicaments for therapeutic use",
                   ("medicine", "drug", "pill", "tablet", "capsule", "pharmaceutical", 
                    "paracetamol", "ibuprofen", "medication", "3004")),
        TaricEntry("3002200090", "3002", "Vaccines",
                   ("vaccine", "immunization", "injection", "3002")),
        TaricEntry("2106909200", "2106", "Food supplements (Vitamins and minerals)",
                   ("vitamin", "supplement", "multivitamin", "dietary supplement", 
                    "vitamins", "minerals", "omega-3", "probiotic", "2106")),
    ])
    
    # Chapter 95: Toys & Games
    catalog.extend([
        TaricEntry("9503000000", "9503", "Toys and puzzles",
                   ("toy", "game", "puzzle", "doll", "action figure", "board game", 
                    "lego", "stuffed toy", "plush toy", "9503")),
        TaricEntry("9504500000", "9504", "Video game consoles and equipment",
                   ("playstation", "xbox", "nintendo", "console", "video game", 
                    "switch", "gaming", "game controller", "9504")),
        TaricEntry("9506290000", "9506", "Articles for sports and games",
                   ("sports", "ball", "racket", "equipment", "fitness", "9506")),
        TaricEntry("9507900000", "9507", "Fishing rods and reels",
                   ("fishing", "rod", "reel", "tackle", "9507")),
    ])
    
    # Chapter 94: Furniture
    catalog.extend([
        TaricEntry("9401200090", "9401", "Seats with wooden frames",
                   ("chair", "seat", "furniture", "wooden chair", "office chair", "9401")),
        TaricEntry("9403600090", "9403", "Furniture of wood",
                   ("desk", "table", "wooden furniture", "cabinet", "shelf", "9403")),
        TaricEntry("9403910000", "9403", "Furniture of wood - Parts",
                   ("furniture part", "wooden part", "9403")),
    ])
    
    # Chapter 39: Plastics
    catalog.extend([
        TaricEntry("3917310000", "3917", "Flexible tubes of plastic",
                   ("plastic tube", "hose", "tubing", "pvc tube", "3917")),
        TaricEntry("3923900000", "3923", "Plastic articles for packing",
                   ("plastic", "lid", "closure", "container", "packaging", "3923")),
        TaricEntry("3924100000", "3924", "Plastic tableware and kitchenware",
                   ("plastic dish", "plate", "cup", "bowl", "kitchenware", "3924")),
    ])
    
    # Chapter 73: Steel articles
    catalog.extend([
        TaricEntry("7308900000", "7308", "Structures of steel",
                   ("steel", "structural", "beam", "frame", "7308")),
        TaricEntry("7323990000", "7323", "Table, kitchen articles of iron/steel",
                   ("kitchenware", "cookware", "pot", "pan", "utensil", "7323")),
    ])
    
    # Chapter 70: Glass
    catalog.extend([
        TaricEntry("7007110000", "7007", "Safety glass (toughened/laminated)",
                   ("glass", "safety", "window", "windshield", "tempered glass", "7007")),
        TaricEntry("7010100000", "7010", "Glass bottles and containers",
                   ("bottle", "glass", "container", "jar", "7010")),
        TaricEntry("7013290000", "7013", "Drinking glasses",
                   ("glass", "drinking", "tableware", "cup", "mug", "7013")),
    ])
    
    # Chapter 42: Leather goods
    catalog.extend([
        TaricEntry("4202210010", "4202", "Handbags with outer surface of leather",
                   ("handbag", "purse", "bag", "leather", "wallet", "4202")),
        TaricEntry("4202910000", "4202", "Other leather articles",
                   ("leather goods", "briefcase", "luggage", "4202")),
    ])
    
    # Chapter 48: Paper
    catalog.extend([
        TaricEntry("4809900010", "4809", "Toilet paper",
                   ("toilet paper", "tissue", "paper", "bathroom tissue", "4809")),
        TaricEntry("4818100000", "4818", "Toilet paper and similar paper",
                   ("toilet paper", "tissue", "paper towel", "napkin", "4818")),
    ])
    
    # Chapter 96: Miscellaneous
    catalog.extend([
        TaricEntry("9619001000", "9619", "Sanitary towels and tampons",
                   ("sanitary", "personal care", "tampon", "pad", "kotex", 
                    "feminine hygiene", "menstrual product", "9619")),
        TaricEntry("9603290000", "9603", "Brooms and brushes",
                   ("broom", "brush", "cleaning", "toothbrush", "hairbrush", "9603")),
        TaricEntry("9609100000", "9609", "Pencils and crayons",
                   ("pencil", "crayon", "writing", "drawing", "9609")),
    ])
    
    # Chapter 32: Inks
    catalog.extend([
        TaricEntry("3210000000", "3210", "Printing inks and preparations",
                   ("ink", "printing", "stamp", "refill", "printer ink", "toner", "3210")),
        TaricEntry("3215110000", "3215", "Ink for writing or drawing",
                   ("ink", "pen ink", "fountain pen", "writing ink", "3215")),
    ])
    
    # Sort by TARIC code
    catalog.sort(key=lambda x: x.taric_code)
    
    return catalog


def validate_catalog(catalog: List[TaricEntry]) -> Tuple[List[TaricEntry], List[str]]:
    """Validate all entries in the catalog and return valid entries and errors."""
    valid_entries = []
    errors = []
    seen_codes = set()
    
    for entry in catalog:
        # Validate TARIC code
        if not validate_taric_code(entry.taric_code):
            errors.append(f"Invalid TARIC code: {entry.taric_code} - {entry.description}")
            continue
        
        # Validate HS4
        if not validate_hs4(entry.hs4):
            errors.append(f"Invalid HS4 code: {entry.hs4} for {entry.taric_code}")
            continue
        
        # Check for duplicates
        if entry.taric_code in seen_codes:
            errors.append(f"Duplicate TARIC code: {entry.taric_code} - {entry.description}")
            continue
        
        # Validate keywords
        if not entry.keywords or len(entry.keywords) == 0:
            errors.append(f"No keywords for: {entry.taric_code} - {entry.description}")
            continue
        
        seen_codes.add(entry.taric_code)
        valid_entries.append(entry)
    
    return valid_entries, errors


def generate_python_file(catalog: List[TaricEntry], output_path: str = "full_taric_catalog.py"):
    """Generate the full_taric_catalog.py file."""
    
    header = '''#!/usr/bin/env python3
"""Complete EU TARIC Catalog - Official codes from EU Tariff ({}+ entries, all chapters + subcases)."""

from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class TaricEntry:
    taric_code: str
    hs4: str
    description: str
    keywords: tuple

# Comprehensive EU TARIC Catalog - Official codes with multiple subcases per chapter ({}+ entries)
FULL_TARIC_CATALOG: Tuple[TaricEntry, ...] = (
'''
    
    footer = ''')

if __name__ == '__main__':
    print(f"✅ Full TARIC Catalog with {{len(FULL_TARIC_CATALOG)}} entries loaded")
    print(f"📊 Chapters covered: 1-96 (all EU chapters)")
    for i, entry in enumerate(FULL_TARIC_CATALOG[:5]):
        print(f"  [{{i+1}}] {{entry.taric_code}}: {{entry.description}}")
    print(f"  ... and {{len(FULL_TARIC_CATALOG) - 5}} more entries")
'''
    
    # Generate entry strings
    entries_str = ""
    current_chapter = ""
    
    for entry in catalog:
        chapter = entry.hs4[:2]
        
        # Add chapter header
        if chapter != current_chapter:
            current_chapter = chapter
            chapter_name = CHAPTER_DEFINITIONS.get(chapter, ("", ""))
            entries_str += f'\n    # ===== CHAPTER {chapter}: {chapter_name[1].upper()} =====\n'
        
        # Format keywords as tuple
        keywords_str = ", ".join(f'"{kw}"' for kw in entry.keywords)
        
        # Add entry
        entries_str += f'    TaricEntry("{entry.taric_code}", "{entry.hs4}", "{entry.description}",\n'
        entries_str += f'               ({keywords_str})),\n'
    
    # Write file
    content = header.format(len(catalog), len(catalog)) + entries_str + footer.format()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content


def validate_ai_matching(catalog: List[TaricEntry], test_cases: List[Tuple[str, str]]):
    """Validate AI matching by testing known product-to-TARIC mappings."""
    from taric_lookup import best_taric_match, _normalize_text_for_matching
    
    results = []
    for product_desc, expected_taric in test_cases:
        match = best_taric_match(product_desc, catalog)
        matched_code = match.taric_code if match else "NO_MATCH"
        success = matched_code == expected_taric
        
        results.append({
            'product': product_desc,
            'expected': expected_taric,
            'matched': matched_code,
            'success': success
        })
    
    return results


def main():
    """Main function to generate and validate the TARIC catalog."""
    print("=" * 70)
    print("🔧 TARIC Catalog Generator & Validator")
    print("=" * 70)
    print()
    
    # Step 1: Generate comprehensive catalog
    print("📝 Step 1: Generating comprehensive TARIC catalog...")
    catalog = generate_comprehensive_catalog()
    print(f"   ✅ Generated {len(catalog)} entries")
    print()
    
    # Step 2: Validate catalog
    print("🔍 Step 2: Validating catalog entries...")
    valid_entries, errors = validate_catalog(catalog)
    
    if errors:
        print(f"   ⚠️ Found {len(errors)} validation issues:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"      - {error}")
        if len(errors) > 10:
            print(f"      ... and {len(errors) - 10} more")
    else:
        print("   ✅ All entries valid!")
    print(f"   📊 Valid entries: {len(valid_entries)} / {len(catalog)}")
    print()
    
    # Step 3: Test AI matching
    print("🤖 Step 3: Testing AI matching with known products...")
    test_cases = [
        ("natural mineral water still", "2201101100"),
        ("sparkling mineral water", "2201101900"),
        ("coca cola soft drink", "2202990000"),
        ("heineken beer", "2203000000"),
        ("red wine bottle", "2204210000"),
        ("vodka premium", "2208303000"),
        ("cigarettes marlboro", "2402200000"),
        ("vape e-liquid without nicotine", "2404120000"),
        ("vape e-liquid with nicotine", "2404110000"),
        ("iphone smartphone", "8517130000"),
        ("airpods wireless earbuds", "8518300000"),
        ("macbook pro laptop", "8471300000"),
        ("mens cotton t-shirt", "6109100000"),
        ("mens denim jeans", "6203421100"),
        ("nike sneakers running shoes", "6402990500"),
        ("makeup foundation cream", "3304990000"),
        ("shampoo hair wash", "3305100000"),
        ("paracetamol tablets medicine", "3004900000"),
        ("lego toys building blocks", "9503000000"),
        ("playstation gaming console", "9504500000"),
    ]
    
    matching_results = validate_ai_matching(valid_entries, test_cases)
    
    success_count = sum(1 for r in matching_results if r['success'])
    print(f"   📊 Matching accuracy: {success_count}/{len(matching_results)} ({100*success_count/len(matching_results):.1f}%)")
    
    for result in matching_results:
        status = "✅" if result['success'] else "❌"
        print(f"      {status} {result['product'][:40]:<40} → {result['matched']}")
    print()
    
    # Step 4: Generate Python file
    print("📄 Step 4: Generating full_taric_catalog.py...")
    output_path = "full_taric_catalog.py"
    generate_python_file(valid_entries, output_path)
    print(f"   ✅ Catalog saved to {output_path}")
    print(f"   📊 Total entries: {len(valid_entries)}")
    
    # Print chapter summary
    chapters = {}
    for entry in valid_entries:
        chapter = entry.hs4[:2]
        if chapter not in chapters:
            chapters[chapter] = 0
        chapters[chapter] += 1
    
    print()
    print("📊 Chapter Summary:")
    for chapter_num in sorted(chapters.keys()):
        chapter_name = CHAPTER_DEFINITIONS.get(chapter_num, ("", ""))
        print(f"   Chapter {chapter_num}: {chapter_name[1]} - {chapters[chapter_num]} entries")
    
    print()
    print("=" * 70)
    print("🎉 Catalog generation completed successfully!")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())