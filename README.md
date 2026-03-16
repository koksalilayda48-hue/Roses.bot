# Telegram Rose Bot (Gelişmiş Güvenlik)

Bu bot, Telegram gruplarını **spam, küfür, link ve bot saldırılarına karşı korur**.  
Ayrıca yeni üyeler için **karşılama mesajı ve captcha doğrulaması** sağlar.  
Belirlenen kanalları ara ara kontrol ederek güncel kalır.  

## Özellikler

- Girişte karşılama mesajı
- Captcha doğrulama
- Spam / küfür / link filtresi
- 3 uyarı → otomatik kick sistemi
- Yavaş mod uyumlu
- Ara kontroller için JobQueue
- Sadece izinli grupta çalışır, başka kanallara işlem yapmaz
- Render / 7/24 uyumlu

## Kurulum

1. Repository’yi klonlayın:

```bash
git clone https://github.com/kullaniciadi/telegram-rose-bot.git
cd telegram-rose-bot
