
# Xiaomi S20 Robot Süpürge Joystick Kontrolü (Teknik Durum)

Bu belge, Xiaomi S20 (model: `xiaomi.vacuum.d106gl`) robot süpürgesini yerel ağ üzerinden joystick ile kontrol etme denemesinin teknik durumunu açıklar. S20'nin resmi MIoT tanımında manuel sürüş eylemi bulunmadığı için aşağıdaki eski RC taslağı bu cihazda çalışmaz.

## 1. Mimari Mantığı (Neden Gecikme Olmuyor?)

Mobil uygulamanın anlık tepki vermesinin sırrı, her komutta yeni bir bağlantı açmamasıdır. Biz de Python scriptimizde bu mantığı taklit edeceğiz:

1.  **Tek Seferlik El Sıkışma (Handshake):** Script çalıştığında süpürge ile sadece bir kez kimlik doğrulaması yapılır ve iletişim tüneli açılır.
2.  **UDP Protokolü (miIO):** İletişim TCP yerine daha hızlı olan UDP paketleri (miIO protokolü) üzerinden sağlanır.
3.  **RC (Remote Control) Modu:** `python-miio` içindeki `manual_start()` metodu `app_rc_start` gönderir. S20 bu komutu onaylamaz.
4.  **Sonuç:** `user ack timeout` hatası alınır. Bu, ağ veya token hatası değil, cihaz-protokol uyumsuzluğudur.

---

## 2. Gereksinimler

*   **Python:** Minimum Python 3.8+
*   **Ağ:** Bilgisayarınız ve robot süpürge aynı Wi-Fi ağında (tercihen aynı modeme, örneğin ZTE H3600'e) bağlı olmalıdır.
*   **Bilgiler:** Robot süpürgenin yerel **IP Adresi** ve 32 karakterlik **Token** bilgisi.
*   **Donanım:** Bilgisayara bağlı bir gamepad (Xbox, PlayStation vb.)
*   **Gerekli Kütüphaneler:** Terminalde şu komutla gerekli paketleri yükleyin:
    ```bash
    python -m pip install -r requirements.txt
    ```

---

## 3. Çözülen MIoT Sürüş Komutu

Mi Home trafiği token ile çözüldüğünde gerçek sürüş komutu bulundu. S20 yön bilgisini `set_properties` yöntemiyle gönderiyor:

```python
vacuum.send(
    "set_properties",
    [{"did": "1069182766", "siid": 7, "piid": 16, "value": 1}],
)
```

`siid: 7`, `piid: 16` özelliğinin resmi değerleri:

| Değer | Yön |
|---:|---|
| 1 | İleri |
| 2 | Sol |
| 3 | Sağ |
| 4 | Geri |
| 5 | Dur |
| 10 | Sürüş modundan çık |

`did` değeri bu cihaz için `1069182766`'dır. Eski `app_rc_start` ve `app_rc_move` komutları S20 için kullanılmamalıdır.

Bu nedenle aşağıdaki gibi uydurma bir çağrı çalışmaz:

```python
vac.send("action", {"did": "forward", "siid": 2, "aiid": 1, "in": []})
```

`aiid: 1`, ileri sürüş değil, **Start Sweep** eylemidir. Bu kimliği yönlendirme amacıyla kullanmak normal temizlik başlatabilir.

## 4. Kodun Ana Yapısı ve İşleyişi

### Adım 1: Bağlantı ve Cihaz Kurulumu
`python-miio` temel `Device` sınıfı ile `set_properties` komutu ve cihazın MIoT yön özelliği kullanılabilir.

### Adım 2: Joystick Başlatma (Pygame)
`pygame.joystick` modülü ile bilgisayara bağlı kollar taranır ve ilk bulunan kol kontrol için seçilir.

### Adım 3: S20 Sürüş Özelliği
Joystick yönü `siid=7`, `piid=16` ve `value` alanı ile gönderilir. Her komut yeni bir `app_rc_start` gerektirmez.

### Adım 4: Ana Döngü
Sonsuz döngüde joystick eksenleri okunur ve `1`, `2`, `3`, `4` veya `5` değerlerinden birine çevrilerek gönderilir.

### Adım 5: Komut Gönderimi
Yön değeri `set_properties` ile periyodik olarak gönderilir. Joystick bırakıldığında `value=5` dur komutu, kapanışta `value=10` çıkış komutu gönderilir.

---

## 5. Sonuç

`controller.py` joystick'i algılıyor ve Mi Home trafiğinden çıkarılan gerçek S20 sürüş komutunu gönderiyor. `app_rc_start` yerine `set_properties` kullanıldığı için önceki `user ack timeout` hatası bu akışta oluşmaz.

Temizlik başlatma/durdurma MIoT eylemleri ayrı komutlardır; joystick sürüşü `siid=7`, `piid=16` özelliğidir.

## 6. Eski Python Taslağı

Aşağıdaki taslak, yukarıda anlatılan mimarinin temel iskeletidir. Kendi IP ve Token bilgilerinizi girmelisiniz.

```python
import time
import pygame
from miio import Vacuum

# 1. Cihaz Bilgileri
VACUUM_IP = "192.168.1.XX"  # Süpürgenin yerel IP adresi
VACUUM_TOKEN = "32_KARAKTERLIK_TOKEN_BURAYA"

def main():
    # 2. Joystick Kurulumu (Pygame)
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0:
        print("Bağlı joystick bulunamadı!")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick bağlandı: {joystick.get_name()}")

    # 3. Süpürge Bağlantısı
    print(f"{VACUUM_IP} adresindeki süpürgeye bağlanılıyor...")
    vac = Vacuum(VACUUM_IP, VACUUM_TOKEN)
    
    # RC Modunu Başlat (Gecikmesiz sürekli iletişim için)
    print("RC Modu başlatılıyor...")
    vac.manual_start()
    
    try:
        print("Kontrol başlatıldı. (Çıkmak için CTRL+C)")
        while True:
            pygame.event.pump()  # Joystick verilerini güncelle
            
            # 4. Eksen Verilerini Oku
            # Sol analog çubuğun Y ekseni (İleri/Geri) ve X ekseni (Sağ/Sol)
            # Not: Yukarı itildiğinde genellikle negatif değer gelir, bu yüzden tersine çeviriyoruz.
            axis_y = -joystick.get_axis(1) 
            axis_x = joystick.get_axis(0)
            
            # Eşik değeri (Deadzone): Çubuk hafif titriyorsa yoksay
            if abs(axis_y) < 0.1: axis_y = 0.0
            if abs(axis_x) < 0.1: axis_x = 0.0
            
            # 5. Süpürgeye Verileri Çevir (Mapping)
            # Değerleri süpürgenin hız limitlerine göre çarpmak gerekebilir.
            velocity = axis_y * 0.3  # İleri/geri hızı ayarlayın
            rotation = axis_x * 0.5  # Dönüş hızını ayarlayın
            
            if velocity != 0 or rotation != 0:
                # Açık olan kanal üzerinden komutu gönder
                vac.manual_control(velocity, rotation)
            else:
                # Joystick bırakıldığında dur
                vac.manual_control_once(0.0, 0.0) 

            # Aşırı komut gönderip cihazı boğmamak için bekleme (Örn: Saniyede 10 komut)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("Çıkış yapılıyor...")
    finally:
        # 6. RC Modunu Kapat
        print("RC Modu kapatılıyor, normale dönülüyor...")
        vac.manual_stop()
        pygame.quit()

if __name__ == "__main__":
    main()
```
