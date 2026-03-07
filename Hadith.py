import requests
import os
import logging
import random
import re
import hashlib
from datetime import datetime
from pathlib import Path
import json
from groq import Groq

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialisation de Groq
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if groq_client:
    logging.info("✅ GroqCloud initialisé")

class CorrectHadithAPI:
    """Version corrigée - Utilise la recherche par mot-clé"""
    
    BASE_URL = "https://hadithapi.com/api"
    
    # Mots-clés d'invocation pour la recherche
    DUA_KEYWORDS = [
        "اللهم", "ربنا", "رب", "يا رب", "يا الله",
        "اغفر لي", "ارحمنا", "اهدنا", "تقبل", "استجب"
    ]
    
    # Livres disponibles
    BOOKS = {
        "sahih-bukhari": "صحيح البخاري",
        "sahih-muslim": "صحيح مسلم",
        "sunan-abu-dawud": "سنن أبي داود",
        "sunan-tirmidhi": "جامع الترمذي",
        "sunan-nasai": "سنن النسائي",
        "sunan-ibnmajah": "سنن ابن ماجه"
    }
    
    def __init__(self):
        self.session = requests.Session()
        logging.info("✅ Client CorrectHadithAPI initialisé")
    
    def search_hadith_by_keyword(self, keyword, book=None, max_results=10):
        """
        Recherche des hadiths contenant un mot-clé spécifique
        """
        url = f"{self.BASE_URL}/hadiths/"
        params = {
            'search': keyword,
            'paginate': max_results
        }
        
        if book:
            params['book'] = book
        
        try:
            logging.info(f"🔍 Recherche de hadiths avec le mot-clé: {keyword}")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data and data.get('hadiths', {}).get('data'):
                hadiths = data['hadiths']['data']
                logging.info(f"✅ {len(hadiths)} hadiths trouvés pour '{keyword}'")
                return hadiths
            else:
                logging.info(f"ℹ️ Aucun hadith trouvé pour '{keyword}'")
                return []
                
        except Exception as e:
            logging.error(f"❌ Erreur recherche '{keyword}': {e}")
            return []
    
    def get_hadith_with_dua_correct(self):
        """
        Méthode CORRECTE: Récupère un hadith contenant une invocation
        en utilisant la recherche par mots-clés
        """
        # Mélanger les mots-clés pour varier les résultats
        keywords = self.DUA_KEYWORDS.copy()
        random.shuffle(keywords)
        
        # Essayer chaque mot-clé
        for keyword in keywords:
            # Chercher dans tous les livres ou un livre aléatoire
            if random.choice([True, False]):
                # Recherche dans un livre spécifique
                book = random.choice(list(self.BOOKS.keys()))
                hadiths = self.search_hadith_by_keyword(keyword, book=book, max_results=20)
            else:
                # Recherche dans tous les livres
                hadiths = self.search_hadith_by_keyword(keyword, max_results=30)
            
            if hadiths:
                # Filtrer pour s'assurer que le hadith contient bien l'invocation
                valid_hadiths = []
                for h in hadiths:
                    text = h.get('hadithArabic', '')
                    # Vérification plus précise avec l'expression régulière complète
                    if re.search(r'اللهم|ربنا|رب\s+[يا]?|اغفر|ارحم|اهدنا|تقبل|استجب', text):
                        valid_hadiths.append(h)
                
                if valid_hadiths:
                    # Choisir un hadith aléatoire parmi les résultats
                    selected = random.choice(valid_hadiths)
                    
                    # Récupérer le nom du livre
                    book_name = selected.get('book', {}).get('name', '')
                    book_key = next((k for k, v in self.BOOKS.items() if v == book_name), 'sahih-bukhari')
                    
                    logging.info(f"✅ Hadith avec invocation trouvé via recherche '{keyword}'")
                    
                    return {
                        "hadith_text": selected.get('hadithArabic', ''),
                        "metadata": {
                            "collection": book_name,
                            "number": selected.get('hadithNumber', ''),
                            "grade": selected.get('status', 'صحيح'),
                            "book_key": book_key
                        },
                        "success": True
                    }
        
        # Si aucun hadith trouvé avec les mots-clés, essayer l'endpoint aléatoire
        logging.info("ℹ️ Aucun hadith trouvé par recherche, utilisation de l'endpoint aléatoire...")
        return self.get_random_hadith_fallback()
    
    def get_random_hadith_fallback(self, max_attempts=10):
        """
        Fallback: Endpoint aléatoire avec vérification
        """
        for attempt in range(max_attempts):
            try:
                # Choisir un livre aléatoire
                book = random.choice(list(self.BOOKS.keys()))
                
                url = f"{self.BASE_URL}/hadiths/"
                params = {
                    'book': book,
                    'paginate': 20
                }
                
                response = self.session.get(url, params=params, timeout=10)
                data = response.json()
                
                if data and data.get('hadiths', {}).get('data'):
                    hadiths = data['hadiths']['data']
                    
                    # Vérifier chaque hadith
                    for hadith in hadiths:
                        text = hadith.get('hadithArabic', '')
                        if re.search(r'اللهم|ربنا|رب\s+[يا]?|اغفر|ارحم|اهدنا|تقبل|استجب', text):
                            book_name = hadith.get('book', {}).get('name', '')
                            
                            return {
                                "hadith_text": text,
                                "metadata": {
                                    "collection": book_name,
                                    "number": hadith.get('hadithNumber', ''),
                                    "grade": hadith.get('status', 'صحيح')
                                },
                                "success": True
                            }
                    
                    logging.info(f"⏳ Tentative {attempt+1}/{max_attempts}: pas d'invocation dans cette page")
                    
            except Exception as e:
                logging.error(f"❌ Erreur fallback: {e}")
        
        return None

