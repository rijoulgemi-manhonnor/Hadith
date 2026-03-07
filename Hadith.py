import os
import logging
import json
import hashlib
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

class GroqOnlyHadithBot:
    """Bot qui utilise UNIQUEMENT Groq pour tout"""
    
    def __init__(self, client):
        self.client = client
        self.cache_dir = Path("groq_cache")
        self.cache_dir.mkdir(exist_ok=True)
        logging.info("✅ Bot GroqOnly initialisé")
    
    def get_hadith_with_dua(self):
        """
        Utilise Groq pour générer un hadith authentique contenant une invocation
        """
        cache_key = "daily_hadith_dua"
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        # Vérifier le cache (24h)
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(data['timestamp'])).days < 1:
                    logging.info("✅ Hadith trouvé dans le cache")
                    return data['hadith_data']
        
        prompt = """أنت عالم حديث متخصص. المطلوب: اذكر حديثاً صحيحاً واحداً من الأحاديث النبوية الشريفة يستوفي الشروط التالية:

1. يجب أن يكون الحديث صحيحاً (من صحيح البخاري أو مسلم أو غيرهما من كتب الحديث المعتمدة).
2. يجب أن يحتوي الحديث على دعاء أو ابتهال إلى الله تعالى (مثل: اللهم، ربنا، رب، اغفر لي، ارحمني، اهدني، تقبل منا، ونحو ذلك).
3. اذكر نص الحديث كاملاً باللغة العربية الفصحى كما ورد.
4. اذكر مصدر الحديث (الكتاب ورقم الحديث إن أمكن).
5. اذكر درجة الحديث (صحيح، حسن، وغير ذلك).

أخرج المعلومات بالصيغة التالية (JSON فقط، بدون أي نص إضافي):

{
  "hadith_text": "نص الحديث الكامل هنا",
  "source": "اسم الكتاب (مثل: صحيح البخاري)",
  "number": "رقم الحديث إن وجد، أو ضع رقم/صفحة تقريبية",
  "grade": "درجة الحديث (مثل: صحيح)"
}

تأكد من أن النص العربي صحيح وخالٍ من الأخطاء الإملائية."""
        
        try:
            logging.info("🤖 Groq génère un hadith avec invocation...")
            
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "أنت عالم حديث سلفي متخصص. ترد فقط بصيغة JSON ولا تكتب أي شيء آخر."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validation basique
            required_fields = ['hadith_text', 'source', 'number', 'grade']
            if not all(field in result for field in required_fields):
                logging.error("❌ Réponse JSON incomplète")
                return None
            
            hadith_data = {
                "hadith_text": result['hadith_text'],
                "metadata": {
                    "collection": result['source'],
                    "number": result['number'],
                    "grade": result['grade']
                },
                "success": True
            }
            
            # Sauvegarder dans le cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'hadith_data': hadith_data
                }, f, ensure_ascii=False)
            
            logging.info(f"✅ Hadith généré par Groq: {result['source']} n°{result['number']}")
            return hadith_data
            
        except Exception as e:
            logging.error(f"❌ Erreur Groq: {e}")
            return None
    
    def generate_explanation(self, hadith_text, metadata):
        """
        Génère l'explication du hadith en arabe
        """
        cache_key = hashlib.md5(hadith_text[:100].encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if (datetime.now() - datetime.fromisoformat(data['timestamp'])).days < 7:
                    return data['explanation']
        
        prompt = f"""اشرح الحديث النبوي التالي شرحاً وافياً باللغة العربية:

الحديث: {hadith_text[:700]}

المصدر: {metadata['collection']} (رقم {metadata['number']})

المطلوب في الشرح:
1. **شرح الكلمات الغريبة** في الحديث.
2. **المعنى الإجمالي** للحديث.
3. **الفوائد والأحكام المستفادة** من الحديث.
4. **الدروس والعبر**.

كن دقيقاً ومختصراً (لا يزيد الشرح عن 250 كلمة)."""
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "أنت عالم حديث متمكن. اكتب شرحاً واضحاً ومفيداً."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=800
            )
            
            explanation = response.choices[0].message.content.strip()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'explanation': explanation}, f)
            
            return explanation
            
        except Exception as e:
            logging.error(f"❌ Erreur génération explication: {e}")
            return None


def get_hijri_date():
    """Récupère la date Hijri (API externe légère)"""
    try:
        import requests
        today = datetime.now().strftime("%d-%m-%Y")
        response = requests.get(f"http://api.aladhan.com/v1/gToH?date={today}", timeout=5)
        if response.status_code == 200:
            data = response.json()['data']['hijri']
            return f"{data['day']} {data['month']['ar']} {data['year']}"
    except:
        pass
    return datetime.now().strftime("%d %B %Y")


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
                'parse_mode': 'Markdown'
            },
            timeout=15
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"❌ Erreur envoi: {e}")
        return False


def format_message(hadith_data, hijri_date, explanation=None):
    """Formate le message final"""
    meta = hadith_data['metadata']
    
    msg = f"""🌙 *حديث الدعاء*

📚 *المصدر*: {meta['collection']}
🔢 *الرقم*: {meta['number']}
⭐ *الدرجة*: {meta['grade']}
📅 *التاريخ*: {hijri_date}

━━━━━━━━━━━━━━━━

📖 *الحديث:*
{hadith_data['hadith_text']}

━━━━━━━━━━━━━━━━"""

    if explanation:
        msg += f"""

📝 *الشرح:*
{explanation}

━━━━━━━━━━━━━━━━"""

    msg += "\n\n#حديث #دعاء #أدعية #إسلام #سنة"
    return msg


def run():
    """Fonction principale"""
    logging.info("=" * 50)
    logging.info("🚀 Bot Hadith (Propulsé par Groq)")
    logging.info("=" * 50)
    
    # Vérifications
    if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logging.error("❌ Clés API manquantes")
        return
    
    # Initialisation
    bot = GroqOnlyHadithBot(groq_client)
    
    # 1. Obtenir un hadith avec invocation via Groq
    hadith_data = bot.get_hadith_with_dua()
    
    if not hadith_data:
        logging.error("❌ Échec génération hadith")
        send_telegram_message("⚠️ عذراً، لم نتمكن من تحضير حديث الدعاء اليوم.")
        return
    
    # 2. Date hijri
    hijri_date = get_hijri_date()
    
    # 3. Générer l'explication
    explanation = bot.generate_explanation(
        hadith_data['hadith_text'],
        hadith_data['metadata']
    )
    
    # 4. Formater et envoyer
    message = format_message(hadith_data, hijri_date, explanation)
    
    if send_telegram_message(message):
        logging.info("✅ Message envoyé avec succès!")
    else:
        logging.error("❌ Échec envoi")
    
    logging.info("=" * 50)


if __name__ == "__main__":
    # Import requests uniquement si nécessaire
    try:
        import requests
    except ImportError:
        pass
    run()
