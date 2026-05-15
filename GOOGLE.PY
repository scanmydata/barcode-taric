import os
import json
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
import re

# =====================================================================
# ΜΗΧΑΝΙΣΜΟΙ ΑΝΤΛΗΣΗΣ ΚΑΙ ΕΠΕΞΕΡΓΑΣΙΑΣ (100% ΔΩΡΕΑΝ)
# =====================================================================

def google_search_and_extract(query):
    """
    ΒΗΜΑ 1: Αναζήτηση στη Google. Αν είναι barcode, μετατρέπεται σε κείμενο specs.
    Αν είναι ήδη περιγραφή, εμπλουτίζεται με context από την αγορά.
    """
    print(f"[Google] Αναζήτηση και εξαγωγή στοιχείων για: '{query}'...")
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://google.com{encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Συλλογή τίτλων (h3) από τα οργανικά αποτελέσματα της Google
            titles = [h3.get_text() for h3 in soup.find_all("h3")][:3]
            if titles:
                combined_context = " | ".join(titles)
                return combined_context
    except Exception as e:
        print(f"    -> Σφάλμα Google Search: {e}")
    return query


def free_ai_convert_to_hs(product_context):
    """
    ΒΗΜΑ 2: Δωρεάν AI Engine (No-Key). Αναλύει το κείμενο της αγοράς 
    και το μεταφράζει στο επίσημο 4ψήφιο κεφάλαιο HS Code του δασμολογίου.
    """
    print(f"[AI Engine] Ανάλυση κατηγοριοποίησης εμπορεύματος...")
    
    prompt = (
        f"Είσαι έμπειρος εκτελωνιστής. Σου δίνω την περιγραφή/τίτλους ενός προϊόντος: \"{product_context}\". "
        "Βρες σε ποιο 4ψήφιο κεφάλαιο (HS Code / Κλάση TARIC) ανήκει. "
        "Απάντησε ΑΥΣΤΗΡΑ ΚΑΙ ΜΟΝΟ με τον 4ψήφιο αριθμό (π.χ. 8517 ή 2201), χωρίς καμία άλλη λέξη, επεξήγηση ή σημεία στίξης."
    )
    
    # Χρήση του Pollinations AI (δωρεάν, χωρίς όρια και χωρίς API Key)
    url = "https://pollinations.ai"
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "openai-large",
        "jsonMode": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            ai_response = response.text.strip()
            # Απομόνωση των 4 ψηφίων με Regular Expression για ασφάλεια
            match = re.search(r'\b\d{4}\b', ai_response)
            if match:
                return match.group(0)
    except Exception as e:
        print(f"    -> Σφάλμα AI Engine: {e}")
    
    return "0000"


def fetch_official_eu_taric(hs_code):
    """
    ΒΗΜΑ 3: Live Σύνδεση με την Ευρωπαϊκή Επιτροπή.
    Παίρνει το 4ψήφιο HS και επιστρέφει τον επίσημο, ενεργό 10ψήφιο TARIC.
    """
    if hs_code == "0000":
        return "Αδυναμία κατηγοριοποίησης"
        
    print(f"[EU Portal] Σύνδεση με ec.europa.eu για την κλάση {hs_code}...")
    url = "https://europa.eu"
    params = {
        "Lang": "el",
        "Taric": hs_code,
        "Expand": "true",
        "ScreenOrder": "1"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            taric_elements = soup.find_all(class_="taric-code")
            
            for elem in taric_elements:
                code = "".join(elem.get_text(strip=True).split())
                # Κλειδώνουμε τον πρώτο έγκυρο 10ψήφιο κωδικό TARIC της κατηγορίας
                if len(code) == 10 and code.startswith(hs_code):
                    return code
                    
            return f"{hs_code}000000 (Βασική Κλάση)"
    except Exception as e:
        print(f"    -> Σφάλμα σύνδεσης με Ευρωπαϊκή Επιτροπή: {e}")
        
    return f"{hs_code}000000"

# =====================================================================
# ΚΥΡΙΑ ΚΕΝΤΡΙΚΗ ΡΟΗ (PIPELINE)
# =====================================================================

def execute_taric_pipeline(inputs_list):
    final_output = []
    total_items = len(inputs_list)
    
    print(f"==================================================")
    print(f"🚀 Έναρξη Επεξεργασίας: {total_items} Προϊόντα")
    print(f"==================================================")
    
    for index, current_input in enumerate(inputs_list, 1):
        current_input = str(current_input).strip()
        print(f"\n[{index}/{total_items}] Processing: {current_input}")
        
        # 1. Scraping Context
        market_context = google_search_and_extract(current_input)
        print(f"   -> Εντοπίστηκε context: {market_context[:70]}...")
        
        # 2. AI Parsing
        hs_code = free_ai_convert_to_hs(market_context)
        print(f"   -> AI Δασμολογική Κλάση: {hs_code}")
        
        # 3. Live EU Validation
        taric_code = fetch_official_eu_taric(hs_code)
        print(f"   -> Επίσημος Κωδικός TARIC: {taric_code}")
        
        # Καταγραφή Αποτελέσματος
        final_output.append({
            "user_input": current_input,
            "resolved_description": market_context,
            "predicted_hs_code": hs_code,
            "official_taric_code": taric_code,
            "execution_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Αντι-μπλοκάρισμα (Anti-bot delay για τη Google)
        time.sleep(2.5)

    # Εγγραφή του αρχείου JSON στον root φάκελο
    output_path = os.path.join(os.getcwd(), "taric_output.json")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        print(f"\n==================================================")
        print(f"✅ Η επεξεργασία ολοκληρώθηκε με επιτυχία!")
        print(f"💾 Το αρχείο JSON αποθηκεύτηκε: {output_path}")
        print(f"==================================================")
    except Exception as e:
        print(f"Σφάλμα κατά την εγγραφή του JSON: {e}")

# =====================================================================
# ΕΙΣΑΓΩΓΗ ΔΕΔΟΜΕΝΩΝ ΠΡΟΣ ΕΠΕΞΕΡΓΑΣΙΑ
# =====================================================================
if __name__ == "__main__":
    # Εδώ βάζετε όσα barcodes ή περιγραφές θέλετε ταυτόχρονα
    my_products_list = [
        "5201005080027",                          # Barcode (Νερό Αύρα)
        "8447351005797",                          # Barcode (Υγρό Vape Bombo)
        "Ανδρικό βαμβακερό πουκάμισο μακρυμάνικο",   # Περιγραφή προϊόντος
        "Φορητός υπολογιστής Apple MacBook Pro",   # Περιγραφή προϊόντος
        "0901210000"                              # Απευθείας Κωδικός προς έλεγχο
    ]
    
    execute_taric_pipeline(my_products_list)