class GroqHadithExplainer:
    """Génère des explications de hadiths en arabe"""
    
    def __init__(self, client):
        self.client = client
        self.cache_dir = Path("groq_cache")
        self.cache_dir.mkdir(exist_ok=True)
    
    def generate_explanation(self, hadith_text, metadata):
        """Génère une explication en arabe"""
        cache_key = hashlib.md5(hadith_text[:100].encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(data['timestamp'])).days < 7:
                    return data['explanation']
        
        prompt = f"""بصفتك متخصصاً في علوم الحديث، اشرح هذا الحديث باللغة العربية فقط:

الحديث: {hadith_text[:500]}...

المعلومات:
- الكتاب: {metadata['collection']}
- الرقم: {metadata['number']}

اكتب:
1. معنى الكلمات الغريبة
2. شرح مختصر للحديث
3. الفوائد المستفادة

200 كلمة كحد أقصى."""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            
            explanation = response.choices[0].message.content.strip()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'explanation': explanation}, f)
            
            return explanation
        except Exception as e:
            logging.error(f"Erreur Groq: {e}")
            return None


def get_hijri_date():
    """Récupère la date Hijri"""
    try:
        today = datetime.now().strftime("%d-%m-%Y")
        response = requests.get(f"http://api.aladhan.com/v1/gToH?date={today}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']}"
    except:
        pass
    
    return datetime.now().strftime("%d %B %Y")


def format_telegram_message(hadith_data, hijri_date, groq_explanation=None):
    """Formate le message Telegram en arabe"""
    metadata = hadith_data['metadata']
    
    message = f"""🌙 *حديث الدعاء*

📚 *الكتاب*: {metadata['collection']}
🔢 *الرقم*: {metadata['number']}
⭐ *الدرجة*: {metadata['grade']}
📅 *التاريخ*: {hijri_date}

━━━━━━━━━━━━━━━━

📖 *الحديث:*
{hadith_data['hadith_text']}

━━━━━━━━━━━━━━━━"""

    if groq_explanation:
        message += f"""

📝 *الشرح:*
{groq_explanation}

━━━━━━━━━━━━━━━━"""

    message += """

#حديث #دعاء #أدعية #إسلام #سنة"""
    
    return message


def send_telegram_message(message):
    """Envoie le message Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"❌ Erreur envoi: {e}")
        return False


def run():
    """Fonction principale"""
    logging.info("=" * 50)
    logging.info("🚀 Démarrage du Bot Hadith (Version CORRIGÉE)")
    logging.info("=" * 50)
    
    # Vérifications
    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.error("❌ Clés API manquantes")
        return
    
    # Date
    hijri_date = get_hijri_date()
    logging.info(f"📅 Date: {hijri_date}")
    
    # Récupérer un hadith avec invocation (MÉTHODE CORRECTE)
    client = CorrectHadithAPI()
    hadith_data = client.get_hadith_with_dua_correct()
    
    if not hadith_data:
        logging.error("❌ Aucun hadith avec invocation trouvé")
        send_telegram_message("⚠️ لم يتم العثور على حديث يحتوي على دعاء اليوم")
        return
    
    logging.info(f"✅ Hadith trouvé: {hadith_data['metadata']['collection']} n°{hadith_data['metadata']['number']}")
    logging.info(f"📝 Début du hadith: {hadith_data['hadith_text'][:100]}...")
    
    # Générer l'explication
    groq_explanation = None
    if groq_client:
        explainer = GroqHadithExplainer(groq_client)
        groq_explanation = explainer.generate_explanation(
            hadith_data['hadith_text'],
            hadith_data['metadata']
        )
        
        if groq_explanation:
            logging.info(f"✅ Explication générée ({len(groq_explanation)} caractères)")
    
    # Envoyer
    message = format_telegram_message(hadith_data, hijri_date, groq_explanation)
    
    if send_telegram_message(message):
        logging.info("✅ Message envoyé avec succès!")
    else:
        logging.error("❌ Échec de l'envoi")
    
    logging.info("=" * 50)


if __name__ == "__main__":
    run()
