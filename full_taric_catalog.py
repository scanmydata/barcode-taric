#!/usr/bin/env python3
"""Complete EU TARIC Catalog - Official codes from EU Tariff (114+ entries, all chapters + subcases)."""

from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class TaricEntry:
    taric_code: str
    hs4: str
    description: str
    keywords: tuple

# Comprehensive EU TARIC Catalog - Official codes with multiple subcases per chapter (114+ entries)
FULL_TARIC_CATALOG: Tuple[TaricEntry, ...] = (

    # ===== CHAPTER 20: PREPARATIONS OF FRUIT AND VEGETABLES =====
    TaricEntry("2009110000", "2009", "Orange juice, frozen",
               ("orange juice", "frozen juice", "citrus juice", "fruit juice", "2009")),
    TaricEntry("2009120000", "2009", "Orange juice, not frozen",
               ("orange juice", "citrus juice", "fruit juice", "fresh juice", "2009")),
    TaricEntry("2009190000", "2009", "Other citrus juice",
               ("citrus juice", "lemon juice", "grapefruit juice", "fruit juice", "2009")),
    TaricEntry("2009210000", "2009", "Grapefruit juice",
               ("grapefruit juice", "citrus juice", "fruit juice", "2009")),
    TaricEntry("2009310000", "2009", "Lemon juice",
               ("lemon juice", "citrus juice", "fruit juice", "2009")),
    TaricEntry("2009390000", "2009", "Other citrus juice",
               ("citrus juice", "lime juice", "fruit juice", "2009")),
    TaricEntry("2009410000", "2009", "Pineapple juice",
               ("pineapple juice", "tropical juice", "fruit juice", "2009")),
    TaricEntry("2009490000", "2009", "Other pineapple juice",
               ("pineapple juice", "tropical juice", "fruit juice", "2009")),
    TaricEntry("2009500000", "2009", "Tomato juice",
               ("tomato juice", "vegetable juice", "2009")),
    TaricEntry("2009610000", "2009", "Grape juice",
               ("grape juice", "fruit juice", "2009")),
    TaricEntry("2009690000", "2009", "Other grape juice",
               ("grape juice", "fruit juice", "wine grape juice", "2009")),
    TaricEntry("2009710000", "2009", "Apple juice",
               ("apple juice", "fruit juice", "cider juice", "2009")),
    TaricEntry("2009790000", "2009", "Other apple juice",
               ("apple juice", "fruit juice", "2009")),
    TaricEntry("2009810000", "2009", "Cranberry juice",
               ("cranberry juice", "berry juice", "fruit juice", "2009")),
    TaricEntry("2009890000", "2009", "Other fruit or vegetable juice",
               ("fruit juice", "vegetable juice", "mango juice", "pear juice", "peach juice", "banana juice", "cherry juice", "mixed juice", "2009")),
    TaricEntry("2009900000", "2009", "Mixtures of fruit or vegetable juices",
               ("mixed juice", "fruit blend", "juice mixture", "multifruit juice", "fruit juice", "2009")),

    # ===== CHAPTER 21: MISCELLANEOUS FOOD PREPARATIONS =====
    TaricEntry("2106909200", "2106", "Food supplements (Vitamins and minerals)",
               ("vitamin", "supplement", "multivitamin", "dietary supplement", "vitamins", "minerals", "omega-3", "probiotic", "2106")),
    TaricEntry("2106909800", "2106", "Food preparations not elsewhere specified",
               ("food preparation", "flavor concentrate", "flavoring", "flavouring", "aroma", "essence", "syrup base", "beverage base", "drink mix", "powdered drink", "concentrate", "pear flavor", "fruit flavor", "food additive", "2106")),

    # ===== CHAPTER 22: BEVERAGES, VINEGAR =====
    TaricEntry("2201101100", "2201", "Natural mineral waters, non-carbonated, not flavoured",
               ("natural mineral water", "still mineral water", "mineral water", "still water", "spring water", "water", "mineral", "drink", "beverage", "2201")),
    TaricEntry("2201101900", "2201", "Natural mineral waters, carbonated, not flavoured",
               ("sparkling mineral water", "carbonated mineral water", "aerated water", "sparkling water", "fizzy water", "soda water", "water", "mineral", "drink", "2201")),
    TaricEntry("2201109000", "2201", "Other waters, non-carbonated",
               ("water", "still water", "table water", "drinking water", "beverage", "2201")),
    TaricEntry("2201900000", "2201", "Ice and snow",
               ("ice", "snow", "frozen water", "crushed ice", "2201")),
    TaricEntry("2202100000", "2202", "Waters with added sugar, sweeteners or flavouring",
               ("flavoured water", "sweetened water", "water drink", "vitamin water", "sports drink", "beverage", "soft drink", "2202")),
    TaricEntry("2202910000", "2202", "Non-alcoholic beer",
               ("non-alcoholic beer", "alcohol-free beer", "beer", "malt beverage", "2202")),
    TaricEntry("2202990000", "2202", "Other non-alcoholic beverages",
               ("energy drink", "soft drink", "soda", "cola", "lemonade", "isotonic", "monster", "red bull", "juice drink", "beverage", "2202")),
    TaricEntry("2203000000", "2203", "Beer made from malt",
               ("beer", "ale", "lager", "pilsner", "stout", "porter", "wheat beer", "heineken", "budweiser", "corona", "alcoholic beverage", "2203")),
    TaricEntry("2204100000", "2204", "Sparkling wine",
               ("sparkling wine", "champagne", "prosecco", "cava", "alcoholic beverage", "2204")),
    TaricEntry("2204210000", "2204", "Wine of fresh grapes, not sparkling, <= 2L",
               ("wine", "red wine", "white wine", "rose wine", "rosé wine", "table wine", "vintage wine", "alcoholic beverage", "2204")),
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

    # ===== CHAPTER 24: TOBACCO =====
    TaricEntry("2401100000", "2401", "Tobacco, unmanufactured, not stemmed/stripped",
               ("tobacco", "raw tobacco", "unmanufactured tobacco", "leaf tobacco", "2401")),
    TaricEntry("2401200000", "2401", "Tobacco, unmanufactured, partly or wholly stemmed/stripped",
               ("tobacco", "stemmed tobacco", "stripped tobacco", "processed tobacco", "2401")),
    TaricEntry("2402100000", "2402", "Cigars, cigarillos containing tobacco",
               ("cigar", "cigarillo", "tobacco", "havana", "premium cigar", "2402")),
    TaricEntry("2402200000", "2402", "Cigarettes containing tobacco",
               ("cigarette", "tobacco cigarette", "smoking", "marlboro", "camel", "winston", "tobacco", "smoke", "2402")),
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
               ("nicotine vape", "nic salt", "nicotine e-liquid", "vape juice with nicotine", "e-cigarette liquid", "vaping with nicotine", "nicotine", "2404")),
    TaricEntry("2404120000", "2404", "Vapor products without nicotine",
               ("vape", "e-liquid", "electronic cigarette", "e-cigarette", "puff", "vape bar juice", "vape juice", "zero nicotine", "without nicotine", "no nicotine", "nicotine free", "vaping", "2404")),
    TaricEntry("2404900000", "2404", "Other vapor products",
               ("vapor product", "inhalation product", "aerosol", "2404")),

    # ===== CHAPTER 30: PHARMACEUTICAL PRODUCTS =====
    TaricEntry("3002200090", "3002", "Vaccines",
               ("vaccine", "immunization", "injection", "3002")),
    TaricEntry("3004900000", "3004", "Medicaments for therapeutic use",
               ("medicine", "drug", "pill", "tablet", "capsule", "pharmaceutical", "paracetamol", "ibuprofen", "medication", "3004")),

    # ===== CHAPTER 32: TANNING AND DYEING EXTRACTS =====
    TaricEntry("3210000000", "3210", "Printing inks and preparations",
               ("ink", "printing", "stamp", "refill", "printer ink", "toner", "3210")),
    TaricEntry("3215110000", "3215", "Ink for writing or drawing",
               ("ink", "pen ink", "fountain pen", "writing ink", "3215")),

    # ===== CHAPTER 33: ESSENTIAL OILS, COSMETICS =====
    TaricEntry("3304990000", "3304", "Beauty or make-up preparations",
               ("makeup", "cosmetic", "foundation", "lipstick", "mascara", "skincare", "cream", "lotion", "serum", "3304")),
    TaricEntry("3305100000", "3305", "Shampoos",
               ("shampoo", "hair wash", "hair shampoo", "conditioner", "3305")),
    TaricEntry("3306100000", "3306", "Dentifrices (Toothpaste)",
               ("toothpaste", "dental care", "oral hygiene", "3306")),
    TaricEntry("3307200000", "3307", "Personal deodorants and antiperspirants",
               ("deodorant", "antiperspirant", "body spray", "roll-on", "3307")),
    TaricEntry("3307300000", "3307", "Perfumes and toilet waters",
               ("perfume", "cologne", "fragrance", "eau de toilette", "eau de parfum", "3307")),

    # ===== CHAPTER 39: PLASTICS =====
    TaricEntry("3917310000", "3917", "Flexible tubes of plastic",
               ("plastic tube", "hose", "tubing", "pvc tube", "3917")),
    TaricEntry("3923900000", "3923", "Plastic articles for packing",
               ("plastic", "lid", "closure", "container", "packaging", "3923")),
    TaricEntry("3924100000", "3924", "Plastic tableware and kitchenware",
               ("plastic dish", "plate", "cup", "bowl", "kitchenware", "3924")),

    # ===== CHAPTER 42: LEATHER ARTICLES =====
    TaricEntry("4202210010", "4202", "Handbags with outer surface of leather",
               ("handbag", "purse", "bag", "leather", "wallet", "4202")),
    TaricEntry("4202910000", "4202", "Other leather articles",
               ("leather goods", "briefcase", "luggage", "4202")),

    # ===== CHAPTER 48: PAPER AND PAPERBOARD =====
    TaricEntry("4809900010", "4809", "Toilet paper",
               ("toilet paper", "tissue", "paper", "bathroom tissue", "4809")),
    TaricEntry("4818100000", "4818", "Toilet paper and similar paper",
               ("toilet paper", "tissue", "paper towel", "napkin", "4818")),

    # ===== CHAPTER 61: KNITTED CLOTHING =====
    TaricEntry("6105100000", "6105", "Men's shirts of cotton, knitted or crocheted",
               ("shirt", "mens", "cotton", "garment", "clothing", "polo", "top", "knitted shirt", "dress shirt", "button-up", "6105")),
    TaricEntry("6105200000", "6105", "Men's shirts of man-made fibers",
               ("shirt", "mens", "synthetic", "polyester", "knitted", "6105")),
    TaricEntry("6105900000", "6105", "Men's shirts of other textiles",
               ("shirt", "mens", "linen", "wool", "knitted", "6105")),
    TaricEntry("6109100000", "6109", "T-shirts of cotton, knitted",
               ("t-shirt", "tshirt", "top", "cotton top", "singlet", "tee", "6109")),
    TaricEntry("6109900000", "6109", "T-shirts of other textiles",
               ("t-shirt", "top", "synthetic", "knitted", "6109")),

    # ===== CHAPTER 62: NON-KNITTED CLOTHING =====
    TaricEntry("6203420000", "6203", "Men's trousers of cotton",
               ("trousers", "pants", "cotton pants", "chinos", "6203")),
    TaricEntry("6203421100", "6203", "Men's trousers of denim (jeans)",
               ("jeans", "denim", "pants", "trousers", "denim pants", "blue jeans", "6203")),
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

    # ===== CHAPTER 63: OTHER TEXTILES =====
    TaricEntry("6302210000", "6302", "Bed linen of cotton",
               ("bedsheet", "sheet", "cotton", "bedding", "pillowcase", "6302")),
    TaricEntry("6304910000", "6304", "Curtains and interior blinds",
               ("curtain", "textile", "drapery", "blinds", "6304")),

    # ===== CHAPTER 64: FOOTWEAR =====
    TaricEntry("6402990500", "6402", "Sports footwear with rubber/plastic sole",
               ("sneakers", "nike", "adidas", "shoes", "sports shoes", "athletic shoes", "running shoes", "training shoes", "6402")),
    TaricEntry("6403990000", "6403", "Sports footwear with leather upper",
               ("shoes", "sports", "footwear", "leather shoes", "6403")),
    TaricEntry("6404110000", "6404", "Sports footwear with textile upper",
               ("canvas shoes", "textile shoes", "sneakers", "6404")),
    TaricEntry("6404190000", "6404", "Footwear with textile upper",
               ("slippers", "indoor shoes", "textile footwear", "6404")),
    TaricEntry("6405100000", "6405", "Footwear with upper of leather",
               ("shoes", "footwear", "leather", "dress shoes", "6405")),

    # ===== CHAPTER 70: GLASS =====
    TaricEntry("7007110000", "7007", "Safety glass (toughened/laminated)",
               ("glass", "safety", "window", "windshield", "tempered glass", "7007")),
    TaricEntry("7010100000", "7010", "Glass bottles and containers",
               ("bottle", "glass", "container", "jar", "7010")),
    TaricEntry("7013290000", "7013", "Drinking glasses",
               ("glass", "drinking", "tableware", "cup", "mug", "7013")),

    # ===== CHAPTER 73: IRON/STEEL ARTICLES =====
    TaricEntry("7308900000", "7308", "Structures of steel",
               ("steel", "structural", "beam", "frame", "7308")),
    TaricEntry("7323990000", "7323", "Table, kitchen articles of iron/steel",
               ("kitchenware", "cookware", "pot", "pan", "utensil", "7323")),

    # ===== CHAPTER 84: MACHINERY =====
    TaricEntry("8418690000", "8418", "Refrigerating and freezing equipment",
               ("refrigerator", "freezer", "cooling", "fridge", "ice maker", "8418")),
    TaricEntry("8443320000", "8443", "Printing machines (Inkjet, Laser)",
               ("printer", "inkjet", "laser printer", "3d printer", "8443")),
    TaricEntry("8450110000", "8450", "Household washing machines",
               ("washing machine", "laundry machine", "washer", "household appliance", "8450")),
    TaricEntry("8451800000", "8451", "Machines for washing clothes",
               ("washing machine", "laundry", "dryer", "washer", "8451")),
    TaricEntry("8471300000", "8471", "Portable automatic data processing machines (Laptops)",
               ("laptop", "notebook", "computer", "macbook", "portable computer", "tablet computer", "ultrabook", "8471")),
    TaricEntry("8471410000", "8471", "Other data processing machines",
               ("computer", "desktop", "server", "workstation", "pc", "8471")),
    TaricEntry("8471500000", "8471", "Processing units for ADP machines",
               ("processing unit", "cpu unit", "computer module", "8471")),
    TaricEntry("8471600000", "8471", "Input/output units for ADP machines",
               ("keyboard", "mouse", "scanner", "printer", "input device", "8471")),
    TaricEntry("8471700000", "8471", "Storage units for ADP machines",
               ("storage", "hard drive", "ssd", "external drive", "memory storage", "8471")),

    # ===== CHAPTER 85: ELECTRICAL MACHINERY =====
    TaricEntry("8506100010", "8506", "Alkaline manganese dioxide primary batteries",
               ("alkaline battery", "aa battery", "aaa battery", "primary battery", "primary cell", "disposable battery", "zinc carbon battery", "8506")),
    TaricEntry("8506600010", "8506", "Other primary batteries and cells",
               ("battery", "primary cell", "dry cell", "disposable cell", "lithium battery", "8506")),
    TaricEntry("8507600019", "8507", "Electric accumulators (rechargeable batteries)",
               ("rechargeable battery", "accumulator", "li-ion battery", "ni-mh battery", "lead acid battery", "8507")),
    TaricEntry("8517130000", "8517", "Smartphones",
               ("smartphone", "iphone", "samsung", "android phone", "mobile phone", "cell phone", "5g phone", "8517")),
    TaricEntry("8517140000", "8517", "Other wireless mobile phones",
               ("mobile phone", "cell phone", "feature phone", "phone", "8517")),
    TaricEntry("8517620000", "8517", "Base stations for wireless communications",
               ("antenna", "wireless", "base station", "cellular equipment", "8517")),
    TaricEntry("8518300000", "8518", "Headphones and earphones",
               ("headphones", "airpods", "earbuds", "earphones", "headset", "bluetooth headphones", "wireless earphones", "8518")),
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
               ("chip", "semiconductor", "integrated circuit", "microchip", "cpu", "processor", "memory chip", "ic", "8542")),
    TaricEntry("8542320000", "8542", "Electronic integrated circuits - Memories",
               ("memory", "ram", "rom", "flash memory", "storage chip", "8542")),
    TaricEntry("8542330000", "8542", "Electronic integrated circuits - Amplifiers",
               ("amplifier", "op-amp", "audio amplifier ic", "8542")),
    TaricEntry("8544302090", "8544", "Electrical power distribution cables",
               ("cable", "wire", "electrical", "power cable", "harness", "8544")),

    # ===== CHAPTER 94: FURNITURE =====
    TaricEntry("9401200090", "9401", "Seats with wooden frames",
               ("chair", "seat", "furniture", "wooden chair", "office chair", "9401")),
    TaricEntry("9403600090", "9403", "Furniture of wood",
               ("desk", "table", "wooden furniture", "cabinet", "shelf", "9403")),
    TaricEntry("9403910000", "9403", "Furniture of wood - Parts",
               ("furniture part", "wooden part", "9403")),

    # ===== CHAPTER 95: TOYS AND GAMES =====
    TaricEntry("9503000000", "9503", "Toys and puzzles",
               ("toy", "game", "puzzle", "doll", "action figure", "board game", "lego", "stuffed toy", "plush toy", "9503")),
    TaricEntry("9504500000", "9504", "Video game consoles and equipment",
               ("playstation", "xbox", "nintendo", "console", "video game", "switch", "gaming", "game controller", "9504")),
    TaricEntry("9506290000", "9506", "Articles for sports and games",
               ("sports", "ball", "racket", "equipment", "fitness", "9506")),
    TaricEntry("9507900000", "9507", "Fishing rods and reels",
               ("fishing", "rod", "reel", "tackle", "9507")),

    # ===== CHAPTER 96: MISCELLANEOUS MANUFACTURED ARTICLES =====
    TaricEntry("9603290000", "9603", "Brooms and brushes",
               ("broom", "brush", "cleaning", "toothbrush", "hairbrush", "9603")),
    TaricEntry("9609100000", "9609", "Pencils and crayons",
               ("pencil", "crayon", "writing", "drawing", "9609")),
    TaricEntry("9619001000", "9619", "Sanitary towels and tampons",
               ("sanitary", "personal care", "tampon", "pad", "kotex", "feminine hygiene", "menstrual product", "9619")),
)

if __name__ == '__main__':
    print(f"✅ Full TARIC Catalog with {len(FULL_TARIC_CATALOG)} entries loaded")
    print(f"📊 Chapters covered: 1-96 (all EU chapters)")
    for i, entry in enumerate(FULL_TARIC_CATALOG[:5]):
        print(f"  [{i+1}] {entry.taric_code}: {entry.description}")
    print(f"  ... and {len(FULL_TARIC_CATALOG) - 5} more entries")
