import os
import logging
import json
import hashlib
import random
from datetime import datetime
from pathlib import Path
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

class GroqHadithMaster:
    """
    Bot qui utilise Groq pour générer des hadiths authentiques avec sources complètes
    """
    
    # Base de connaissances des livres de hadith
    HADITH_BOOKS = {
        "bukhari": {
            "name": "صحيح البخاري",
            "full_name": "الجامع المسند الصحيح المختصر من أمور رسول الله صلى الله عليه وسلم وسننه وأيامه",
            "scholar": "محمد بن إسماعيل البخاري",
            "total": 7563
        },
        "muslim": {
            "name": "صحيح مسلم",
            "full_name": "المسند الصحيح المختصر من السنن بنقل العدل عن العدل عن رسول الله صلى الله عليه وسلم",
            "scholar": "مسلم بن الحجاج النيسابوري",
            "total": 5362
        },
        "abudawud": {
            "name": "سنن أبي داود",
            "full_name": "سنن أبي داود",
            "scholar": "سليمان بن الأشعث السجستاني",
            "total": 5274
        },
        "tirmidhi": {
            "name": "جامع الترمذي",
            "full_name": "الجامع الكبير (سنن الترمذي)",
            "scholar": "محمد بن عيسى الترمذي",
            "total": 3891
        },
        "nasai": {
            "name": "سنن النسائي",
            "full_name": "السنن الصغرى (المجتبى)",
            "scholar": "أحمد بن شعيب النسائي",
            "total": 5758
        },
        "ibnmajah": {
            "name": "سنن ابن ماجه",
            "full_name": "سنن ابن ماجه",
            "scholar": "محمد بن يزيد القزويني",
            "total": 4341
        }
    }
    
    def __init__(self, client):
        self.client = client
        self.cache_dir = Path("hadith_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.daily_hadith_file = self.cache_dir / "daily_hadith.json"
        logging.info("✅ GroqHadithMaster initialisé")
    
    def get_daily_hadith(self):
        """
        Récupère le hadith du jour (avec cache de 24h)
        """
        # Vérifier le cache quotidien
        if self.daily_hadith_file.exists():
            with open(self.daily_hadith_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                last_date = datetime.fromisoformat(data['date']).date()
                if last_date == datetime.now().date():
                    logging.info("✅ Hadith du jour trouvé dans le cache")
                    return data['hadith']
        
        # Générer un nouveau hadith
        hadith = self._generate_authentic_hadith()
        
        if hadith:
            # Sauvegarder dans le cache
            with open(self.daily_hadith_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': datetime.now().isoformat(),
                    'hadith': hadith
                }, f, ensure_ascii=False)
        
        return hadith
    
    def _generate_authentic_hadith(self):
        """
        Génère un hadith authentique avec source complète
        """
        # Sélectionner un livre aléatoire
        book_key = random.choice(list(self.HADITH_BOOKS.keys()))
        book = self.HADITH_BOOKS[book_key]
        
        # Générer un numéro de hadith plausible
        hadith_number = random.randint(1, book['total'])
        
        prompt = f"""أنت محدث وعالم حديث متخصص. المطلوب: اذكر حديثاً نبوياً شريفاً واحداً فقط يستوفي الشروط التالية بدقة:

1. **الحديث يجب أن يكون صحيحاً أو حسناً** من كتب الحديث المعتمدة.
2. **الحديث يجب أن يحتوي على دعاء أو ابتهال** (مثل: اللهم، ربنا، رب، اغفر لي، ارحمني، اهدني، تقبل، استجب).
3. **الكتاب المطلوب**: {book['name']} للإمام {book['scholar']}.
4. **رقم الحديث التقريبي**: {hadith_number} (أو ما يقاربه).

المطلوب منك:
- اذكر **نص الحديث كاملاً** بالعربية الفصحى كما ورد في المصادر.
- اذكر **الراوي** (صحابي أو تابعي).
- اذكر **الكتاب ورقم الحديث** الدقيق (بقدر الإمكان).
- اذكر **درجة الحديث** (صحيح، حسن، وغير ذلك).
- اذكر **التخريج** (من أخرجه غير صاحب الكتاب إن أمكن).

أخرج المعلومات بالصيغة JSON التالية بدقة، ولا تكتب أي شيء خارج JSON:

{{
  "hadith": {{
    "arabic_text": "نص الحديث الكامل هنا",
    "narrator": "اسم الراوي",
    "source": {{
      "book": "{book['name']}",
      "number": "الرقم الدقيق للحديث في الكتاب",
      "grade": "درجة الحديث (صحيح/حسن/ضعيف)"
    }},
    "additional_sources": [
      {{
        "book": "اسم كتاب آخر",
        "number": "رقم الحديث فيه"
      }}
    ],
    "keywords": ["دعاء", "كلمات", "مفتاحية"]
  }}
}}

تأكد من:
- صحة النص العربي وخلوه من الأخطاء.
- أن الحديث يحتوي على دعاء صريح.
- أن المعلومات دقيقة بقدر المستطاع."""
        
        try:
            logging.info(f"🤖 Groq génère un hadith de {book['name']}...")
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "أنت محدث جليل، عالم بالحديث وعلومه. ترد فقط بصيغة JSON ولا تكتب أي شيء آخر."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,  # Température basse pour plus de précision
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validation et enrichissement
            hadith = result.get('hadith', {})
            
            # S'assurer que le texte du hadith est complet
            if len(hadith.get('arabic_text', '')) < 50:
                logging.warning("⚠️ Hadith trop court, nouvelle tentative...")
                return self._generate_authentic_hadith()  # Réessayer
            
            # Ajouter des métadonnées supplémentaires
            hadith['metadata'] = {
                'generated_at': datetime.now().isoformat(),
                'model': 'llama-3.3-70b-versatile',
                'book_info': book
            }
            
            logging.info(f"✅ Hadith généré: {hadith['source']['book']} n°{hadith['source']['number']}")
            return hadith
            
        except Exception as e:
            logging.error(f"❌ Erreur Groq: {e}")
            return None
    
    def explain_hadith(self, hadith):
        """
        Génère une explication détaillée du hadith
        """
        cache_key = hashlib.md5(hadith['arabic_text'][:100].encode()).hexdigest()
        cache_file = self.cache_dir / f"explain_{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(data['timestamp'])).days < 30:  # Cache 30 jours
                    return data['explanation']
        
        prompt = f"""بصفتك عالماً من علماء الحديث، اشرح الحديث النبوي التالي شرحاً وافياً:

📖 *نص الحديث:*
{hadith['arabic_text']}

📚 *المصدر:* {hadith['source']['book']} (رقم {hadith['source']['number']})
👤 *الراوي:* {hadith['narrator']}
⭐ *الدرجة:* {hadith['source']['grade']}

المطلوب في الشرح:

1. **شرح الكلمات الغريبة**: اشرح المفردات الصعبة في الحديث.
2. **المعنى الإجمالي**: لخص معنى الحديث في سطرين.
3. **الفوائد والأحكام**: اذكر 3-5 فوائد مستفادة من الحديث.
4. **الدعاء في الحديث**: حلل الدعاء الوارد في الحديث وبين فضله.
5. **التطبيقات العملية**: كيف نطبق هذا الحديث في حياتنا اليومية.

اكتب الشرح بأسلوب واضح وميسر، مع ذكر أقوال العلماء إن أمكن.
الشرح باللغة العربية الفصحى.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "أنت عالم حديث متمكن، تشرح الأحاديث بأسلوب واضح ومفيد."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=1200
            )
            
            explanation = response.choices[0].message.content.strip()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'explanation': explanation}, f)
            
            return explanation
            
        except Exception as e:
            logging.error(f"❌ Erreur explication: {e}")
            return None


def get_hijri_date():
    """Récupère la date Hijri complète"""
    try:
        import requests
        today = datetime.now().strftime("%d-%m-%Y")
        response = requests.get(f"http://api.aladhan.com/v1/gToH?date={today}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()['data']['hijri']
            weekday = data['weekday']['ar']
            day = data['day']
            month = data['month']['ar']
            year = data['year']
            return f"{weekday} {day} {month} {year}هـ"
    except:
        pass
    
    return datetime.now().strftime("%d %B %Y")


def format_telegram_message(hadith, explanation, hijri_date):
    """
    Formate le message Telegram de façon élégante et complète
    """
    source = hadith['source']
    
    message = f"""🌙 *حديث نبوي شريف*

━━━━━━━━━━━━━━━━━━
📅 *التاريخ:* {hijri_date}
━━━━━━━━━━━━━━━━━━

📖 *نص الحديث:*
{hadith['arabic_text']}

━━━━━━━━━━━━━━━━━━
👤 *الراوي:* {hadith['narrator']}
📚 *المصدر:* {source['book']} (رقم {source['number']})
⭐ *الدرجة:* {source['grade']}
"""

    # Ajouter les sources additionnelles si disponibles
    if hadith.get('additional_sources'):
        message += "\n📌 *أخرجه أيضًا:*\n"
        for src in hadith['additional_sources'][:2]:  # Maximum 2 sources
            message += f"• {src['book']} (رقم {src['number']})\n"
    
    message += f"""
━━━━━━━━━━━━━━━━━━"""

    if explanation:
        message += f"""

📝 *شرح الحديث:*
{explanation}

━━━━━━━━━━━━━━━━━━"""

    message += """

✨ *دعاء اليوم مستفاد من هذا الحديث*
#حديث #دعاء #إسلام #سنة #هدي_نبوي"""
    
    return message


def send_telegram_message(message):
    """Envoie le message Telegram"""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            url,
            data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"❌ Erreur envoi: {e}")
        return False


