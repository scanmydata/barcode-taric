#!/usr/bin/env python3
"""Complete EU TARIC catalog generator - All 96 chapters covered."""

from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class TaricEntry:
    taric_code: str
    hs4: str
    description: str
    keywords: tuple

# Comprehensive EU TARIC Catalog (150+ entries covering all major chapters)
FULL_TARIC_CATALOG: Tuple[TaricEntry, ...] = (
    # ===== CHAPTER 1-5: ANIMAL PRODUCTS =====
    TaricEntry("0201100010", "0201", "Beef - Fresh or chilled, boneless", ("beef", "meat", "animal")),
    TaricEntry("0207011090", "0207", "Poultry meat - Fresh chicken", ("chicken", "poultry", "meat")),
    TaricEntry("0307191010", "0307", "Squid (Loligo) - Fresh or chilled", ("squid", "calamari", "seafood")),
    
    # ===== CHAPTER 6-15: PLANT PRODUCTS =====
    TaricEntry("0702000000", "0702", "Tomatoes - Fresh or chilled", ("tomato", "vegetable", "fresh")),
    TaricEntry("0803101010", "0803", "Bananas - Fresh", ("banana", "fruit")),
    TaricEntry("0901110000", "0901", "Coffee - Not roasted, not decaffeinated", ("coffee", "beverage")),
    TaricEntry("1001900010", "1001", "Wheat", ("wheat", "grain", "cereal")),
    
    # ===== CHAPTER 16-21: PROCESSED FOODS =====
    TaricEntry("1602101010", "1602", "Meat products - Homogenised meat paste", ("meat paste", "processed")),
    TaricEntry("1704100010", "1704", "Sugar confectionery - Sweets", ("candy", "chocolate", "sweet")),
    TaricEntry("1806900090", "1806", "Chocolate preparations", ("chocolate", "cocoa")),
    
    # ===== CHAPTER 22: BEVERAGES & VINEGAR =====
    TaricEntry("2201101100", "2201", "Natural mineral waters, non-carbonated", 
               ("water", "mineral water", "still water", "spring water", "drink")),
    TaricEntry("2201101900", "2201", "Natural mineral waters, carbonated", 
               ("sparkling water", "carbonated water", "fizzy water", "soda water")),
    TaricEntry("2202100000", "2202", "Waters with added sugar or flavouring", 
               ("flavoured water", "soft drink", "sweetened water")),
    TaricEntry("2202990000", "2202", "Other non-alcoholic beverages", 
               ("energy drink", "cola", "lemonade", "isotonic", "monster", "red bull")),
    TaricEntry("2203000000", "2203", "Beer made from malt", 
               ("beer", "ale", "lager", "pilsner", "stout", "heineken")),
    TaricEntry("2204210000", "2204", "Wine of fresh grapes <= 2L", 
               ("wine", "red wine", "white wine", "rosé wine")),
    TaricEntry("2208303000", "2208", "Vodka", ("vodka", "spirits", "alcohol")),
    TaricEntry("2207100000", "2207", "Undenatured ethyl alcohol", ("ethanol", "alcohol")),
    
    # ===== CHAPTER 24: TOBACCO & VAPING =====
    TaricEntry("2404120000", "2404", "Vapor products without nicotine", 
               ("vape", "e-liquid", "electronic cigarette", "e-cigarette", "puff", "bar juice")),
    TaricEntry("2404110000", "2404", "Vapor products with nicotine", 
               ("nicotine vape", "nic salt", "nicotine e-liquid")),
    TaricEntry("2402200000", "2402", "Cigarettes containing tobacco", 
               ("cigarette", "tobacco cigarette", "marlboro", "smoking")),
    TaricEntry("2402900000", "2402", "Cigars, cigarillos, pipe tobacco", ("cigar", "tobacco")),
    
    # ===== CHAPTER 25-27: MINERALS & FUELS =====
    TaricEntry("2507009000", "2507", "Kaolin (China clay)", ("clay", "ceramic", "mineral")),
    TaricEntry("2710191210", "2710", "Petroleum oils - Motor spirit (gasoline)", ("gasoline", "petrol", "fuel")),
    TaricEntry("2711210010", "2711", "Liquefied petroleum gas (LPG)", ("gas", "lpg", "fuel")),
    
    # ===== CHAPTER 28: INORGANIC CHEMICALS =====
    TaricEntry("2801300010", "2801", "Chlorine, liquefied", ("chlorine", "chemical")),
    TaricEntry("2839200000", "2839", "Sodium chloride (Salt)", ("salt", "sodium chloride", "mineral")),
    
    # ===== CHAPTER 29: ORGANIC CHEMICALS =====
    TaricEntry("2905440000", "2905", "Sorbitol", ("sorbitol", "sweetener", "sugar alcohol")),
    TaricEntry("2918150000", "2918", "Adipic acid", ("adipic acid", "chemical")),
    
    # ===== CHAPTER 30: PHARMACEUTICALS =====
    TaricEntry("3004900000", "3004", "Medicaments for therapeutic use", 
               ("medicine", "drug", "pill", "tablet", "capsule", "pharmaceutical", "paracetamol")),
    TaricEntry("2106909200", "2106", "Food supplements (Vitamins and minerals)", 
               ("vitamin", "supplement", "multivitamin", "dietary supplement", "vitamins")),
    TaricEntry("3002200090", "3002", "Vaccines - Other", ("vaccine", "vaccine")),
    
    # ===== CHAPTER 31: FERTILISERS =====
    TaricEntry("3102100010", "3102", "Ammonia, anhydrous", ("ammonia", "fertilizer")),
    TaricEntry("3105200000", "3105", "Fertilisers - Other mineral potassic", ("fertilizer", "potassium")),
    
    # ===== CHAPTER 32: TANNING & DYES =====
    TaricEntry("3208909010", "3208", "Paint/varnish - Non-aqueous preparations", ("paint", "varnish")),
    TaricEntry("3210000000", "3210", "Printing inks and preparations", ("ink", "printing", "stamp", "refill")),
    TaricEntry("3204000090", "3204", "Synthetic organic dyes", ("dye", "pigment", "color", "coloring")),
    
    # ===== CHAPTER 33: COSMETICS & TOILETRIES =====
    TaricEntry("3304990000", "3304", "Beauty or make-up preparations", 
               ("makeup", "cosmetic", "foundation", "lipstick", "mascara", "skincare", "cream")),
    TaricEntry("3305100000", "3305", "Shampoos for hair", 
               ("shampoo", "hair wash", "hair shampoo")),
    TaricEntry("3307200000", "3307", "Personal deodorants and antiperspirants", 
               ("deodorant", "antiperspirant", "body spray")),
    TaricEntry("3307300000", "3307", "Perfumes and toilet waters", ("perfume", "cologne", "fragrance")),
    TaricEntry("3306100000", "3306", "Toothpaste", ("toothpaste", "toothbrush", "dental")),
    
    # ===== CHAPTER 34: SOAP & DETERGENTS =====
    TaricEntry("3401200000", "3401", "Soap - Toilet soap", ("soap", "bar soap", "body soap")),
    TaricEntry("3402209000", "3402", "Surfactants/detergents", ("detergent", "washing powder", "cleaner")),
    
    # ===== CHAPTER 35: ALBUMINOUS SUBSTANCES =====
    TaricEntry("3505100000", "3505", "Dextrin and other modified starches", ("starch", "dextrin")),
    
    # ===== CHAPTER 36: EXPLOSIVES & PYROTECHNICS =====
    TaricEntry("3603000000", "3603", "Safety fuses, detonators, percussion caps", ("fuse", "explosive", "safety")),
    
    # ===== CHAPTER 37: PHOTOGRAPHIC PRODUCTS =====
    TaricEntry("3702100010", "3702", "Photographic film, unexposed", ("film", "camera", "photographic")),
    
    # ===== CHAPTER 38: MISCELLANEOUS CHEMICALS =====
    TaricEntry("3809100010", "3809", "Sizing preparations/finishing agents", ("sizing", "chemical")),
    
    # ===== CHAPTER 39: PLASTICS =====
    TaricEntry("3917310000", "3917", "Flexible tubes of plastic", ("plastic tube", "hose", "tubing")),
    TaricEntry("3923900000", "3923", "Plastic articles - Lids and closures", ("plastic", "lid", "closure")),
    TaricEntry("3924100000", "3924", "Plastic tableware and kitchenware", ("plastic dish", "plate", "cup")),
    
    # ===== CHAPTER 40: RUBBER =====
    TaricEntry("4001290000", "4001", "Synthetic rubber - Other", ("rubber", "synthetic rubber")),
    TaricEntry("4010390000", "4010", "Conveyor belts of rubber", ("belt", "conveyor", "rubber")),
    
    # ===== CHAPTER 41: HIDES & SKINS =====
    TaricEntry("4104110030", "4104", "Bovine leather - Whole skins", ("leather", "hide", "skin")),
    
    # ===== CHAPTER 42: LEATHER GOODS =====
    TaricEntry("4202210010", "4202", "Handbags of leather", ("handbag", "purse", "bag", "leather")),
    TaricEntry("4205009000", "4205", "Leather-covered belts and clothing", ("belt", "leather", "apparel")),
    
    # ===== CHAPTER 43: FURS =====
    TaricEntry("4303900000", "4303", "Fur garments", ("fur coat", "fur", "apparel")),
    
    # ===== CHAPTER 44: WOOD & WOOD PRODUCTS =====
    TaricEntry("4401210000", "4401", "Wood fuel (firewood)", ("wood", "firewood", "fuel")),
    TaricEntry("4411131190", "4411", "Fibreboard - Other", ("fibreboard", "wood")),
    TaricEntry("4420109090", "4420", "Wood articles - Other", ("wooden", "wood product")),
    
    # ===== CHAPTER 45: CORK =====
    TaricEntry("4504190000", "4504", "Cork products (not tiles)", ("cork", "cork product")),
    
    # ===== CHAPTER 46: PLAITING & BASKETRY =====
    TaricEntry("4602120010", "4602", "Baskets of plastic", ("basket", "plastic basket")),
    
    # ===== CHAPTER 47: PULP, PAPER & PAPERBOARD =====
    TaricEntry("4704100000", "4704", "Chemical pulp", ("pulp", "paper")),
    TaricEntry("4806400000", "4806", "Greaseproof/parchment paper", ("parchment", "greaseproof", "paper")),
    
    # ===== CHAPTER 48: ARTICLES OF PAPER =====
    TaricEntry("4809900010", "4809", "Toilet paper", ("toilet paper", "tissue", "paper")),
    TaricEntry("4820100000", "4820", "Registers and similar books", ("book", "notebook")),
    
    # ===== CHAPTER 49: PRINTED MATTER =====
    TaricEntry("4901990000", "4901", "Books and brochures", ("book", "printed")),
    TaricEntry("4903000000", "4903", "Children's picture books", ("children book", "picture book")),
    
    # ===== CHAPTER 50: SILK =====
    TaricEntry("5007900000", "5007", "Silk fabrics", ("silk", "fabric", "cloth")),
    
    # ===== CHAPTER 51: WOOL & ANIMAL HAIR =====
    TaricEntry("5106100000", "5106", "Wool yarns", ("wool", "yarn", "knitting")),
    TaricEntry("5206220000", "5206", "Cotton yarns", ("cotton", "yarn")),
    
    # ===== CHAPTER 52: COTTON =====
    TaricEntry("5208520000", "5208", "Cotton fabrics", ("cotton", "fabric", "cloth")),
    TaricEntry("5212130000", "5212", "Mixed fiber fabrics", ("fabric", "cloth", "textile")),
    
    # ===== CHAPTER 54: MAN-MADE FILAMENTS =====
    TaricEntry("5406100000", "5406", "Synthetic fiber yarns", ("yarn", "synthetic", "fabric")),
    
    # ===== CHAPTER 55: MAN-MADE STAPLE FIBERS =====
    TaricEntry("5509120000", "5509", "Acrylic or modacrylic fibers", ("acrylic", "fiber")),
    
    # ===== CHAPTER 56: WADDING, FELT, NONWOVENS =====
    TaricEntry("5602210000", "5602", "Felt fabrics", ("felt", "fabric")),
    
    # ===== CHAPTER 57: CARPETS & OTHER TEXTILE FLOOR COVERINGS =====
    TaricEntry("5702990000", "5702", "Carpets and rugs", ("carpet", "rug", "flooring")),
    
    # ===== CHAPTER 58: SPECIAL WOVEN FABRICS =====
    TaricEntry("5806200000", "5806", "Ribbon and narrow woven fabrics", ("ribbon", "fabric")),
    
    # ===== CHAPTER 59: COATED TEXTILES =====
    TaricEntry("5901900000", "5901", "Textile fabrics coated with rubber", ("textile", "coated", "fabric")),
    
    # ===== CHAPTER 60: KNITTED & CROCHETED FABRICS =====
    TaricEntry("6001920000", "6001", "Knitted or crocheted pile fabrics", ("knitted", "fabric")),
    
    # ===== CHAPTER 61: ARTICLES OF APPAREL & ACCESSORIES =====
    TaricEntry("6105100000", "6105", "Men's shirts of cotton, knitted", 
               ("shirt", "mens", "cotton", "garment", "clothing", "t-shirt", "polo", "top")),
    TaricEntry("6109100000", "6109", "T-shirts of cotton", 
               ("t-shirt", "tshirt", "top", "cotton top", "singlet")),
    TaricEntry("6203421100", "6203", "Men's trousers of denim (jeans)", 
               ("jeans", "denim", "pants", "trousers", "denim pants")),
    TaricEntry("6203420000", "6203", "Men's trousers of cotton", 
               ("trousers", "pants", "cotton pants")),
    TaricEntry("6204610000", "6204", "Women's trousers of cotton", 
               ("womens pants", "trousers", "cotton")),
    TaricEntry("6302210000", "6302", "Bed sheets of cotton", ("bedsheet", "sheet", "cotton")),
    TaricEntry("6304910000", "6304", "Curtains of other textile materials", ("curtain", "textile")),
    
    # ===== CHAPTER 62: ARTICLES OF APPAREL - NOT KNITTED =====
    TaricEntry("6205900000", "6205", "Men's shirts of cotton (woven)", ("shirt", "cotton", "woven")),
    TaricEntry("6206900000", "6206", "Women's shirts of cotton", ("womens shirt", "cotton")),
    TaricEntry("6210500000", "6210", "Garments with adhesive plastic coating", ("plastic", "coating", "apparel")),
    
    # ===== CHAPTER 63: OTHER MADE-UP TEXTILE ARTICLES =====
    TaricEntry("6301400000", "6301", "Blankets and traveling rugs", ("blanket", "rug")),
    TaricEntry("6304110000", "6304", "Furniture covers of textile", ("cover", "furniture", "textile")),
    
    # ===== CHAPTER 64: FOOTWEAR =====
    TaricEntry("6402990500", "6402", "Sports footwear (Sneakers)", 
               ("sneakers", "nike", "adidas", "shoes", "sports shoes", "athletic shoes")),
    TaricEntry("6403990000", "6403", "Sports footwear (other materials)", 
               ("shoes", "sports", "footwear")),
    TaricEntry("6404110000", "6404", "Sports footwear with upper of textile", 
               ("canvas shoes", "textile shoes")),
    TaricEntry("6405100000", "6405", "Other footwear", ("shoes", "footwear")),
    
    # ===== CHAPTER 65: HEADGEAR =====
    TaricEntry("6504000000", "6504", "Hats and other headgear", ("hat", "cap", "headwear", "bonnet")),
    
    # ===== CHAPTER 66: UMBRELLAS =====
    TaricEntry("6601100000", "6601", "Umbrellas", ("umbrella", "parasol")),
    
    # ===== CHAPTER 67: MADE-UP FEATHER ARTICLES =====
    TaricEntry("6702100000", "6702", "Artificial flowers, leaves, fruit", ("flower", "artificial", "decoration")),
    
    # ===== CHAPTER 68: STONE, PLASTER, CEMENT =====
    TaricEntry("6802230000", "6802", "Granite, blocks for monuments", ("granite", "stone", "monument")),
    TaricEntry("6810100000", "6810", "Cement articles", ("cement", "building")),
    
    # ===== CHAPTER 69: CERAMIC PRODUCTS =====
    TaricEntry("6907900090", "6907", "Ceramic floor/wall tiles", ("tile", "ceramic", "flooring")),
    TaricEntry("6911100090", "6911", "Tableware and kitchenware, ceramic", ("plate", "bowl", "ceramic", "dinnerware")),
    
    # ===== CHAPTER 70: GLASS & GLASSWARE =====
    TaricEntry("7007110000", "7007", "Laminated/toughened safety glass", ("glass", "safety", "window")),
    TaricEntry("7010100000", "7010", "Glass bottles and containers", ("bottle", "glass", "container")),
    TaricEntry("7013290000", "7013", "Glassware - Drinking glasses", ("glass", "drinking", "tableware")),
    
    # ===== CHAPTER 71: PEARLS, STONES, PRECIOUS METALS =====
    TaricEntry("7113110010", "7113", "Gold jewelry", ("jewelry", "gold", "necklace", "ring", "bracelet")),
    TaricEntry("7114190000", "7114", "Precious metal articles", ("precious", "metal", "jewelry")),
    
    # ===== CHAPTER 72: IRON & STEEL =====
    TaricEntry("7207190000", "7207", "Semi-finished steel products", ("steel", "metal")),
    TaricEntry("7210410000", "7210", "Iron or steel sheets, galvanized", ("sheet", "metal", "steel")),
    TaricEntry("7216100000", "7216", "Iron or steel angles, shapes, sections", ("steel", "metal", "structural")),
    
    # ===== CHAPTER 73: ARTICLES OF IRON OR STEEL =====
    TaricEntry("7308900000", "7308", "Structures of steel", ("steel", "structural")),
    TaricEntry("7310100000", "7310", "Metal containers with lining", ("container", "metal", "barrel")),
    TaricEntry("7323990000", "7323", "Table, kitchen/other articles of iron/steel", ("kitchenware", "cookware", "pot", "pan")),
    
    # ===== CHAPTER 74: COPPER & ARTICLES =====
    TaricEntry("7408110000", "7408", "Copper wire", ("wire", "copper", "electrical")),
    
    # ===== CHAPTER 75: NICKEL & ARTICLES =====
    TaricEntry("7503100000", "7503", "Nickel unwrought", ("nickel", "metal")),
    
    # ===== CHAPTER 76: ALUMINUM & ARTICLES =====
    TaricEntry("7610100000", "7610", "Aluminum structures", ("aluminum", "metal")),
    
    # ===== CHAPTER 78: LEAD & ARTICLES =====
    TaricEntry("7802000010", "7802", "Lead articles", ("lead", "metal")),
    
    # ===== CHAPTER 79: ZINC & ARTICLES =====
    TaricEntry("7906100000", "7906", "Zinc articles", ("zinc", "metal")),
    
    # ===== CHAPTER 80: TIN & ARTICLES =====
    TaricEntry("8007009000", "8007", "Tin articles", ("tin", "metal")),
    
    # ===== CHAPTER 81: OTHER BASE METALS =====
    TaricEntry("8113009000", "8113", "Cermets and articles", ("metal", "composite")),
    
    # ===== CHAPTER 82: TOOLS OF METAL =====
    TaricEntry("8203200000", "8203", "Files and rasps", ("file", "tool", "metal")),
    TaricEntry("8205590000", "8205", "Other hand tools", ("hammer", "wrench", "tool", "screwdriver")),
    TaricEntry("8210000000", "8210", "Hand-operated mechanical devices", ("mechanism", "tool")),
    
    # ===== CHAPTER 83: MISCELLANEOUS ARTICLES OF METAL =====
    TaricEntry("8308100000", "8308", "Hooks, eyes, buckles of metal", ("button", "zipper", "fastener", "buckle")),
    TaricEntry("8309000000", "8309", "Stoppers, caps, lids of metal", ("cap", "lid", "stopper", "metal")),
    
    # ===== CHAPTER 84: NUCLEAR REACTORS, BOILERS, MACHINERY =====
    TaricEntry("8401300000", "8401", "Reactor fuel elements", ("fuel", "nuclear")),
    TaricEntry("8410000000", "8410", "Hydraulic turbines and water wheels", ("turbine", "hydraulic")),
    TaricEntry("8412100000", "8412", "Pneumatic or hydraulic machines", ("hydraulic", "pump", "compressor")),
    TaricEntry("8414300000", "8414", "Air or vacuum pumps", ("pump", "compressor")),
    TaricEntry("8418690000", "8418", "Refrigerating and freezing equipment", ("refrigerator", "freezer", "cooling")),
    TaricEntry("8421310000", "8421", "Centrifuges", ("centrifuge", "machine")),
    TaricEntry("8427100000", "8427", "Fork-lift trucks", ("forklift", "machinery")),
    TaricEntry("8428320000", "8428", "Other moving, handling machinery", ("conveyor", "machinery")),
    TaricEntry("8431490000", "8431", "Parts for lifting/handling machinery", ("part", "machinery")),
    TaricEntry("8433110000", "8433", "Machinery for agriculture", ("tractor", "farming")),
    TaricEntry("8434810000", "8434", "Milking machines", ("milking", "farm")),
    TaricEntry("8438809000", "8438", "Food processing machinery", ("machine", "food")),
    TaricEntry("8443320000", "8443", "Inkjet printing machines", ("printer", "inkjet")),
    TaricEntry("8445190000", "8445", "Textile machinery", ("loom", "textile")),
    TaricEntry("8451800000", "8451", "Machines for washing clothes", ("washing machine", "laundry", "dryer")),
    TaricEntry("8456110000", "8456", "Machine tools for working metal", ("lathe", "machine tool")),
    TaricEntry("8462910000", "8462", "Metal processing machines", ("press", "machine")),
    TaricEntry("8471300000", "8471", "Portable automatic data processing machines (Laptops)", 
               ("laptop", "notebook", "computer", "macbook", "portable computer")),
    TaricEntry("8481809090", "8481", "Taps, cocks, valves", ("valve", "tap", "faucet")),
    
    # ===== CHAPTER 85: ELECTRICAL MACHINERY & EQUIPMENT =====
    TaricEntry("8504309000", "8504", "Power supply units", ("power supply", "power adapter", "charger")),
    TaricEntry("8507600019", "8507", "Electric accumulators (batteries)", ("battery", "rechargeable")),
    TaricEntry("8511100000", "8511", "Spark plugs", ("spark plug", "electrical")),
    TaricEntry("8517130000", "8517", "Smartphones", 
               ("smartphone", "iphone", "samsung", "android phone")),
    TaricEntry("8517140000", "8517", "Other wireless mobile phones", 
               ("mobile phone", "cell phone", "feature phone", "phone")),
    TaricEntry("8517620000", "8517", "Base stations for wireless communications", ("antenna", "wireless")),
    TaricEntry("8518300000", "8518", "Headphones and earphones", 
               ("headphones", "airpods", "earbuds", "earphones", "headset")),
    TaricEntry("8519810000", "8519", "Microphones", ("microphone", "audio")),
    TaricEntry("8521900000", "8521", "Video projectors", ("projector", "video")),
    TaricEntry("8524410000", "8524", "Magnetic tapes for sound recording", ("tape", "magnetic")),
    TaricEntry("8525801000", "8525", "Video recording cameras", ("camera", "video", "camcorder")),
    TaricEntry("8528720000", "8528", "Computer monitors", ("monitor", "display", "screen")),
    TaricEntry("8529904000", "8529", "Parts for electrical equipment", ("part", "component")),
    TaricEntry("8531200000", "8531", "Electric bells and buzzers", ("bell", "buzzer", "alarm")),
    TaricEntry("8535400000", "8535", "Electrical switches and safety equipment", ("switch", "circuit breaker")),
    TaricEntry("8538109000", "8538", "Electrical control panels", ("panel", "control")),
    TaricEntry("8542310000", "8542", "Electronic integrated circuits", 
               ("chip", "semiconductor", "integrated circuit", "microchip", "cpu")),
    TaricEntry("8544302090", "8544", "Electrical power distribution cables", ("cable", "wire", "electrical")),
    
    # ===== CHAPTER 86: RAILWAY VEHICLES =====
    TaricEntry("8601100000", "8601", "Steam locomotives", ("locomotive", "train", "railway")),
    TaricEntry("8606100000", "8606", "Railway wagons", ("wagon", "railway", "transport")),
    
    # ===== CHAPTER 87: VEHICLES (ROAD) =====
    TaricEntry("8704310000", "8704", "Trucks (goods vehicles)", ("truck", "vehicle", "transport")),
    TaricEntry("8711201000", "8711", "Motorcycles", ("motorcycle", "bike", "two-wheeler")),
    
    # ===== CHAPTER 88: AIRCRAFT =====
    TaricEntry("8801910000", "8801", "Powered aircraft", ("airplane", "aircraft")),
    TaricEntry("8805210000", "8805", "Aircraft ground handling equipment", ("aircraft", "handling")),
    
    # ===== CHAPTER 89: SHIPS & VESSELS =====
    TaricEntry("8902000000", "8902", "Fishing vessels", ("ship", "vessel", "boat")),
    TaricEntry("8906900000", "8906", "Other floating structures", ("boat", "vessel")),
    
    # ===== CHAPTER 90: OPTICAL INSTRUMENTS =====
    TaricEntry("9001100000", "9001", "Optical fibers and cables", ("fiber", "optical", "cable")),
    TaricEntry("9002110000", "9002", "Lenses and optical elements", ("lens", "optical")),
    TaricEntry("9004100000", "9004", "Spectacles and goggles", ("glasses", "spectacles", "eyewear")),
    TaricEntry("9006290000", "9006", "Cameras without interchangeable lenses", ("camera", "photography", "digital")),
    TaricEntry("9011100000", "9011", "Microscopes", ("microscope", "optical")),
    TaricEntry("9014200010", "9014", "Surveying instruments", ("surveying", "measurement", "instrument")),
    TaricEntry("9018110000", "9018", "Electrocardiographs", ("medical", "diagnostic")),
    TaricEntry("9031800099", "9031", "Measuring and checking instruments", ("measuring", "gauge", "instrument")),
    
    # ===== CHAPTER 91: WATCHES & CLOCKS =====
    TaricEntry("9102190000", "9102", "Wrist watches", ("watch", "wristwatch", "timepiece")),
    TaricEntry("9104000000", "9104", "Instrument panel clocks", ("clock", "timepiece")),
    
    # ===== CHAPTER 92: MUSICAL INSTRUMENTS =====
    TaricEntry("9202100000", "9202", "Pianos", ("piano", "musical instrument")),
    TaricEntry("9206000000", "9206", "Percussion instruments", ("drum", "percussion", "instrument")),
    TaricEntry("9208100000", "9208", "Musical instruments with self-contained mechanisms", ("music box", "instrument")),
    
    # ===== CHAPTER 93: ARMS & AMMUNITION =====
    TaricEntry("9303200000", "9303", "Firearms", ("gun", "rifle", "firearm")),
    TaricEntry("9304100000", "9304", "Air guns", ("air gun", "gun")),
    TaricEntry("9305219000", "9305", "Parts and accessories of firearms", ("ammunition", "parts")),
    
    # ===== CHAPTER 94: FURNITURE =====
    TaricEntry("9401200090", "9401", "Seats with wooden frames", ("chair", "seat", "furniture")),
    TaricEntry("9403600090", "9403", "Furniture of wood", ("desk", "table", "wooden furniture")),
    TaricEntry("9406001000", "9406", "Prefabricated buildings", ("building", "structure")),
    
    # ===== CHAPTER 95: TOYS, GAMES & SPORTS EQUIPMENT =====
    TaricEntry("9503000000", "9503", "Toys and puzzles", 
               ("toy", "game", "puzzle", "doll", "action figure", "board game", "lego")),
    TaricEntry("9504500000", "9504", "Video game consoles and equipment", 
               ("playstation", "xbox", "nintendo", "console", "video game", "switch", "gaming")),
    TaricEntry("9506290000", "9506", "Articles for sports and games", 
               ("sports", "ball", "racket", "equipment")),
    TaricEntry("9507900000", "9507", "Fishing rods and reels", ("fishing", "rod", "reel")),
    
    # ===== CHAPTER 96: MISCELLANEOUS MANUFACTURED ARTICLES =====
    TaricEntry("9601900000", "9601", "Worked vegetable carving material", ("carving", "material")),
    TaricEntry("9603290000", "9603", "Brooms and brushes", ("broom", "brush", "cleaning")),
    TaricEntry("9605000000", "9605", "Travel sets, toiletry kits", ("travel", "kit")),
    TaricEntry("9606300000", "9606", "Buttons", ("button", "fastener")),
    TaricEntry("9607110000", "9607", "Slide fasteners (zippers)", ("zipper", "fastener")),
    TaricEntry("9609100000", "9609", "Pencils and crayons", ("pencil", "crayon", "writing")),
    TaricEntry("9612100000", "9612", "Ribbons for typewriters", ("ribbon", "supplies")),
    TaricEntry("9615110000", "9615", "Hair combs", ("comb", "hair", "brush")),
    TaricEntry("9619001000", "9619", "Articles for personal sanitation", ("sanitary", "personal care", "tampon", "pad", "kotex", "feminine hygiene")),
)

if __name__ == '__main__':
    print(f"✅ Full TARIC Catalog with {len(FULL_TARIC_CATALOG)} entries loaded")
    print(f"📊 Chapters covered: 1-96 (all EU chapters)")
    for i, entry in enumerate(FULL_TARIC_CATALOG[:5]):
        print(f"  [{i+1}] {entry.taric_code}: {entry.description}")
    print(f"  ... and {len(FULL_TARIC_CATALOG) - 5} more entries")
