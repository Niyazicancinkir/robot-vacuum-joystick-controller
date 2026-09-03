# Xiaomi S20 (d106gl) Joystick Kontrolü: Doğrulanmış Komut

Bu belge, Xiaomi S20 robot süpürgesini joystick ile kontrol etme denemesinin sonucunu açıklar.

## Cihaz

- Model: `xiaomi.vacuum.d106gl`
- Firmware: `v4.3.9_0020`
- İletişim: yerel miIO/MIoT
- Joystick: Logitech F710 başarıyla algılanıyor

## Alınan Hata

```text
{'code': -9999, 'message': 'user ack timeout'}
```

Hata `manual_start()` çağrısında oluşuyor. IP ve token ile cihazdan cevap alınabildiği için bu bir ağ veya kimlik doğrulama hatası değildir.

## Gemini'deki v2 kodundaki hata

Gemini metnindeki şu komutlar S20'nin resmi MIoT haritasında yoktur:

- `forward`
- `backward`
- `right`
- `left`
- `stop`

Ayrıca `siid: 2, aiid: 1` yönlendirme komutu değildir. S20 haritasında bu, **Start Sweep** eylemidir. Yanlışlıkla joystick yönü gibi kullanmak temizlik başlatabilir.

```python
# Kullanılmamalı: S20'de belgelenmiş bir joystick eylemi değildir.
vac.send("action", {"did": "forward", "siid": 2, "aiid": 1, "in": []})
```

## Gerçek sürüş komutu

Mi Home paketleri token ile çözüldüğünde gerçek komut bulundu:

```python
vacuum.send(
	"set_properties",
	[{"did": "1069182766", "siid": 7, "piid": 16, "value": 1}],
)
```

`siid=7`, `piid=16` yön değerleri:

| Değer | Yön |
|---:|---|
| 1 | İleri |
| 2 | Sol |
| 3 | Sağ |
| 4 | Geri |
| 5 | Dur |
| 10 | Çıkış |

## Resmi MIoT haritasında bulunan diğer eylemler

Robot Cleaner servisinde şu eylemler bulunur:

- Start Sweep
- Stop Sweeping
- Start Only Sweep
- Start Sweep Mop
- Start Mop
- Start Room Sweep
- Start Vacuum Room Sweep

Bu eylemler temizlik kontrolüdür; gerçek zamanlı tekerlek/yön kontrolü değildir.

## Sonuç

`python-miio` ile:

- Cihaz bilgileri okunabilir.
- Desteklenen temizlik komutları gönderilebilir.
- S20, Mi Home’un kullandığı `set_properties` yön özelliği ile joystick olarak sürülebilir.

`app_rc_start` komutu S20 tarafından onaylanmadığı için `app_rc_move` kullanılmamalıdır. Bunun yerine `set_properties` ile `siid=7`, `piid=16` ve yön değeri gönderilmelidir.

## Güvenlik

Resmi MIoT haritasında bulunmayan `siid`/`aiid` değerlerini rastgele denemeyin. Robot beklenmedik şekilde temizlik başlatabilir. Denemelerden önce robotu açık bir alana alın ve acil durdurma için fiziksel düğmeyi hazır tutun.