def run():
    """Fonction principale"""
    logging.info("=" * 60)
    logging.info("🚀 Bot Hadith - Version Complète avec Sources")
    logging.info("=" * 60)
    
    # Vérifications
    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.error("❌ Clés API manquantes")
        return
    
    # Initialisation
    bot = GroqHadithMaster(groq_client)
    
    # 1. Récupérer le hadith du jour
    logging.info("📖 Recherche du hadith du jour...")
    hadith = bot.get_daily_hadith()
    
    if not hadith:
        logging.error("❌ Impossible de générer le hadith")
        send_telegram_message("⚠️ عذراً، حدث خطأ في تحضير الحديث اليوم. سنحاول غداً إن شاء الله.")
        return
    
    # 2. Afficher un aperçu
    logging.info(f"✅ Hadith trouvé: {hadith['source']['book']} n°{hadith['source']['number']}")
    logging.info(f"📝 Début du hadith: {hadith['arabic_text'][:100]}...")
    
    # 3. Générer l'explication
    logging.info("📝 Génération de l'explication...")
    explanation = bot.explain_hadith(hadith)
    
    if explanation:
        logging.info(f"✅ Explication générée ({len(explanation)} caractères)")
    
    # 4. Date hijri
    hijri_date = get_hijri_date()
    
    # 5. Formater et envoyer
    message = format_telegram_message(hadith, explanation, hijri_date)
    
    if send_telegram_message(message):
        logging.info("✅ Message envoyé avec succès sur Telegram!")
    else:
        logging.error("❌ Échec de l'envoi Telegram")
    
    logging.info("=" * 60)


if __name__ == "__main__":
    # Import requests uniquement si disponible
    try:
        import requests
    except ImportError:
        pass
    run()
